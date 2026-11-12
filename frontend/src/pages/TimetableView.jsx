import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import TimetableGrid from '../components/TimetableGrid';
import api from '../services/api';
import { yearLabel } from '../utils/labels';

export default function TimetableView() {
  const { token, role } = useAuth();
  const [programmes, setProgrammes] = useState([]);
  const [selectedProgrammeId, setSelectedProgrammeId] = useState('');
  const [years, setYears] = useState([]);
  const [selectedYearId, setSelectedYearId] = useState('');
  const [entries, setEntries] = useState([]);
  const [subjectCount, setSubjectCount] = useState(null);
  const [loadingSubjects, setLoadingSubjects] = useState(false);
  const [subjectError, setSubjectError] = useState('');
  const [loadingYears, setLoadingYears] = useState(true);
  const [loadingTimetable, setLoadingTimetable] = useState(false);
  const [error, setError] = useState('');
  const [report, setReport] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchProgrammes = async () => {
      if (!token) {
        setError('No auth token was found. Please log in first.');
        setLoadingYears(false);
        return;
      }

      try {
        const response = await api.get('/programmes');
        const items = response.data || [];
        if (active) {
          setProgrammes(items);
          if (items.length) setSelectedProgrammeId(String(items[0].id));
          else setLoadingYears(false);
        }
      } catch (err) {
        if (active) {
          setError(err?.response?.data?.detail || 'Failed to load programmes.');
          setLoadingYears(false);
        }
      }
    };

    fetchProgrammes();
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!programmes.length) return;
    let active = true;
    const fetchYears = async () => {
      setLoadingYears(true);
      setError('');
      setSelectedYearId('');
      setYears([]);
      try {
        const query = selectedProgrammeId ? `?programme_id=${encodeURIComponent(selectedProgrammeId)}` : '';
        const response = await api.get(`/academic-years${query}`);
        const items = response.data || [];
        if (active) {
          setYears(items);
          setSelectedYearId(items.length ? String(items[0].id) : '');
        }
      } catch (err) {
        if (active) setError(err?.response?.data?.detail || 'Failed to load academic years.');
      } finally {
        if (active) setLoadingYears(false);
      }
    };

    fetchYears();
    return () => { active = false; };
  }, [programmes.length, selectedProgrammeId]);

  useEffect(() => {
    if (!selectedYearId || role !== 'HOD') {
      setSubjectCount(null);
      setLoadingSubjects(false);
      return undefined;
    }

    let active = true;
    setSubjectCount(null);
    setSubjectError('');
    setLoadingSubjects(true);
    const fetchSubjects = async () => {
      try {
        const response = await api.get(`/subjects?academic_year_id=${encodeURIComponent(selectedYearId)}`);
        if (active) setSubjectCount((response.data || []).length);
      } catch (err) {
        if (active) setSubjectError(err?.response?.data?.detail || 'Failed to load subjects for this year.');
      } finally {
        if (active) setLoadingSubjects(false);
      }
    };
    fetchSubjects();

    return () => { active = false; };
  }, [role, selectedYearId]);

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
        <p>Loading programmes and academic years...</p>
      ) : (
        <div style={{ marginBottom: '16px' }}>
          <label htmlFor="programme-select" style={{ marginRight: '8px', fontWeight: 600 }}>Programme:</label>
          <select
            id="programme-select"
            value={selectedProgrammeId}
            onChange={(event) => setSelectedProgrammeId(event.target.value)}
            style={{ padding: '8px', minWidth: '220px', marginRight: '16px' }}
          >
            <option value="">All programmes</option>
            {programmes.map((programme) => (
              <option key={programme.id} value={programme.id}>{programme.name}</option>
            ))}
          </select>
          <label htmlFor="year-select" style={{ marginRight: '8px', fontWeight: 600 }}>Academic year:</label>
          <select
            id="year-select"
            value={selectedYearId}
            onChange={(event) => setSelectedYearId(event.target.value)}
            style={{ padding: '8px', minWidth: '220px' }}
          >
            <option value="">Select a year</option>
            {years.map((year) => (
              <option key={year.id} value={year.id}>{yearLabel(year)}</option>
            ))}
          </select>
          {role === 'HOD' ? (
            <button type="button" onClick={generateTimetable} disabled={!selectedYearId || generating || loadingSubjects || subjectCount === 0} style={{ marginLeft: '8px', padding: '8px 12px' }}>
              {generating ? 'Generating...' : 'Generate Timetable'}
            </button>
          ) : null}
        </div>
      )}

      {error ? <p style={{ color: '#b91c1c', marginBottom: '16px' }}>{error}</p> : null}
      {subjectError ? <p style={{ color: '#b91c1c', marginBottom: '16px' }}>{subjectError}</p> : null}

      {loadingTimetable ? <p>Loading timetable...</p> : null}
      {!loadingTimetable && selectedYearId && loadingSubjects ? <p>Checking subjects for this year...</p> : null}

      {!loadingTimetable && selectedYearId && entries.length > 0 ? <TimetableGrid entries={entries} onRefresh={refreshTimetable} /> : null}

      {!loadingTimetable && selectedYearId && entries.length === 0 && !error && !subjectError && !loadingSubjects ? (
        <p>
          {role === 'HOD' && subjectCount === 0
            ? 'No subjects are assigned to this academic year. Add subjects before generating its timetable.'
            : 'No timetable entries were found for this year.'}
        </p>
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
