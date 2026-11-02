import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

export default function AttendanceSessionPage() {
  const { token, role, faculty_id } = useAuth();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [academicYears, setAcademicYears] = useState([]);
  const [selectedYearId, setSelectedYearId] = useState('');
  const [timetableEntries, setTimetableEntries] = useState([]);
  const [selectedEntryId, setSelectedEntryId] = useState('');
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState('');
  const [studentsForYear, setStudentsForYear] = useState([]);
  const [manualStudentId, setManualStudentId] = useState('');
  const [markedStudents, setMarkedStudents] = useState([]);
  const [loadingYears, setLoadingYears] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingEntries, setLoadingEntries] = useState(false);
  const [startingSession, setStartingSession] = useState(false);
  const [recognizing, setRecognizing] = useState(false);
  const [submittingMark, setSubmittingMark] = useState(false);
  const [closingSession, setClosingSession] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [capturedImageUrl, setCapturedImageUrl] = useState('');
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [recognitionResult, setRecognitionResult] = useState(null);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [sessionCloseResult, setSessionCloseResult] = useState(null);

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    return () => {
      if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
      }
      stopCamera();
    };
  }, [capturedImageUrl]);

  const fetchAcademicYears = async () => {
    if (!token) return;

    try {
      const response = await api.get('/academic-years');
      const years = response.data || [];
      setAcademicYears(years);
      if (years.length > 0) {
        setSelectedYearId(String(years[0].id));
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load academic years.');
    } finally {
      setLoadingYears(false);
    }
  };

  const fetchOpenSessions = async () => {
    if (!token) return;

    try {
      const response = await api.get('/attendance-sessions?status=OPEN');
      const openSessions = response.data || [];
      setSessions(openSessions);
      if (openSessions.length > 0 && !selectedSessionId) {
        setSelectedSessionId(String(openSessions[0].id));
      }
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load open sessions.');
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => {
    fetchAcademicYears();
    fetchOpenSessions();
  }, [token]);

  useEffect(() => {
    const loadEntries = async () => {
      if (!selectedYearId || !token) {
        setTimetableEntries([]);
        setSelectedEntryId('');
        return;
      }

      setLoadingEntries(true);
      try {
        const response = await api.get(`/timetable/year/${selectedYearId}`);
        const entries = response.data || [];
        const filtered = role === 'FACULTY' ? entries.filter((entry) => Number(entry.faculty_id) === Number(faculty_id)) : entries;
        setTimetableEntries(filtered);
        if (filtered.length > 0) {
          setSelectedEntryId(String(filtered[0].id));
        } else {
          setSelectedEntryId('');
        }
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to load timetable entries.');
        setTimetableEntries([]);
      } finally {
        setLoadingEntries(false);
      }
    };

    loadEntries();
  }, [selectedYearId, token, role, faculty_id]);

  useEffect(() => {
    const activeSession = sessions.find((session) => String(session.id) === String(selectedSessionId));
    if (!activeSession) {
      setStudentsForYear([]);
      setManualStudentId('');
      return;
    }

    const loadYearStudents = async () => {
      try {
        const response = await api.get(`/students?academic_year_id=${activeSession.academic_year_id}`);
        const studentList = response.data || [];
        setStudentsForYear(studentList);
        if (studentList.length > 0) {
          setManualStudentId(String(studentList[0].id));
        } else {
          setManualStudentId('');
        }
      } catch (err) {
        setStudentsForYear([]);
        setManualStudentId('');
      }
    };

    loadYearStudents();
  }, [selectedSessionId, sessions]);

  useEffect(() => {
    if (videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {
        setError('Unable to start the camera preview.');
      });
    }
  }, [cameraActive]);

  const startCamera = async () => {
    setError('');
    setSuccessMessage('');

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = mediaStream;
      setCameraActive(true);
    } catch (err) {
      setError('Unable to access the camera. Please allow camera access and try again.');
    }
  };

  const resetCapture = () => {
    setRecognitionResult(null);
    setCapturedBlob(null);
    if (capturedImageUrl) {
      URL.revokeObjectURL(capturedImageUrl);
    }
    setCapturedImageUrl('');
    setError('');
    setSuccessMessage('');
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
        setError('Failed to capture the image. Please try again.');
        return;
      }

      if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
      }

      setCapturedBlob(blob);
      setCapturedImageUrl(URL.createObjectURL(blob));
      setRecognitionResult(null);
      setError('');
      setSuccessMessage('');
    }, 'image/jpeg', 0.92);
  };

  const handleRecognize = async () => {
    if (!selectedSessionId || !capturedBlob) {
      setError('Capture a face before recognition.');
      return;
    }

    const formData = new FormData();
    formData.append('file', capturedBlob, 'attendance-recognition.jpg');

    setRecognizing(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await api.post(`/attendance-sessions/${selectedSessionId}/recognize`, formData, {
        headers: {
          'Content-Type': undefined,
        },
      });
      setRecognitionResult(response.data);
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || 'Recognition failed.';
      setError(detail);
    } finally {
      setRecognizing(false);
    }
  };

  const handleMarkPresent = async (studentId) => {
    if (!selectedSessionId) return;

    setSubmittingMark(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await api.post(`/attendance-sessions/${selectedSessionId}/mark`, { student_id: Number(studentId) });
      const studentName = studentsForYear.find((student) => Number(student.id) === Number(studentId))?.name || `Student ${studentId}`;
      setMarkedStudents((existing) => {
        if (existing.some((item) => Number(item.student_id) === Number(studentId))) {
          return existing;
        }
        return [...existing, { student_id: Number(studentId), name: studentName }];
      });
      setSuccessMessage(`Marked present: ${studentName}`);
      setRecognitionResult(null);
      setCapturedBlob(null);
      if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
      }
      setCapturedImageUrl('');
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to mark attendance.';
      setError(detail);
    } finally {
      setSubmittingMark(false);
    }
  };

  const handleCloseSession = async () => {
    if (!selectedSessionId) return;

    setClosingSession(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await api.put(`/attendance-sessions/${selectedSessionId}/close`);
      setSessionCloseResult(response.data);
      setSuccessMessage(`Session closed. Absent rows backfilled: ${response.data.absent_marked_count ?? 0}`);
      const updatedSessions = sessions.filter((session) => String(session.id) !== String(selectedSessionId));
      setSessions(updatedSessions);
      setSelectedSessionId(updatedSessions[0] ? String(updatedSessions[0].id) : '');
      setRecognitionResult(null);
      setCapturedBlob(null);
      if (capturedImageUrl) {
        URL.revokeObjectURL(capturedImageUrl);
      }
      setCapturedImageUrl('');
      stopCamera();
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to close session.';
      setError(detail);
    } finally {
      setClosingSession(false);
    }
  };

  const startNewSession = async () => {
    if (!selectedEntryId) {
      setError('Select a timetable entry before starting a session.');
      return;
    }

    setStartingSession(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await api.post('/attendance-sessions', { timetable_entry_id: Number(selectedEntryId) });
      const nextSession = response.data;
      setSessions((existing) => [nextSession, ...existing]);
      setSelectedSessionId(String(nextSession.id));
      setSuccessMessage('Attendance session started.');
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to start attendance session.';
      setError(detail);
    } finally {
      setStartingSession(false);
    }
  };

  const activeSession = sessions.find((session) => String(session.id) === String(selectedSessionId));
  const activeSessionYear = academicYears.find((year) => Number(year.id) === Number(activeSession?.academic_year_id));
  const activeSessionYearLabel = activeSessionYear
    ? `${activeSessionYear.name} (ID: ${activeSessionYear.id})`
    : activeSession?.academic_year_id
      ? `Academic year ID ${activeSession.academic_year_id}`
      : 'Unknown academic year';

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '24px' }}>
      <h2>Attendance Session</h2>

      {loadingSessions || loadingYears ? (
        <p>Loading session data...</p>
      ) : null}

      {!loadingSessions && !loadingYears && (!sessions.length || !activeSession) ? (
        <div style={{ marginBottom: '24px', padding: '16px', border: '1px solid #d1d5db', borderRadius: '10px' }}>
          <h3>No open session</h3>
          <div style={{ display: 'grid', gap: '12px', maxWidth: '420px' }}>
            <div>
              <label htmlFor="year-selector" style={{ display: 'block', fontWeight: 600, marginBottom: '8px' }}>Academic year</label>
              <select id="year-selector" value={selectedYearId} onChange={(event) => setSelectedYearId(event.target.value)} style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #d1d5db' }}>
                <option value="">Select a year</option>
                {academicYears.map((year) => (
                  <option key={year.id} value={year.id}>{year.name} (ID: {year.id})</option>
                ))}
              </select>
              {selectedYearId ? (
                <p style={{ margin: '8px 0 0', fontSize: '13px', color: '#4b5563' }}>
                  Selected year: {academicYears.find((year) => Number(year.id) === Number(selectedYearId))?.name || 'Unknown'} (ID: {selectedYearId})
                </p>
              ) : null}
            </div>

            {loadingEntries ? <p>Loading timetable entries...</p> : null}

            {!loadingEntries && timetableEntries.length > 0 ? (
              <div>
                <label htmlFor="entry-selector" style={{ display: 'block', fontWeight: 600, marginBottom: '8px' }}>Timetable entry</label>
                <select id="entry-selector" value={selectedEntryId} onChange={(event) => setSelectedEntryId(event.target.value)} style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #d1d5db' }}>
                  <option value="">Select a timetable entry</option>
                  {timetableEntries.map((entry) => (
                    <option key={entry.id} value={entry.id}>{entry.subject_name} • {entry.day} {entry.period}</option>
                  ))}
                </select>
              </div>
            ) : null}

            {!loadingEntries && timetableEntries.length === 0 && selectedYearId ? (
              <p>No timetable entries are available for this year.</p>
            ) : null}

            <button type="button" onClick={startNewSession} disabled={startingSession || !selectedEntryId} style={{ width: 'fit-content', padding: '10px 18px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: startingSession || !selectedEntryId ? 'not-allowed' : 'pointer' }}>
              {startingSession ? 'Starting session...' : 'Start session'}
            </button>
          </div>
        </div>
      ) : null}

      {sessions.length > 0 ? (
        <div style={{ marginBottom: '24px' }}>
          <label htmlFor="session-select" style={{ display: 'block', fontWeight: 600, marginBottom: '8px' }}>Open session</label>
          <select
            id="session-select"
            value={selectedSessionId}
            onChange={(event) => {
              setSelectedSessionId(event.target.value);
              setRecognitionResult(null);
              setCapturedBlob(null);
              if (capturedImageUrl) {
                URL.revokeObjectURL(capturedImageUrl);
              }
              setCapturedImageUrl('');
            }}
            style={{ width: '100%', maxWidth: '420px', padding: '8px 10px', borderRadius: '6px', border: '1px solid #d1d5db' }}
          >
            {sessions.map((session) => (
              <option key={session.id} value={session.id}>{session.subject_id} • {session.date} • {session.status}</option>
            ))}
          </select>
        </div>
      ) : null}

      {activeSession ? (
        <div style={{ marginBottom: '16px', padding: '12px 16px', border: '1px solid #dbeafe', borderRadius: '10px', background: '#eff6ff' }}>
          <strong>Session for:</strong> {activeSessionYearLabel}
        </div>
      ) : null}

      {activeSession ? (
        <div style={{ display: 'grid', gap: '20px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="button" onClick={startCamera} disabled={cameraActive} style={{ padding: '10px 18px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '6px', cursor: cameraActive ? 'not-allowed' : 'pointer' }}>
              Open Camera
            </button>
            <button type="button" onClick={handleCloseSession} disabled={closingSession} style={{ padding: '10px 18px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '6px', cursor: closingSession ? 'not-allowed' : 'pointer' }}>
              {closingSession ? 'Closing...' : 'Close Session'}
            </button>
          </div>

          {sessionCloseResult ? <p style={{ color: '#15803d', margin: 0 }}>Session closed. Absent rows backfilled: {sessionCloseResult.absent_marked_count ?? 0}</p> : null}

          {cameraActive && !capturedImageUrl ? (
            <div>
              <video ref={videoRef} autoPlay playsInline muted style={{ width: '100%', maxWidth: '640px', borderRadius: '12px', background: '#111827' }} />
              <div style={{ marginTop: '12px', display: 'flex', gap: '12px' }}>
                <button type="button" onClick={handleCapture} style={{ padding: '10px 18px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                  Capture & Recognize
                </button>
                <button type="button" onClick={stopCamera} style={{ padding: '10px 18px', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                  Stop Camera
                </button>
              </div>
            </div>
          ) : null}

          {capturedImageUrl ? (
            <div>
              <img src={capturedImageUrl} alt="Captured recognition preview" style={{ width: '100%', maxWidth: '640px', borderRadius: '12px', border: '1px solid #d1d5db' }} />
              <div style={{ marginTop: '12px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <button type="button" onClick={handleRecognize} disabled={recognizing} style={{ padding: '10px 18px', background: '#111827', color: '#fff', border: 'none', borderRadius: '6px', cursor: recognizing ? 'not-allowed' : 'pointer' }}>
                  {recognizing ? 'Recognizing...' : 'Recognize'}
                </button>
                <button type="button" onClick={resetCapture} style={{ padding: '10px 18px', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                  Retake
                </button>
              </div>
            </div>
          ) : null}

          <canvas ref={canvasRef} style={{ display: 'none' }} />

          {recognitionResult ? (
            <div style={{ padding: '16px', border: '1px solid #d1d5db', borderRadius: '10px', background: '#f9fafb' }}>
              {recognitionResult.matched ? (
                <div>
                  <p style={{ marginTop: 0, marginBottom: '12px', fontWeight: 700 }}>
                    Student recognized: {recognitionResult.student_name}
                  </p>
                  <p style={{ marginTop: 0, marginBottom: '12px' }}>Confidence: {Number(recognitionResult.confidence).toFixed(4)}</p>
                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    <button type="button" onClick={() => handleMarkPresent(recognitionResult.student_id)} disabled={submittingMark} style={{ padding: '10px 18px', background: '#15803d', color: '#fff', border: 'none', borderRadius: '6px', cursor: submittingMark ? 'not-allowed' : 'pointer' }}>
                      {submittingMark ? 'Marking...' : 'Confirm & Mark Present'}
                    </button>
                    <button type="button" onClick={() => { setRecognitionResult(null); setError(''); setSuccessMessage(''); }} style={{ padding: '10px 18px', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                      Reject / Retake
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <p style={{ marginTop: 0, marginBottom: '12px' }}>{recognitionResult.message}</p>
                  <p style={{ marginTop: 0, marginBottom: '12px' }}>Confidence: {Number(recognitionResult.confidence).toFixed(4)}</p>
                  {studentsForYear.length > 0 ? (
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                      <select value={manualStudentId} onChange={(event) => setManualStudentId(event.target.value)} style={{ padding: '8px 10px', minWidth: '220px', borderRadius: '6px', border: '1px solid #d1d5db' }}>
                        {studentsForYear.map((student) => (
                          <option key={student.id} value={student.id}>{student.name} ({student.roll_number})</option>
                        ))}
                      </select>
                      <button type="button" onClick={() => handleMarkPresent(manualStudentId)} disabled={!manualStudentId || submittingMark} style={{ padding: '10px 18px', background: '#111827', color: '#fff', border: 'none', borderRadius: '6px', cursor: !manualStudentId || submittingMark ? 'not-allowed' : 'pointer' }}>
                        {submittingMark ? 'Marking...' : 'Mark Present Manually'}
                      </button>
                    </div>
                  ) : (
                    <p>No students are available for manual fallback in this academic year.</p>
                  )}
                  <div style={{ marginTop: '12px' }}>
                    <button type="button" onClick={() => { setRecognitionResult(null); setError(''); setSuccessMessage(''); }} style={{ padding: '10px 18px', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                      Retake
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {error ? <p style={{ color: '#b91c1c', margin: 0 }}>{error}</p> : null}
          {successMessage ? <p style={{ color: '#15803d', margin: 0 }}>{successMessage}</p> : null}

          <div style={{ padding: '16px', border: '1px solid #d1d5db', borderRadius: '10px' }}>
            <h3>Marked present</h3>
            {markedStudents.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '18px' }}>
                {markedStudents.map((student) => (
                  <li key={student.student_id}>{student.name}</li>
                ))}
              </ul>
            ) : (
              <p style={{ margin: 0 }}>No one has been marked present yet.</p>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
