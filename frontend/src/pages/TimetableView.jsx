import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import TimetableGrid from '../components/TimetableGrid';
import api from '../services/api';

export default function TimetableView() {
  const { token, role } = useAuth();
  const [years, setYears] = useState([]);
  const [selectedYearId, setSelectedYearId] = useState('');
  const [entries, setEntries] = useState([]);
  const [loadingYears, setLoadingYears] = useState(true);
  const [loadingTimetable, setLoadingTimetable] = useState(false);
  const [error, setError] = useState('');
  const [report, setReport] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const fetchYears = async () => {
      if (!token) {
        setError('No auth token was found. Please log in first.');
        setLoadingYears(false);
        return;
      }

      try {
        const response = await api.get('/academic-years');
        setYears(response.data || []);
        if (response.data?.length) {
          setSelectedYearId(String(response.data[0].id));
        }
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to load academic years.');
      } finally {
        setLoadingYears(false);
      }
    };

    fetchYears();
  }, [token]);

  useEffect(() => {
    if (!selectedYearId) {
      setEntries([]);
      return;
    }

    const fetchTimetable = async () => {
      if (!token) {
        setError('No auth token was found.');
        return;
      }

      setLoadingTimetable(true);
      setError('');

      try {
        const response = await api.get(`/timetable/year/${selectedYearId}`);
        setEntries(response.data || []);
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to load timetable.');
        setEntries([]);
      } finally {
        setLoadingTimetable(false);
      }
    };

    fetchTimetable();
  }, [selectedYearId, token]);

  const refreshTimetable = async () => {
    if (!selectedYearId) return;
    const response = await api.get(`/timetable/year/${selectedYearId}`);
    setEntries(response.data || []);
  };

  const generateTimetable = async () => {
    if (!selectedYearId || !window.confirm('Regenerating the timetable will discard existing timetable changes. Continue?')) return;
    setGenerating(true);
    setError('');
    setReport(null);
    try {
      const response = await api.post('/timetable/generate', { academic_year_id: Number(selectedYearId) });
      setReport(response.data);
      await refreshTimetable();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to generate timetable.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h2>Academic Year Timetable</h2>

      {loadingYears ? (
        <p>Loading academic years...</p>
      ) : (
        <div style={{ marginBottom: '16px' }}>
          <label htmlFor="year-select" style={{ marginRight: '8px', fontWeight: 600 }}>Academic year:</label>
          <select
            id="year-select"
            value={selectedYearId}
            onChange={(event) => setSelectedYearId(event.target.value)}
            style={{ padding: '8px', minWidth: '220px' }}
          >
            <option value="">Select a year</option>
            {years.map((year) => (
              <option key={year.id} value={year.id}>{year.name}</option>
            ))}
          </select>
          {role === 'HOD' ? (
            <button type="button" onClick={generateTimetable} disabled={!selectedYearId || generating} style={{ marginLeft: '8px', padding: '8px 12px' }}>
              {generating ? 'Generating...' : 'Generate Timetable'}
            </button>
          ) : null}
        </div>
      )}

      {error ? <p style={{ color: '#b91c1c', marginBottom: '16px' }}>{error}</p> : null}

      {loadingTimetable ? <p>Loading timetable...</p> : null}

      {!loadingTimetable && selectedYearId && entries.length > 0 ? <TimetableGrid entries={entries} onRefresh={refreshTimetable} /> : null}

      {!loadingTimetable && selectedYearId && entries.length === 0 && !error ? (
        <p>No timetable entries were found for this year.</p>
      ) : null}

      {report ? (
        <div style={{ marginTop: '16px' }}>
          <h3>Generation report</h3>
          <p>Placed entries: {report.placed_count}</p>
          {report.unscheduled?.length > 0 ? (
            <>
              <h4>Unscheduled subjects</h4>
              <ul>{report.unscheduled.map((item, index) => <li key={`${item.subject_name}-${index}`}>{item.subject_name}: {item.reason}</li>)}</ul>
            </>
          ) : <p>All scheduled blocks were placed.</p>}
          {report.feasibility_warnings && (
            <div>
              <h4>Feasibility warnings</h4>
              {Object.entries(report.feasibility_warnings).map(([type, warnings]) => warnings?.length > 0 ? (
                <div key={type}><strong>{type}</strong><ul>{warnings.map((warning, index) => <li key={`${type}-${index}`}>{warning}</li>)}</ul></div>
              ) : null)}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
