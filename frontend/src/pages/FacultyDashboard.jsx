import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import TimetableGrid from '../components/TimetableGrid';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import ErrorMessage from '../components/ui/ErrorMessage';
import PageHeader from '../components/ui/PageHeader';
import Spinner from '../components/ui/Spinner';
import StatCard from '../components/ui/StatCard';
import Table from '../components/ui/Table';

const weekdayNames = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];

function localDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function FacultyDashboard() {
  const { faculty_id } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryKey, setRetryKey] = useState(0);

  const loadDashboard = useCallback(async () => {
    if (!faculty_id) {
      setError('Faculty account is not linked to a faculty record.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const today = new Date();
      const [timetableResponse, sessionsResponse] = await Promise.all([
        api.get(`/timetable/faculty/${faculty_id}`),
        api.get(`/attendance-sessions?date=${localDateString(today)}`),
      ]);
      const timetable = timetableResponse.data || [];
      const sessions = sessionsResponse.data || [];
      const yearIds = [...new Set(timetable.map((entry) => entry.academic_year_id))];
      const reportResponses = await Promise.all(
        yearIds.map((yearId) => api.get(`/reports/attendance/class-summary/${yearId}`))
      );
      const attendance = reportResponses.flatMap((response, index) =>
        (response.data || []).map((row) => ({ ...row, academic_year_id: yearIds[index] }))
      );
      setData({ timetable, sessions, attendance, todayName: weekdayNames[today.getDay()] });
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Failed to load faculty dashboard.');
    } finally {
      setLoading(false);
    }
  }, [faculty_id]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard, retryKey]);

  const subjects = useMemo(() => {
    if (!data) return [];
    const unique = new Map();
    data.timetable.forEach((entry) => {
      unique.set(entry.subject_id, {
        subject_id: entry.subject_id,
        subject_name: entry.subject_name,
        academic_year_id: entry.academic_year_id,
      });
    });
    return [...unique.values()];
  }, [data]);

  if (loading) return <Spinner label="Loading faculty dashboard..." />;
  if (error) return <ErrorMessage message={error} onRetry={() => setRetryKey((value) => value + 1)} />;
  if (!data) return <EmptyState title="No faculty dashboard data" description="No timetable data is available yet." />;

  const todayClasses = data.timetable.filter((entry) => entry.day === data.todayName);
  const openSessions = data.sessions.filter((session) => session.status === 'OPEN');
  const closedSessions = data.sessions.filter((session) => session.status === 'CLOSED');
  const entryById = new Map(data.timetable.map((entry) => [entry.id, entry]));

  return (
    <>
      <PageHeader title="Faculty Dashboard" description="Today's classes, attendance sessions, and assigned subjects." />

      <div className="stat-grid">
        <StatCard label="Today's classes" value={todayClasses.length} />
        <StatCard label="Assigned subjects" value={subjects.length} />
        <StatCard label="Open sessions today" value={openSessions.length} />
        <StatCard label="Closed sessions today" value={closedSessions.length} />
      </div>

      <div className="dashboard-grid">
        <Card className="panel-panel">
          <div className="section-heading"><h3>Today's classes</h3></div>
          {todayClasses.length ? (
            <Table
              headers={['Period', 'Subject', 'Lab', '']}
              rows={todayClasses.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.period}</td><td>{entry.subject_name}</td><td>{entry.lab_name || '—'}</td>
                  <td><Link to="/attendance"><Button>Start attendance</Button></Link></td>
                </tr>
              ))}
            />
          ) : <EmptyState title="No classes today" description="There are no classes scheduled for today." />}
        </Card>

        <Card className="panel-panel">
          <div className="section-heading"><h3>Today's attendance sessions</h3></div>
          {data.sessions.length ? (
            <Table
              headers={['Subject', 'Status', 'Session']}
              rows={data.sessions.map((session) => (
                <tr key={session.id}>
                  <td>{entryById.get(session.timetable_entry_id)?.subject_name || `Subject ${session.subject_id}`}</td>
                  <td><Badge tone={session.status === 'OPEN' ? 'warning' : 'success'}>{session.status}</Badge></td>
                  <td>{session.id}</td>
                </tr>
              ))}
            />
          ) : <EmptyState title="No sessions today" description="Attendance sessions started today will appear here." />}
        </Card>
      </div>

      <Card className="full-width">
        <div className="section-heading"><h3>Assigned subjects</h3></div>
        {subjects.length ? (
          <Table
            headers={['Subject', 'Academic year']}
            rows={subjects.map((subject) => (
              <tr key={subject.subject_id}><td>{subject.subject_name}</td><td>Year {subject.academic_year_id}</td></tr>
            ))}
          />
        ) : <EmptyState title="No assigned subjects" description="Subjects from your timetable will appear here." />}
      </Card>

      <Card className="full-width">
        <div className="section-heading"><h3>Weekly timetable</h3></div>
        {data.timetable.length ? <TimetableGrid entries={data.timetable} /> : <EmptyState title="No timetable available" description="No timetable entries are assigned to you yet." />}
      </Card>

      <Card className="full-width">
        <div className="section-heading"><h3>Class attendance by subject</h3></div>
        {data.attendance.length ? (
          <Table
            headers={['Subject', 'Academic year', 'Present', 'Absent', 'Total', 'Attendance']}
            rows={data.attendance.map((row) => (
              <tr key={`${row.academic_year_id}-${row.subject_id}`}>
                <td>{row.subject_name}</td><td>Year {row.academic_year_id}</td>
                <td>{row.present_count}</td><td>{row.absent_count}</td><td>{row.total_count}</td>
                <td>{Number(row.percentage).toFixed(1)}%</td>
              </tr>
            ))}
          />
        ) : <EmptyState title="No class attendance yet" description="Subject attendance summaries will appear once sessions are recorded." />}
      </Card>
    </>
  );
}
