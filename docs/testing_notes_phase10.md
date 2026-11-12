# Phase 10 face-recognition testing notes

## Current status

This project has verified the safety-critical false-positive behavior for the face matching pipeline:

- Different-person embedding comparisons are well below the current MATCH_THRESHOLD.
- In the real tests run against the project data, the different-person cosine similarity score was approximately 0.39, while MATCH_THRESHOLD is 0.58.
- This means the system is currently showing strong separation between genuinely different people and is unlikely to produce false positives under the tested conditions.

## Important limitation

The same-person case has not yet been validated with a genuinely different capture of the same person taken under different conditions (angle, lighting, expression, etc.).

The project currently only has exact-duplicate or near-identical same-person images for positive checks; for example, the earlier same-person tests used the exact same registration image, which confirms the pipeline can match identical bytes but does not prove the real-world live-camera scenario is stable enough at different capture angles or lighting.

This should be treated as a known testing limitation until Phase 10b's live camera capture is available and can be validated in person against registered students.

## Recommendation

When Phase 10b is implemented, test these real-world scenarios:

1. Register a student from a normal enrollment photo.
2. Open a live camera session in class.
3. Capture a different frame of the same student under class lighting and angle.
4. Confirm cosine similarity remains comfortably above MATCH_THRESHOLD.
5. Capture a different person and confirm they remain below threshold.

If the same-person-different-capture score drifts too close to the threshold, the threshold should be tuned empirically and the system should be revalidated before production use.
