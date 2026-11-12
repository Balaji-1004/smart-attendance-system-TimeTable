import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import ErrorMessage from '../components/ui/ErrorMessage';
import EmptyState from '../components/ui/EmptyState';
import PageHeader from '../components/ui/PageHeader';
import Spinner from '../components/ui/Spinner';
import StatCard from '../components/ui/StatCard';
import { yearLabel } from '../utils/labels';

function percentStyle(value) {
  if (value == null) return { width: '0%', background: '#e5e7eb' };
  const clamped = Math.min(100, Math.max(0, Number(value)));
  return { width: `${clamped}%` };
}

export default function HODDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryKey, setRetryKey] = useState(0);

  const loadDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/dashboard/hod');
      setData(response.data || null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, [retryKey]);

  const summary = useMemo(() => {
    if (!data) return null;
    const registered = data.counts?.students_face_registered || 0;
    const total = data.counts?.students || 0;
    return {
      registered,
      total,
      faceRate: total > 0 ? (registered / total) * 100 : 0,
    };
  }, [data]);

  if (loading) {
    return <Spinner label="Loading dashboard..." />;
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={() => setRetryKey((value) => value + 1)} />;
  }

  if (!data) {
    return <EmptyState title="No dashboard data" description="No dashboard metrics are available yet." />;
  }

  const getYearLabel = (yearId, name, programmeName) => {
    const year = data.years.find((item) => Number(item.academic_year_id ?? item.id) === Number(yearId));
    return yearLabel(year || { name, programme_name: programmeName });
  };

  return (
    <>
      <PageHeader
        title="HOD Dashboard"
        description="Department readiness, attendance trends, and recent session activity."
        actions={
          <>
            <Link to="/timetable"><Button variant="secondary">Generate/View Timetable</Button></Link>
            <Link to="/face-registration"><Button variant="secondary">Face Registration</Button></Link>
            <Link to="/attendance"><Button>Start Attendance</Button></Link>
          </>
        }
      />

      <div className="stat-grid">
        <StatCard label="Academic Years" value={data.counts.academic_years} />
        <StatCard label="Students" value={data.counts.students} />
        <StatCard label="Faculty" value={data.counts.faculty} />
        <StatCard label="Subjects" value={data.counts.subjects} />
        <StatCard label="Labs" value={data.counts.labs} />
        <StatCard label="Face Registered" value={`${summary.registered} / ${summary.total}`} hint={`${summary.faceRate.toFixed(0)}% registered`} />
      </div>

      <div className="dashboard-grid">
        <Card className="panel-panel">
          <h3>Today</h3>
          <div className="key-stats">
            <div><span>Total</span><strong>{data.today.sessions_total}</strong></div>
            <div><span>Open</span><strong>{data.today.sessions_open}</strong></div>
            <div><span>Closed</span><strong>{data.today.sessions_closed}</strong></div>
            <div><span>Present</span><strong>{data.today.present_count}</strong></div>
            <div><span>Absent</span><strong>{data.today.absent_count}</strong></div>
          </div>
        </Card>

        <Card className="panel-panel">
          <h3>Quick overview</h3>
          <div className="progress-stack">
            <div>
              <div className="progress-label"><span>Face registration</span><strong>{summary.faceRate.toFixed(0)}%</strong></div>
              <div className="progress-bar"><span style={percentStyle(summary.faceRate)} /></div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="full-width">
        <div className="section-heading">
          <h3>Academic year overview</h3>
        </div>
        <div className="year-grid">
          {data.years.length === 0 ? (
            <EmptyState title="No academic year data" description="Create an academic year to begin tracking coverage." />
          ) : (
            data.years.map((year) => {
              const schedulePercent = year.expected_weekly_periods > 0 ? (year.timetable_entries_count / year.expected_weekly_periods) * 100 : 0;
              const facePercent = year.student_count > 0 ? (year.face_registered_count / year.student_count) * 100 : 0;
              return (
                <div key={year.academic_year_id} className="year-card">
                  <div className="year-card__header">
                    <h4>{yearLabel(year)}</h4>
                    <div className="year-card__actions">
                      <Link to="/timetable"><Button variant="secondary">View timetable</Button></Link>
                      <Link to="/attendance"><Button variant="secondary">Open attendance</Button></Link>
                    </div>
                  </div>
                  <div className="meta-row">
                    <span>Students: {year.student_count}</span>
                    <span>Subjects: {year.subject_count}</span>
                  </div>
                  <div className="progress-stack compact">
                    <div>
                      <div className="progress-label"><span>Coverage</span><strong>{year.timetable_entries_count}/{year.expected_weekly_periods}</strong></div>
                      <div className="progress-bar"><span style={percentStyle(schedulePercent)} /></div>
                    </div>
                    <div>
                      <div className="progress-label"><span>Face registered</span><strong>{year.face_registered_count}/{year.student_count}</strong></div>
                      <div className="progress-bar"><span style={percentStyle(facePercent)} /></div>
                    </div>
                  </div>
                  <div className="year-card__footer">
                    <span>Attendance</span>
                    {year.attendance_percentage == null ? <Badge tone="neutral">No data yet</Badge> : <Badge tone={year.attendance_percentage >= 75 ? 'success' : 'warning'}>{year.attendance_percentage.toFixed(1)}%</Badge>}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>

      <div className="dashboard-grid">
        <Card>
          <div className="section-heading">
            <h3>Recent sessions</h3>
          </div>
          {data.recent_sessions.length === 0 ? (
            <EmptyState title="No recent sessions" description="No attendance sessions have been created yet." />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Subject</th>
                    <th>Faculty</th>
                    <th>Year</th>
                    <th>Present</th>
                    <th>Absent</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_sessions.map((session) => (
                    <tr key={session.id}>
                      <td>{session.id}</td>
                      <td>{session.date}</td>
                      <td><Badge tone={session.status === 'OPEN' ? 'warning' : 'success'}>{session.status}</Badge></td>
                      <td>{session.subject_name}</td>
                      <td>{session.faculty_name}</td>
                      <td>{getYearLabel(session.academic_year_id, session.academic_year_name, session.programme_name)}</td>
                      <td>{session.present_count}</td>
                      <td>{session.absent_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card>
          <div className="section-heading">
            <h3>Low attendance students</h3>
          </div>
          {data.low_attendance_students.length === 0 ? (
            <EmptyState title="All clear" description="No students currently fall below the 75% threshold." />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Year</th>
                    <th>Percentage</th>
                  </tr>
                </thead>
                <tbody>
                  {data.low_attendance_students.map((student) => (
                    <tr key={student.student_id}>
                      <td>{student.name} ({student.roll_number})</td>
                      <td>{getYearLabel(student.academic_year_id, student.academic_year_name, student.programme_name)}</td>
                      <td><Badge tone="warning">{student.percentage.toFixed(1)}%</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card className="full-width">
        <div className="section-heading">
          <h3>Warnings</h3>
        </div>
        {data.warnings.length === 0 ? (
          <div className="all-good">All good</div>
        ) : (
          <ul className="warning-list">
            {data.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        )}
      </Card>
    </>
  );
}
