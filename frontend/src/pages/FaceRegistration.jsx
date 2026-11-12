import { useEffect, useRef, useState } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

export default function FaceRegistration({ mode = 'hod' }) {
  const { token } = useAuth();
  const isSelf = mode === 'self';
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [students, setStudents] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [registrationType, setRegistrationType] = useState('student');
  const selectedType = isSelf ? 'faculty' : registrationType;
  const targets = selectedType === 'student' ? students : faculty;
  const [selectedTargetId, setSelectedTargetId] = useState('');
  const [loadingStudents, setLoadingStudents] = useState(true);
  const [cameraActive, setCameraActive] = useState(false);
  const [capturedImageUrl, setCapturedImageUrl] = useState('');
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [stream, setStream] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    let cancelled = false;

    const fetchTargets = async () => {
      if (isSelf) {
        setLoadingStudents(false);
        return;
      }
      if (!token) {
        setLoadingStudents(false);
        return;
      }

      try {
        const response = await api.get(selectedType === 'student' ? '/students' : '/faculty');
        if (!cancelled) {
          const items = response.data || [];
          if (selectedType === 'student') setStudents(items);
          else setFaculty(items);
          setSelectedTargetId(items.length ? String(items[0].id) : '');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err?.response?.data?.detail || `Failed to load ${selectedType === 'student' ? 'students' : 'faculty'}.`);
        }
      } finally {
        if (!cancelled) {
          setLoadingStudents(false);
        }
      }
    };

    setLoadingStudents(true);
    fetchTargets();

    return () => {
      cancelled = true;
    };
  }, [isSelf, token, selectedType]);

  useEffect(() => {
    const currentStream = stream;
    if (currentStream && videoRef.current) {
      videoRef.current.srcObject = currentStream;
      videoRef.current.play().catch(() => {
        setError('Unable to start the camera preview.');
      });
    }
  }, [stream]);

  useEffect(() => {
    return () => {
      if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
      }
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [capturedImageUrl, stream]);

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
    setCameraActive(false);
  };

  const switchRegistrationType = (type) => {
    setRegistrationType(type);
    setSelectedTargetId('');
    setCapturedBlob(null);
    if (capturedImageUrl) URL.revokeObjectURL(capturedImageUrl);
    setCapturedImageUrl('');
    setError('');
    setSuccessMessage('');
    stopCamera();
  };

  const startCamera = async () => {
    setError('');
    setSuccessMessage('');

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
      setStream(mediaStream);
      setCameraActive(true);
    } catch {
      setError('Unable to access the camera. Please allow camera access and try again.');
      setCameraActive(false);
    }
  };

  const handleCapture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) {
      setError('Camera preview is not ready yet.');
      return;
    }

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext('2d');
    context.drawImage(video, 0, 0, width, height);

    canvas.toBlob((blob) => {
      if (!blob) {
        setError('Failed to capture the image frame. Please try again.');
        return;
      }

      if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
      }

      setCapturedBlob(blob);
      setCapturedImageUrl(URL.createObjectURL(blob));
      setSuccessMessage('');
    }, 'image/jpeg', 0.92);
  };

  const handleRetake = () => {
    if (capturedImageUrl) {
      URL.revokeObjectURL(capturedImageUrl);
    }
    setCapturedBlob(null);
    setCapturedImageUrl('');
    setSuccessMessage('');
    setError('');
  };

  const handleSubmit = async () => {
    if ((!isSelf && !selectedTargetId) || !capturedBlob) {
      setError('Capture a photo before submitting.');
      return;
    }

    const formData = new FormData();
    formData.append('file', capturedBlob, 'face-capture.jpg');

    setSubmitting(true);
    setError('');
    setSuccessMessage('');

    try {
      const endpoint = isSelf
        ? '/faculty/me/face-registration'
        : selectedType === 'faculty'
          ? `/faculty/${selectedTargetId}/face-registration`
          : `/students/${selectedTargetId}/face-registration`;
      const response = await api.post(endpoint, formData, {
        headers: {
          'Content-Type': undefined,
        },
      });
      setSuccessMessage(response.data.message || 'Face registration successful.');
      if (!isSelf && selectedType === 'faculty') {
        setFaculty((items) => items.map((member) => String(member.id) === selectedTargetId
          ? { ...member, face_registered: true }
          : member));
      }
      setCapturedBlob(null);
      if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
      }
      setCapturedImageUrl('');
      stopCamera();
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Face registration failed.';
      setError(detail);
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    if (!selectedTargetId) {
      setCapturedBlob(null);
      setCapturedImageUrl('');
    }
  }, [selectedTargetId]);

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '24px' }}>
      <h2>{isSelf ? 'My Face Registration' : 'Face Registration'}</h2>
      {isSelf ? <p>Register or update the face used to identify your faculty profile.</p> : null}

      {!isSelf ? (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', alignItems: 'center' }}>
          <strong>Register for</strong>
          <button type="button" aria-pressed={selectedType === 'student'} onClick={() => switchRegistrationType('student')} style={{ padding: '8px 14px', border: '1px solid #d1d5db', borderRadius: '6px', background: selectedType === 'student' ? '#dbeafe' : '#fff' }}>
            Student
          </button>
          <button type="button" aria-pressed={selectedType === 'faculty'} onClick={() => switchRegistrationType('faculty')} style={{ padding: '8px 14px', border: '1px solid #d1d5db', borderRadius: '6px', background: selectedType === 'faculty' ? '#dbeafe' : '#fff' }}>
            Faculty
          </button>
        </div>
      ) : null}

      {loadingStudents ? (
        <p>Loading {selectedType}...</p>
      ) : !isSelf ? (
        <div style={{ marginBottom: '20px' }}>
          <label htmlFor="registration-target-select" style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
            Select {selectedType}
          </label>
          <select
            id="registration-target-select"
            value={selectedTargetId}
            onChange={(event) => setSelectedTargetId(event.target.value)}
            style={{ width: '100%', maxWidth: '360px', padding: '10px 12px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          >
            <option value="">Choose a {selectedType}</option>
            {targets.map((target) => (
              <option key={target.id} value={target.id}>
                {selectedType === 'student'
                  ? `${target.name} (${target.roll_number})`
                  : `${target.name}${target.face_registered ? ' (Registered)' : ''}`}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {(isSelf || selectedTargetId) && !loadingStudents ? (
        <div style={{ display: 'grid', gap: '16px' }}>
          {!cameraActive && !capturedImageUrl ? (
            <button type="button" onClick={startCamera} style={{ width: 'fit-content', padding: '10px 18px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
              Open Camera
            </button>
          ) : null}

          {cameraActive && !capturedImageUrl ? (
            <div>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={{ width: '100%', maxWidth: '640px', borderRadius: '12px', background: '#111827' }}
              />
              <div style={{ marginTop: '12px' }}>
                <button type="button" onClick={handleCapture} style={{ padding: '10px 18px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                  Capture
                </button>
              </div>
            </div>
          ) : null}

          {capturedImageUrl ? (
            <div>
              <img src={capturedImageUrl} alt="Captured preview" style={{ width: '100%', maxWidth: '640px', borderRadius: '12px', border: '1px solid #d1d5db' }} />
              <div style={{ marginTop: '12px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button type="button" onClick={handleRetake} style={{ padding: '10px 18px', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                  Retake
                </button>
                <button type="button" onClick={handleSubmit} disabled={submitting} style={{ padding: '10px 18px', background: '#111827', color: '#fff', border: 'none', borderRadius: '6px', cursor: submitting ? 'not-allowed' : 'pointer' }}>
                  {submitting ? 'Submitting...' : 'Submit'}
                </button>
              </div>
            </div>
          ) : null}

          <canvas ref={canvasRef} style={{ display: 'none' }} />

          {error ? <p style={{ color: '#b91c1c', margin: 0 }}>{error}</p> : null}
          {successMessage ? <p style={{ color: '#15803d', margin: 0 }}>{successMessage}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
