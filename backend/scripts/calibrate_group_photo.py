#!/usr/bin/env python3
"""Read-only calibration script for group-photo face recognition experiments.

This script intentionally avoids modifying any project files or writing to the database.
It reads the live SQLite database in read-only mode and compares the detected faces
against all registered embeddings using the existing face_service helpers.
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path
from statistics import median

import cv2
import numpy as np
from deepface import DeepFace

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.face_service import (
    MATCH_THRESHOLD,
    compare_embeddings,
    detect_single_face,
    deserialize_embedding,
    find_best_match,
    generate_embedding,
)

YUNET_MODEL = Path(__file__).resolve().parent / "models" / "face_detection_yunet_2023mar.onnx"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_PATH = OUTPUT_DIR / "calibration_annotated.jpg"


def parse_truth(value: str | None):
    if value is None or not value.strip():
        return {}
    mapping = {}
    for segment in value.split(","):
        if not segment.strip():
            continue
        if "=" not in segment:
            raise ValueError(f"Invalid truth value '{segment}'. Expected 'N=STUDENT_ID'.")
        face_no_str, student_id_str = segment.split("=", 1)
        face_no = int(face_no_str.strip())
        student_id = int(student_id_str.strip())
        mapping[face_no] = student_id
    return mapping


def ensure_yunet_model():
    if not YUNET_MODEL.exists():
        print("ERROR: Missing YuNet model file at:", YUNET_MODEL)
        print("Official OpenCV Zoo model directory:")
        print("https://github.com/opencv/opencv_zoo/tree/master/models/face_detection_yunet")
        print("Target path:")
        print(str(YUNET_MODEL))
        raise SystemExit(1)


def load_image(path: Path, max_side: int):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Unable to read image: {path}")

    height, width = image.shape[:2]
    original_size = (width, height)
    if max_side <= 0:
        max_side = max(width, height)

    longest = max(width, height)
    if longest > max_side:
        scale = max_side / longest
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    print(f"Input image: {path}")
    print(f"Original size: {original_size[0]}x{original_size[1]} px")
    print(f"Used size: {image.shape[1]}x{image.shape[0]} px")
    return image


def _contained_ratio(inner_box: tuple[int, int, int, int], outer_box: tuple[int, int, int, int]) -> float:
    inner_x, inner_y, inner_right, inner_bottom = inner_box
    outer_x, outer_y, outer_right, outer_bottom = outer_box
    overlap_left = max(inner_x, outer_x)
    overlap_top = max(inner_y, outer_y)
    overlap_right = min(inner_right, outer_right)
    overlap_bottom = min(inner_bottom, outer_bottom)
    overlap_w = max(0, overlap_right - overlap_left)
    overlap_h = max(0, overlap_bottom - overlap_top)
    overlap_area = overlap_w * overlap_h
    inner_area = max(0, inner_right - inner_x) * max(0, inner_bottom - inner_y)
    if inner_area == 0:
        return 0.0
    return overlap_area / inner_area


def detect_yunet_faces(image: np.ndarray, score_threshold: float, min_face_px: int = 0):
    height, width = image.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(YUNET_MODEL),
        "",
        (width, height),
        0.05,
        0.3,
        5000,
    )
    detector.setInputSize((width, height))
    _, faces = detector.detect(image)

    raw_count = 0 if faces is None else int(len(faces))
    print(f"Raw YuNet detections before score threshold: {raw_count}")
    if faces is None:
        return []

    detections = []
    for face in np.asarray(faces, dtype=np.float32):
        if face.size < 5:
            continue
        x, y, box_w, box_h = [float(v) for v in face[:4]]
        score = float(face[-1])
        if score < score_threshold:
            continue

        shorter_side = min(float(box_w), float(box_h))
        status = "TOO_SMALL" if min_face_px > 0 and shorter_side < min_face_px else "OK"
        detections.append({
            "x": int(round(x)),
            "y": int(round(y)),
            "box_w": int(round(box_w)),
            "box_h": int(round(box_h)),
            "score": float(score),
            "status": status,
            "shorter_side": shorter_side,
        })

    detections.sort(key=lambda item: item["score"], reverse=True)

    kept = []
    for detection in detections:
        det_box = (
            detection["x"],
            detection["y"],
            detection["x"] + detection["box_w"],
            detection["y"] + detection["box_h"],
        )
        suppressed = False
        for kept_detection in kept:
            kept_box = (
                kept_detection["x"],
                kept_detection["y"],
                kept_detection["x"] + kept_detection["box_w"],
                kept_detection["y"] + kept_detection["box_h"],
            )
            iou = 0.0
            inter_left = max(det_box[0], kept_box[0])
            inter_top = max(det_box[1], kept_box[1])
            inter_right = min(det_box[2], kept_box[2])
            inter_bottom = min(det_box[3], kept_box[3])
            inter_w = max(0, inter_right - inter_left)
            inter_h = max(0, inter_bottom - inter_top)
            inter_area = inter_w * inter_h
            det_area = max(1, detection["box_w"] * detection["box_h"])
            kept_area = max(1, kept_detection["box_w"] * kept_detection["box_h"])
            union_area = det_area + kept_area - inter_area
            if union_area > 0:
                iou = inter_area / union_area
            if iou > 0.3:
                suppressed = True
                break
            if _contained_ratio(det_box, kept_box) > 0.70:
                suppressed = True
                break
        if not suppressed:
            kept.append(detection)

    kept.sort(key=lambda item: (item["y"], item["x"]))
    return kept


def crop_with_margin(image: np.ndarray, x: int, y: int, box_w: int, box_h: int, margin_ratio: float = 0.20):
    margin_x = int(round(box_w * margin_ratio))
    margin_y = int(round(box_h * margin_ratio))
    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)
    x2 = min(image.shape[1], x + box_w + margin_x)
    y2 = min(image.shape[0], y + box_h + margin_y)
    return image[y1:y2, x1:x2]


def blur_score(gray_crop: np.ndarray):
    if gray_crop.size == 0:
        return 0.0
    return float(cv2.Laplacian(gray_crop, cv2.CV_32F).var())


def gather_registered_candidates():
    db_path = Path(__file__).resolve().parents[1] / "smart_attendance.db"
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at: {db_path}")

    sqlite_uri = f"{db_path.as_uri()}?mode=ro"
    conn = sqlite3.connect(sqlite_uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT s.id AS student_id,
                   s.roll_number,
                   s.name,
                   fd.face_embedding
            FROM face_data fd
            JOIN students s ON s.id = fd.student_id
            ORDER BY s.id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    candidates = []
    for row in rows:
        embedding = deserialize_embedding(row["face_embedding"], dtype="float32", length=4096)
        candidates.append({
            "student_id": int(row["student_id"]),
            "roll_number": row["roll_number"],
            "name": row["name"],
            "embedding": embedding,
        })
    return candidates


def run_media_pipe_check(image_bytes: bytes):
    try:
        detection = detect_single_face(image_bytes)
        face_count = int(detection.get("face_count", 0))
        return face_count, detection
    except Exception as exc:  # pragma: no cover - calibration diagnostics
        return None, {"error": f"{type(exc).__name__}: {exc}"}


def deepface_haar_found(crop: np.ndarray):
    temp_path = None
    try:
        suffix = ".jpg"
        with open("_tmp_calibration_face.jpg", "wb") as tmp:
            ok, encoded = cv2.imencode(suffix, crop)
            if not ok:
                return False, "cv2.imencode failed for DeepFace crop diagnostic"
            tmp.write(encoded.tobytes())
            temp_path = tmp.name

        result = DeepFace.represent(
            img_path=temp_path,
            detector_backend="opencv",
            enforce_detection=True,
        )
        if not result or not isinstance(result, list):
            return False, "DeepFace returned no face list"
        return True, None
    except Exception as exc:  # pragma: no cover - calibration diagnostics
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink(missing_ok=True)


def select_best(results):
    ranked = sorted(results, key=lambda entry: entry["similarity"], reverse=True)
    if not ranked:
        return None, None, None, None
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    return best, second, best["similarity"], (best["similarity"] - second["similarity"]) if second else 0.0


def print_table_header():
    header = (
        f"{ 'face#':>4} | {'box_w x box_h':>12} | {'yolo/yunet':>10} | {'blur':>10} | {'haar_found':>10} | "
        f"{'best':>6} | {'best_score':>10} | {'2nd':>6} | {'2nd_score':>10} | {'margin':>8} | {'seconds':>8}"
    )
    print()
    print("compare_embeddings() uses cosine SIMILARITY (higher is better).")
    print("MATCH_THRESHOLD = 0.58 is applied as: accepted if best_score >= 0.58.")
    print("Margin is best_score - second_best_score, with higher numbers better.")
    print(header)
    print("-" * len(header))


def main():
    parser = argparse.ArgumentParser(description="Calibration for group-photo face recognition")
    parser.add_argument("--image", required=True, help="Path to the group photo to analyze.")
    parser.add_argument("--score-threshold", type=float, default=0.6, help="Minimum YuNet confidence threshold (default: 0.6).")
    parser.add_argument("--max-side", type=int, default=1600, help="Downscale so longest side is at most this value. Do not upscale below the original image size.")
    parser.add_argument("--min-face-px", type=int, default=0, help="Discard small faces below this minimum shorter-side threshold (default: 0).")
    parser.add_argument("--truth", default=None, help='Optional mapping like "1=STUDENT_ID,3=STUDENT_ID".')
    args = parser.parse_args()

    ensure_yunet_model()
    truth_map = parse_truth(args.truth)

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    image = load_image(image_path, args.max_side)
    yunet_faces = detect_yunet_faces(image, args.score_threshold, min_face_px=args.min_face_px)
    if not yunet_faces:
        print("No faces were detected by YuNet above the requested threshold and minimum-size filter.")
        return 0

    original_bytes = cv2.imencode(".jpg", cv2.imread(str(image_path), cv2.IMREAD_COLOR))[1].tobytes()
    media_pipe_count, media_pipe_debug = run_media_pipe_check(original_bytes)
    if media_pipe_count is None:
        print("MediaPipe detect_single_face() raised an exception:")
        print(media_pipe_debug["error"])
    else:
        print(f"MediaPipe count on full image: {media_pipe_count}")

    all_candidates = gather_registered_candidates()
    if not all_candidates:
        print("No registered face embeddings were found in the database.")
        return 0

    print(f"Students with FaceData rows: {len(all_candidates)}")
    print("FaceData students: " + ", ".join(
        f"({candidate['student_id']}, {candidate['roll_number']})" for candidate in all_candidates
    ))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crops_dir = OUTPUT_DIR / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    print(f"Crops folder: {crops_dir}")
    annotated = image.copy()
    face_rows = []

    print_table_header()
    for index, face in enumerate(yunet_faces, start=1):
        x = face["x"]
        y = face["y"]
        box_w = face["box_w"]
        box_h = face["box_h"]
        score = face["score"]
        face_status = face["status"]
        if face_status == "TOO_SMALL":
            print(
                f"{index:>4} | {box_w:>4}x{box_h:<4} | {score:>10.4f} | TOO_SMALL | SKIPPED |"
            )
            continue

        crop = crop_with_margin(image, x, y, box_w, box_h, margin_ratio=0.20)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur = blur_score(gray)

        crop_path = crops_dir / f"face_{index:02d}.jpg"
        cv2.imwrite(str(crop_path), crop)

        crop_bytes = cv2.imencode(".jpg", crop)[1].tobytes()
        start = time.perf_counter()
        crop_embedding = generate_embedding(crop_bytes)
        elapsed = time.perf_counter() - start

        haar_found, deepface_error = deepface_haar_found(crop)

        scored_candidates = []
        for candidate in all_candidates:
            similarity = compare_embeddings(crop_embedding, candidate["embedding"])
            scored_candidates.append({
                "student_id": candidate["student_id"],
                "roll_number": candidate["roll_number"],
                "name": candidate["name"],
                "similarity": float(similarity),
            })

        best, second, best_score, margin = select_best(scored_candidates)
        if best is None:
            best_student_id = None
            best_roll = "-"
            best_name = "-"
            best_score = 0.0
            second_student_id = None
            second_roll = "-"
            second_name = "-"
            second_score = 0.0
            margin = 0.0
        else:
            best_student_id = int(best["student_id"])
            best_roll = best["roll_number"]
            best_name = best["name"]
            best_score = float(best["similarity"])
            if second is None:
                second_student_id = None
                second_roll = "-"
                second_name = "-"
                second_score = 0.0
            else:
                second_student_id = int(second["student_id"])
                second_roll = second["roll_number"]
                second_name = second["name"]
                second_score = float(second["similarity"])
                margin = float(best_score - second_score)

        expected_student_id = truth_map.get(index)
        if expected_student_id is not None:
            label = "TRUE_MATCH" if best_student_id == expected_student_id else "FALSE_MATCH"
        else:
            label = "EXPECTED_UNKNOWN"

        row = {
            "face_no": index,
            "box_w": box_w,
            "box_h": box_h,
            "score": score,
            "blur": blur,
            "haar_found": True if haar_found else False,
            "best_student_id": best_student_id,
            "best_roll": best_roll,
            "best_name": best_name,
            "best_score": best_score,
            "second_student_id": second_student_id,
            "second_roll": second_roll,
            "second_name": second_name,
            "second_score": second_score,
            "margin": margin,
            "seconds": elapsed,
            "label": label,
            "deepface_error": deepface_error,
        }
        face_rows.append(row)

        cv2.rectangle(annotated, (x, y), (x + box_w, y + box_h), (0, 255, 0), 2)
        cv2.putText(annotated, str(index), (x, max(0, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if best_student_id is None:
            best_text = "-"
            best_score_text = "-"
        else:
            best_text = f"{best_student_id}"
            best_score_text = f"{best_score:.4f}"
        if second_student_id is None:
            second_text = "-"
            second_score_text = "-"
        else:
            second_text = f"{second_student_id}"
            second_score_text = f"{second_score:.4f}"

        print(
            f"{index:>4} | {box_w:>4}x{box_h:<4} | {score:>10.2f} | {blur:>10.2f} | {str(haar_found):>10} | "
            f"{best_text:>6} | {best_score_text:>10} | {second_text:>6} | {second_score_text:>10} | {margin:>8.4f} | {elapsed:>8.4f} | {label}"
        )

    print()
    print("Summary")
    print("-------")
    print(f"YuNet faces detected: {len(yunet_faces)}")
    if media_pipe_count is None:
        print("MediaPipe count: ERROR (detect_single_face raised)")
    else:
        print(f"MediaPipe count on full image: {media_pipe_count}")
    matched_count = sum(1 for row in face_rows if row["best_score"] >= MATCH_THRESHOLD)
    print(f"Detected faces that would match at threshold {MATCH_THRESHOLD}: {matched_count}")

    unknown_scores = [row["best_score"] for row in face_rows if row["label"] == "EXPECTED_UNKNOWN"]
    if unknown_scores:
        print("EXPECTED_UNKNOWN best-score distribution: "
              f"min={min(unknown_scores):.4f}, median={median(unknown_scores):.4f}, max={max(unknown_scores):.4f}")
    else:
        print("EXPECTED_UNKNOWN best-score distribution: no unknown faces to summarize")

    true_match_rows = [row for row in face_rows if row["label"] == "TRUE_MATCH"]
    if true_match_rows:
        print("TRUE_MATCH best scores:")
        for row in true_match_rows:
            print(f"  face#{row['face_no']} -> student {row['best_student_id']} ({row['best_roll']}): {row['best_score']:.4f}")
    else:
        print("TRUE_MATCH best scores: none")

    cv2.imwrite(str(OUTPUT_PATH), annotated)
    print(f"Annotated image saved to: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - script debugging path
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
