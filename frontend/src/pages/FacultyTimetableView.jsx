import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import TimetableGrid from '../components/TimetableGrid';
import api from '../services/api';

export default function FacultyTimetableView() {
  const { token, faculty_id } = useAuth();
  const [facultyIdInput, setFacultyIdInput] = useState('');
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const effectiveFacultyId = faculty_id ?? facultyIdInput;

  useEffect(() => {
    if (!token) {
      setError('No auth token was found. Please log in first.');
      return;
    }

    if (!effectiveFacultyId) {
      setError('Faculty ID is not available in the current auth state. Log in as a faculty user or enter a faculty ID manually to test this page.');
      return;
    }

    const fetchFacultyTimetable = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await api.get(`/timetable/faculty/${effectiveFacultyId}`);
        setEntries(response.data || []);
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to load faculty timetable.');
        setEntries([]);
      } finally {
        setLoading(false);
      }
    };

    fetchFacultyTimetable();
  }, [effectiveFacultyId, token]);

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h2>Faculty Timetable</h2>

      {!faculty_id && (
        <div style={{ marginBottom: '12px' }}>
          <label htmlFor="faculty-id-input" style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Enter faculty ID to test manually:</label>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              id="faculty-id-input"
              type="number"
              value={facultyIdInput}
              onChange={(event) => setFacultyIdInput(event.target.value)}
              placeholder="Faculty ID"
              style={{ padding: '8px', minWidth: '180px' }}
            />
          </div>
        </div>
      )}

      {error ? <p style={{ color: '#b91c1c', marginBottom: '16px' }}>{error}</p> : null}
      {loading ? <p>Loading faculty timetable...</p> : null}
      {!loading && entries.length > 0 ? <TimetableGrid entries={entries} /> : null}
      {!loading && !error && entries.length === 0 && effectiveFacultyId ? <p>No timetable entries found for this faculty.</p> : null}
    </div>
  );
}
