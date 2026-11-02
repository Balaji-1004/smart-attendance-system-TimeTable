import importlib
import tempfile
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from deepface import DeepFace

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = BACKEND_ROOT / "scripts" / "models"
MODEL_PATH = MODEL_DIR / "face_detection_short_range.tflite"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"

# Tune this threshold based on real-world validation of the deployed model and dataset.
# IMPORTANT: we have verified strong separation between different people in the current test set,
# but same-person captures taken from a live classroom camera under different angles/lighting
# have not yet been validated. Once Phase 10b's live camera workflow is available, this value
# should be re-tested with real same-person vs different-person captures before relying on it in production.
MATCH_THRESHOLD = 0.58


def _ensure_model_download() -> str:
    MODEL_DIR.mkdir(exist_ok=True, parents=True)
    if MODEL_PATH.exists():
        return str(MODEL_PATH)

    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return str(MODEL_PATH)


def detect_single_face(image_bytes: bytes) -> dict:
    if not image_bytes:
        return {"face_count": 0, "bounding_box": None}

    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return {"face_count": 0, "bounding_box": None}

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    import mediapipe as mp

    vision = importlib.import_module("mediapipe.tasks.python.vision")
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

    model_path = _ensure_model_download()
    detector = vision.FaceDetector.create_from_options(
        vision.FaceDetectorOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE,
            min_detection_confidence=0.5,
        )
    )
    result = detector.detect(image)

    if not result.detections:
        return {"face_count": 0, "bounding_box": None}

    if len(result.detections) > 1:
        return {"face_count": len(result.detections), "bounding_box": None}

    bbox = result.detections[0].bounding_box
    return {
        "face_count": 1,
        "bounding_box": {
            "origin_x": bbox.origin_x,
            "origin_y": bbox.origin_y,
            "width": bbox.width,
            "height": bbox.height,
        },
    }


def generate_embedding(image_bytes: bytes) -> np.ndarray:
    with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as temp_file:
        temp_file.write(image_bytes)
        temp_path = temp_file.name

    try:
        result = DeepFace.represent(
            img_path=temp_path,
            detector_backend="opencv",
            enforce_detection=False,
        )
        if not result or not isinstance(result, list):
            raise ValueError("DeepFace did not return a face embedding.")
        embedding = np.asarray(result[0]["embedding"], dtype=np.float32)
        return embedding
    finally:
        Path(temp_path).unlink(missing_ok=True)


def serialize_embedding(embedding: np.ndarray) -> bytes:
    return np.asarray(embedding, dtype=np.float32).tobytes()


def deserialize_embedding(data: bytes, dtype: str = "float32", length: int = 4096) -> np.ndarray:
    np_dtype = np.dtype(dtype)
    return np.frombuffer(data, dtype=np_dtype, count=length).astype(np.float32, copy=False)


def compare_embeddings(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    vec_a = np.asarray(embedding_a, dtype=np.float32).ravel()
    vec_b = np.asarray(embedding_b, dtype=np.float32).ravel()

    if vec_a.size == 0 or vec_b.size == 0 or vec_a.size != vec_b.size:
        return 0.0

    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    cosine_similarity = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    return float(np.clip(cosine_similarity, -1.0, 1.0))


def find_best_match(captured_embedding: np.ndarray, candidate_embeddings: list[tuple[int, np.ndarray]]) -> tuple[int | None, float]:
    if not candidate_embeddings:
        return None, 0.0

    best_student_id = None
    best_similarity = float("-inf")

    for student_id, candidate_embedding in candidate_embeddings:
        similarity = compare_embeddings(captured_embedding, candidate_embedding)
        if similarity > best_similarity:
            best_student_id = student_id
            best_similarity = similarity

    if best_student_id is None:
        return None, 0.0

    return best_student_id, float(best_similarity)
