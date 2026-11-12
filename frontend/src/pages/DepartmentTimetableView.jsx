import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import TimetableGrid from '../components/TimetableGrid';
import api from '../services/api';
import { yearLabel } from '../utils/labels';

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
        const [timetableResponse, yearsResponse] = await Promise.all([
          api.get('/timetable/department'),
          api.get('/academic-years'),
        ]);
        const yearsById = new Map((yearsResponse.data || []).map((year) => [String(year.id), year]));
        const grouped = {};
        (timetableResponse.data || []).forEach((entry) => {
          const academicYear = yearsById.get(String(entry.academic_year_id));
          const programmeName = academicYear?.programme_name || entry.programme_name || 'Programme';
          const programmeId = academicYear?.programme_id || entry.programme_id || programmeName;
          if (!grouped[programmeId]) grouped[programmeId] = { name: programmeName, years: {} };

          const yearId = String(entry.academic_year_id);
          if (!grouped[programmeId].years[yearId]) {
            const year = {
              ...(academicYear || {}),
              name: academicYear?.name || entry.academic_year_name || `Academic Year ${yearId}`,
              programme_name: programmeName,
            };
            grouped[programmeId].years[yearId] = { name: yearLabel(year), entries: [] };
          }
          grouped[programmeId].years[yearId].entries.push(entry);
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

      {!loading && Object.entries(entriesByYear).map(([programmeId, programme]) => (
        <div key={programmeId} style={{ marginTop: '24px' }}>
          <h3 style={{ marginBottom: '12px' }}>{programme.name}</h3>
          {Object.entries(programme.years).map(([yearId, year]) => (
            <div key={yearId} style={{ marginTop: '16px' }}>
              <h4 style={{ marginBottom: '12px' }}>{year.name}</h4>
              <TimetableGrid entries={year.entries} />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
