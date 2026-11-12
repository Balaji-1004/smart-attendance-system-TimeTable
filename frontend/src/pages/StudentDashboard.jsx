import { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import TimetableGrid from '../components/TimetableGrid';
import Badge from '../components/ui/Badge';
import Card from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import ErrorMessage from '../components/ui/ErrorMessage';
import PageHeader from '../components/ui/PageHeader';
import Spinner from '../components/ui/Spinner';
import StatCard from '../components/ui/StatCard';
import Table from '../components/ui/Table';
import { yearLabel } from '../utils/labels';

const weekdayNames = ['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'];

function todayName() {
  return weekdayNames[new Date().getDay()];
}

function progressStyle(value) {
  return { width: `${Math.min(100, Math.max(0, Number(value) || 0))}%` };
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function StudentDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryKey, setRetryKey] = useState(0);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [profile, timetable, summary, history] = await Promise.all([
        api.get('/me/profile'),
        api.get('/me/timetable'),
        api.get('/me/attendance/summary'),
        api.get('/me/attendance/history'),
      ]);
      setData({
        profile: profile.data,
        timetable: timetable.data || [],
        summary: summary.data,
        history: history.data || [],
      });
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Failed to load student dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard, retryKey]);

  if (loading) return <Spinner label="Loading student dashboard..." />;
  if (error) return <ErrorMessage message={error} onRetry={() => setRetryKey((value) => value + 1)} />;
  if (!data) return <EmptyState title="No student dashboard data" description="Your student profile is not available." />;

  const { profile, timetable, summary, history } = data;
  const subjects = summary.subjects || [];
  const classesAttended = subjects.reduce((total, subject) => total + subject.present_count, 0);
  const todayClasses = timetable.filter((entry) => entry.day === todayName());
  const recentHistory = history.slice(0, 15);

  return (
    <>
      <PageHeader title="Student Dashboard" description="Your profile, timetable, and attendance at a glance." />

      <Card className="panel-panel">
        <div className="section-heading">
          <h3>{profile.name}</h3>
          <Badge tone={profile.face_registered ? 'success' : 'neutral'}>
            {profile.face_registered ? 'Face registered' : 'Face not registered'}
          </Badge>
        </div>
        <div className="key-stats">
          <div><span>Roll number</span><strong>{profile.roll_number}</strong></div>
          <div><span>Academic year</span><strong>{yearLabel(profile.academic_year || {
            name: profile.academic_year_name,
            programme_name: profile.programme_name || profile.academic_year_programme_name,
          })}</strong></div>
          <div><span>Department</span><strong>{profile.department_name}</strong></div>
        </div>
      </Card>

      <div className="stat-grid">
        <StatCard label="Overall attendance" value={`${Number(summary.overall_percentage || 0).toFixed(1)}%`} />
        <StatCard label="Subjects" value={subjects.length} />
        <StatCard label="Classes attended" value={classesAttended} />
      </div>

      <Card className="full-width">
        <div className="section-heading"><h3>Subject attendance</h3></div>
        {subjects.length ? (
          <Table
            headers={['Subject', 'Present', 'Absent', 'Total', 'Attendance']}
            rows={subjects.map((subject) => (
              <tr key={subject.subject_id}>
                <td>{subject.subject_name}</td>
                <td>{subject.present_count}</td>
                <td>{subject.absent_count}</td>
                <td>{subject.total_count}</td>
                <td>
                  <div className="progress-label">
                    <span>{Number(subject.percentage).toFixed(1)}%</span>
                    {subject.percentage < 75 ? <Badge tone="warning">Below 75%</Badge> : null}
                  </div>
                  <div className="progress-bar"><span style={progressStyle(subject.percentage)} /></div>
                </td>
              </tr>
            ))}
          />
        ) : <EmptyState title="No subjects" description="No subjects are assigned to your academic year yet." />}
      </Card>

      <Card className="full-width">
        <div className="section-heading"><h3>Today's classes</h3></div>
        {todayClasses.length ? (
          <Table
            headers={['Period', 'Subject', 'Faculty', 'Lab']}
            rows={todayClasses.map((entry) => (
              <tr key={entry.id}>
                <td>{entry.period}</td><td>{entry.subject_name}</td><td>{entry.faculty_name}</td><td>{entry.lab_name || '—'}</td>
              </tr>
            ))}
          />
        ) : <EmptyState title="No classes today" description="There are no classes scheduled for today." />}
      </Card>

      <Card className="full-width">
        <div className="section-heading"><h3>Weekly timetable</h3></div>
        {timetable.length ? <TimetableGrid entries={timetable} /> : <EmptyState title="No timetable available" description="Your academic year has no scheduled timetable entries yet." />}
      </Card>

      <Card className="full-width">
        <div className="section-heading"><h3>Recent attendance history</h3></div>
        {recentHistory.length ? (
          <Table
            headers={['Date', 'Time', 'Subject', 'Status']}
            rows={recentHistory.map((row, index) => (
              <tr key={`${row.date}-${row.time}-${row.subject_name}-${index}`}>
                <td>{row.date}</td><td>{formatTime(row.time)}</td><td>{row.subject_name}</td>
                <td><Badge tone={row.status === 'PRESENT' ? 'success' : 'warning'}>{row.status}</Badge></td>
              </tr>
            ))}
          />
        ) : <EmptyState title="No attendance history" description="Your attendance records will appear here." />}
      </Card>
    </>
  );
}
