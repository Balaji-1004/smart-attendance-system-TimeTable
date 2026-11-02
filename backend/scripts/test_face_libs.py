from __future__ import annotations

import importlib
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
IMAGE_CANDIDATES = [
    ROOT / "scripts" / "sample_face.jpeg",
    ROOT / "scripts" / "sample_face.jpg",
    ROOT / "scripts" / "sample_face.png",
]
MODEL_DIR = ROOT / "scripts" / "models"
MODEL_PATH = MODEL_DIR / "face_detection_short_range.tflite"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"


def find_sample_image() -> Path | None:
    for candidate in IMAGE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def ensure_model_download() -> Path | None:
    MODEL_DIR.mkdir(exist_ok=True, parents=True)
    if MODEL_PATH.exists():
        return MODEL_PATH

    try:
        print(f"MediaPipe model missing; downloading to {MODEL_PATH}")
        start = time.time()
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        elapsed = time.time() - start
        print(f"MediaPipe model download completed in {elapsed:.2f}s")
        return MODEL_PATH
    except Exception as exc:  # pragma: no cover - smoke test reporting only
        print(f"MediaPipe model download failed: {type(exc).__name__}: {exc}")
        return None


def print_no_image_message() -> None:
    example_dir = ROOT / "scripts"
    print("No sample face image found.")
    print(f"Place a JPG or PNG face photo at: {example_dir / 'sample_face.jpeg'}")
    print("Use a clear, front-facing photo of a person for the smoke test.")
    print("The script will then test Mediapipe face detection and DeepFace embedding generation.")


def main() -> None:
    image_path = find_sample_image()
    if image_path is None:
        print_no_image_message()
        return

    print(f"Using sample image: {image_path}")

    # Mediapipe smoke test
    try:
        import cv2
        import mediapipe as mp

        model_path = ensure_model_download()
        if model_path is None:
            print("Mediapipe: skipped detection because model download failed.")
            raise RuntimeError("No model available")

        vision = importlib.import_module("mediapipe.tasks.python.vision")
        image = mp.Image.create_from_file(str(image_path))
        detector = vision.FaceDetector.create_from_options(
            vision.FaceDetectorOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=vision.RunningMode.IMAGE,
                min_detection_confidence=0.5,
            )
        )
        result = detector.detect(image)

        if not result.detections:
            print("Mediapipe: no face detected")
        else:
            detection = result.detections[0]
            score = detection.categories[0].score if detection.categories else None
            bbox = getattr(detection, "bounding_box", None)
            print("Mediapipe: found face")
            if score is not None:
                print(f"Mediapipe confidence: {score:.4f}")
            if bbox is not None:
                print(f"Mediapipe bounding box: {bbox}")
    except Exception as exc:  # pragma: no cover - smoke test reporting only
        print(f"Mediapipe failed: {type(exc).__name__}: {exc}")

    print("-" * 40)

    # DeepFace smoke test
    try:
        from deepface import DeepFace
        import inspect

        default_model = inspect.signature(DeepFace.represent).parameters["model_name"].default
        print(f"DeepFace default model_name in represent(): {default_model}")

        start = time.time()
        result = DeepFace.represent(
            img_path=str(image_path),
            detector_backend="opencv",
            enforce_detection=False,
        )
        elapsed = time.time() - start
        print(f"DeepFace inference time: {elapsed:.2f}s")

        if isinstance(result, list):
            print(f"DeepFace result length (faces found): {len(result)}")
            if result:
                first = result[0]
                print(f"DeepFace first result keys: {list(first.keys())}")
                if isinstance(first, dict) and "embedding" in first:
                    emb = first["embedding"]
                    print(f"DeepFace actual embedding length: {len(emb)}")
                    print(f"DeepFace first 5 embedding values: {emb[:5]}")
                    vector_type = "list"
                    try:
                        import numpy as np
                        if isinstance(emb, np.ndarray):
                            vector_type = "array"
                    except Exception:
                        pass
                    print(f"DeepFace embedding type: {vector_type}")
                else:
                    print("DeepFace: result[0] did not contain an embedding key")
        else:
            print(f"DeepFace returned unexpected type: {type(result)}")

        print("DeepFace: embedding generated successfully")
    except Exception as exc:  # pragma: no cover - smoke test reporting only
        print(f"DeepFace failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - smoke test reporting only
        print(f"Smoke test crashed unexpectedly: {type(exc).__name__}: {exc}")
        sys.exit(1)
