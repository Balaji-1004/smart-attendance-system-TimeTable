import sys
import cv2

img = cv2.imread(sys.argv[1])
if img is None:
    sys.exit("Could not read image")
h, w = img.shape[:2]
print("image shape (h, w, channels):", img.shape, "dtype:", img.dtype)

detector = cv2.FaceDetectorYN.create(
    "scripts/models/face_detection_yunet_2023mar.onnx", "", (w, h), 0.05, 0.3, 5000
)
detector.setInputSize((w, h))
_, faces = detector.detect(img)

if faces is None:
    print("raw detections: 0")
else:
    print("raw detections:", len(faces))
    for f in faces:
        x, y, bw, bh = [int(v) for v in f[:4]]
        print(f"box x={x} y={y} w={bw} h={bh} score={float(f[-1]):.2f}")