# Face recognition

## Registration

`POST /students/{student_id}/face-registration` accepts an uploaded multipart file and is HOD-only. The route first checks that the target student belongs to the HOD's department. `detect_single_face` decodes the image with OpenCV and runs MediaPipe Tasks' FaceDetector using the BlazeFace short-range TFLite asset at a 0.5 minimum detection confidence.

Zero faces and multiple faces are rejected. For one detected face, `generate_embedding` calls `DeepFace.represent` with `detector_backend="opencv"` and `enforce_detection=False`. No `model_name` is supplied explicitly by this code path. The embedding is converted to float32 bytes by `serialize_embedding` and stored in `face_data.face_embedding`. There is one `FaceData` row per student; a later registration replaces that row's embedding. The endpoint processes one uploaded sample per request; it does not average a set of samples.

Faculty registration uses the same detector, embedding, and serialization helpers, but writes to the separate `faculty_face_data` table. HOD can register a faculty member in the same department with `POST /faculty/{faculty_id}/face-registration`; FACULTY can register or replace only their own embedding with `POST /faculty/me/face-registration`. HOD can read registration status with `GET /faculty/{faculty_id}/face-registration-status`. Registration still requires exactly one detected face. Faculty embeddings are not used by the attendance recognition endpoint; faculty recognition is not implemented.

## Recognition during attendance

`POST /attendance-sessions/{session_id}/recognize` accepts a multipart `file`. It requires HOD or FACULTY, verifies session department/faculty ownership, and rejects closed sessions. The same MediaPipe single-face check is applied:

- No detected face: `matched=false`, confidence 0, and a no-face message.
- More than one face: `matched=false`, confidence 0, and a request for a single-face image.
- Exactly one face: DeepFace produces the captured embedding. The route loads stored embeddings only for students in the session's academic year, deserializes each as 4096 float32 values, and selects the highest cosine similarity.

`MATCH_THRESHOLD` is `0.58` in `backend/app/services/face_service.py`. The route accepts the best match when its score is at least this threshold. The threshold is hard-coded; it is not an environment/config setting. The matcher uses a best-score threshold and does not apply a second-best margin test.

The JSON response has `matched`, `student_id`, `student_name`, `confidence`, and `message`. Recognition does not write attendance. The operator uses the manual `POST /attendance-sessions/{session_id}/mark` workflow to record attendance after reviewing the result.

## Known limitation

`docs/testing_notes_phase10.md` records that different-person scores in the tested data were well below threshold (approximately 0.39 versus 0.58), but same-person captures under genuinely different camera angles, lighting, and expressions have not been validated. Earlier positive checks used exact or near-identical images; that does not establish live classroom robustness. Threshold suitability must therefore be treated as unverified for real-world varied captures.
