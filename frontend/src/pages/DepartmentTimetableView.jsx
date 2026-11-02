import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import TimetableGrid from '../components/TimetableGrid';
import api from '../services/api';

export default function DepartmentTimetableView() {
  const { token } = useAuth();
  const [entriesByYear, setEntriesByYear] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDepartmentTimetable = async () => {
      if (!token) {
        setError('No auth token was found. Log in first.');
        setLoading(false);
        return;
      }

      try {
        const response = await api.get('/timetable/department');

        const grouped = {};
        (response.data || []).forEach((entry) => {
          const key = entry.academic_year_id;
          if (!grouped[key]) {
            grouped[key] = {
              name: entry.academic_year_name || `Academic Year ${entry.academic_year_id}`,
              entries: [],
            };
          }
          grouped[key].entries.push(entry);
        });

        setEntriesByYear(grouped);
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to load department timetable.');
      } finally {
        setLoading(false);
      }
    };

    fetchDepartmentTimetable();
  }, [token]);

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h2>Department Timetable</h2>

      {error ? <p style={{ color: '#b91c1c', marginBottom: '16px' }}>{error}</p> : null}
      {loading ? <p>Loading department timetable...</p> : null}

      {!loading && Object.keys(entriesByYear).length === 0 && !error ? (
        <p>No department timetable entries exist yet.</p>
      ) : null}

      {!loading && Object.entries(entriesByYear).map(([yearId, data]) => (
        <div key={yearId} style={{ marginTop: '24px' }}>
          <h3 style={{ marginBottom: '12px' }}>{data.name}</h3>
          <TimetableGrid entries={data.entries} />
        </div>
      ))}
    </div>
  );
}
