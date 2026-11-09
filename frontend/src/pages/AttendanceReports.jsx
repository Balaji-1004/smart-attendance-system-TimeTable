import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import EmptyState from '../components/ui/EmptyState';
import ErrorMessage from '../components/ui/ErrorMessage';
import PageHeader from '../components/ui/PageHeader';
import Spinner from '../components/ui/Spinner';
import Table from '../components/ui/Table';

const tabs = [
  { id: 'daily', label: 'Daily' },
  { id: 'subject', label: 'Subject-wise' },
  { id: 'student', label: 'Student history' },
  { id: 'class', label: 'Class summary' },
];
const EMPTY_ROWS = [];

function localDateString(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function progressStyle(value) {
  return { width: `${Math.min(100, Math.max(0, Number(value) || 0))}%` };
}

function csvCell(value) {
  const text = value == null ? '' : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function downloadCsv(filename, headers, rows) {
  const content = [headers, ...rows].map((row) => row.map(csvCell).join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8;' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function SelectField({ label, value, options, onChange, placeholder = 'Select' }) {
  return (
    <label className="form-field">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>{option.name}</option>
        ))}
      </select>
    </label>
  );
}

export default function AttendanceReports() {
  const { role, faculty_id } = useAuth();
  const [activeTab, setActiveTab] = useState('daily');
  const [years, setYears] = useState([]);
  const [yearsLoading, setYearsLoading] = useState(true);
  const [yearsError, setYearsError] = useState('');
  const [dailyDate, setDailyDate] = useState(localDateString(new Date()));
  const [dailyYear, setDailyYear] = useState('');
  const [subjectYear, setSubjectYear] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [subjects, setSubjects] = useState([]);
  const [historyYear, setHistoryYear] = useState('');
  const [historyStudentId, setHistoryStudentId] = useState('');
  const [historySubjectId, setHistorySubjectId] = useState('');
  const [students, setStudents] = useState([]);
  const [historySubjects, setHistorySubjects] = useState([]);
  const [classYear, setClassYear] = useState('');
  const [rows, setRows] = useState({});
  const [loading, setLoading] = useState({});
  const [errors, setErrors] = useState({});

  const setTabLoading = (tab, isLoading) => setLoading((current) => ({ ...current, [tab]: isLoading }));
  const setTabError = (tab, message) => setErrors((current) => ({ ...current, [tab]: message }));
  const setTabRows = (tab, data) => setRows((current) => ({ ...current, [tab]: data }));

  const loadYears = useCallback(async () => {
    setYearsLoading(true);
    setYearsError('');
    try {
      const response = await api.get('/academic-years');
      const availableYears = response.data || [];
      setYears(availableYears);
      if (availableYears.length) {
        const firstId = String(availableYears[0].id);
        setSubjectYear((value) => value || firstId);
        setHistoryYear((value) => value || firstId);
        setClassYear((value) => value || firstId);
      }
    } catch (requestError) {
      setYearsError(requestError?.response?.data?.detail || 'Failed to load academic years.');
    } finally {
      setYearsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadYears();
  }, [loadYears]);

  useEffect(() => {
    if (activeTab !== 'daily' || !dailyDate || yearsLoading) return;
    let active = true;
    const load = async () => {
      setTabLoading('daily', true);
      setTabError('daily', '');
      try {
        const params = new URLSearchParams({ date: dailyDate });
        if (dailyYear) params.set('academic_year_id', dailyYear);
        const response = await api.get(`/reports/attendance/daily?${params.toString()}`);
        if (active) setTabRows('daily', response.data || []);
      } catch (requestError) {
        if (active) setTabError('daily', requestError?.response?.data?.detail || 'Failed to load daily attendance.');
      } finally {
        if (active) setTabLoading('daily', false);
      }
    };
    load();
    return () => { active = false; };
  }, [activeTab, dailyDate, dailyYear, yearsLoading]);

  useEffect(() => {
    if (activeTab !== 'subject' || !subjectYear) return;
    let active = true;
    const load = async () => {
      setTabLoading('subject', true);
      setTabError('subject', '');
      setTabRows('subject', []);
      setSubjects([]);
      setSubjectId('');
      try {
        const response = await api.get(`/timetable/year/${subjectYear}`);
        let entries = response.data || [];
        if (role === 'FACULTY') entries = entries.filter((entry) => Number(entry.faculty_id) === Number(faculty_id));
        const unique = [...new Map(entries.map((entry) => [entry.subject_id, {
          id: entry.subject_id,
          name: entry.subject_name,
        }])).values()];
        if (active) {
          setSubjects(unique);
          setSubjectId(String(unique[0]?.id || ''));
          setTabLoading('subject', false);
        }
      } catch (requestError) {
        if (active) {
          setTabError('subject', requestError?.response?.data?.detail || 'Failed to load subjects for this year.');
          setTabLoading('subject', false);
        }
      }
    };
    load();
    return () => { active = false; };
  }, [activeTab, subjectYear, role, faculty_id]);

  useEffect(() => {
    if (activeTab !== 'subject' || !subjectId) return;
    let active = true;
    const load = async () => {
      setTabLoading('subject', true);
      setTabError('subject', '');
      try {
        const response = await api.get(`/reports/attendance/subject/${subjectId}`);
        if (active) setTabRows('subject', response.data || []);
      } catch (requestError) {
        if (active) setTabError('subject', requestError?.response?.data?.detail || 'Failed to load subject attendance.');
      } finally {
        if (active) setTabLoading('subject', false);
      }
    };
    load();
    return () => { active = false; };
  }, [activeTab, subjectId]);

  useEffect(() => {
    if (activeTab !== 'student' || !historyYear) return;
    let active = true;
    const load = async () => {
      setTabLoading('student', true);
      setTabError('student', '');
      setTabRows('student', []);
      setStudents([]);
      setHistorySubjects([]);
      setHistoryStudentId('');
      setHistorySubjectId('');
      try {
        const [studentResponse, timetableResponse] = await Promise.all([
          api.get(`/students?academic_year_id=${historyYear}`),
          api.get(`/timetable/year/${historyYear}`),
        ]);
        const availableStudents = studentResponse.data || [];
        const entries = timetableResponse.data || [];
        const uniqueSubjects = [...new Map(entries.map((entry) => [entry.subject_id, {
          id: entry.subject_id,
          name: entry.subject_name,
        }])).values()];
        if (active) {
          setStudents(availableStudents);
          setHistorySubjects(uniqueSubjects);
          setHistoryStudentId((current) => availableStudents.some((student) => String(student.id) === current)
            ? current
            : String(availableStudents[0]?.id || ''));
          setHistorySubjectId((current) => uniqueSubjects.some((subject) => String(subject.id) === current) ? current : '');
          setTabLoading('student', false);
        }
      } catch (requestError) {
        if (active) {
          setTabError('student', requestError?.response?.data?.detail || 'Failed to load students for this year.');
          setTabLoading('student', false);
        }
      }
    };
    load();
    return () => { active = false; };
  }, [activeTab, historyYear]);

  useEffect(() => {
    if (activeTab !== 'student' || !historyStudentId) return;
    let active = true;
    const load = async () => {
      setTabLoading('student', true);
      setTabError('student', '');
      try {
        const params = historySubjectId ? `?subject_id=${historySubjectId}` : '';
        const response = await api.get(`/reports/attendance/student/${historyStudentId}${params}`);
        if (active) setTabRows('student', response.data || []);
      } catch (requestError) {
        if (active) setTabError('student', requestError?.response?.data?.detail || 'Failed to load student attendance history.');
      } finally {
        if (active) setTabLoading('student', false);
      }
    };
    load();
    return () => { active = false; };
  }, [activeTab, historyStudentId, historySubjectId]);

  useEffect(() => {
    if (activeTab !== 'class' || !classYear) return;
    let active = true;
    const load = async () => {
      setTabLoading('class', true);
      setTabError('class', '');
      try {
        const response = await api.get(`/reports/attendance/class-summary/${classYear}`);
        if (active) setTabRows('class', response.data || []);
      } catch (requestError) {
        if (active) setTabError('class', requestError?.response?.data?.detail || 'Failed to load class summary.');
      } finally {
        if (active) setTabLoading('class', false);
      }
    };
    load();
    return () => { active = false; };
  }, [activeTab, classYear]);

  const shownRows = rows[activeTab] || EMPTY_ROWS;
  const csvData = useMemo(() => {
    if (activeTab === 'daily') return {
      filename: 'daily-attendance.csv',
      headers: ['Time', 'Student', 'Subject', 'Status'],
      rows: shownRows.map((row) => [formatTime(row.time), row.student_name, row.subject_name, row.status]),
    };
    if (activeTab === 'subject') return {
      filename: 'subject-attendance.csv',
      headers: ['Student', 'Present', 'Total', 'Percentage'],
      rows: shownRows.map((row) => [row.student_name, row.present_count, row.total_count, `${row.percentage}%`]),
    };
    if (activeTab === 'student') return {
      filename: 'student-attendance-history.csv',
      headers: ['Date', 'Time', 'Subject', 'Status'],
      rows: shownRows.map((row) => [row.date, formatTime(row.time), row.subject_name, row.status]),
    };
    return {
      filename: 'class-attendance-summary.csv',
      headers: ['Subject', 'Present', 'Absent', 'Total', 'Percentage'],
      rows: shownRows.map((row) => [row.subject_name, row.present_count, row.absent_count, row.total_count, `${row.percentage}%`]),
    };
  }, [activeTab, shownRows]);

  const yearOptions = years.map((year) => ({ id: year.id, name: year.name }));
  const selectOptions = {
    daily: (
      <>
        <label className="form-field">Date<input type="date" value={dailyDate} onChange={(event) => setDailyDate(event.target.value)} /></label>
        <SelectField label="Academic year (optional)" value={dailyYear} options={yearOptions} onChange={setDailyYear} placeholder="All years" />
      </>
    ),
    subject: (
      <>
        <SelectField label="Academic year" value={subjectYear} options={yearOptions} onChange={setSubjectYear} />
        <SelectField label="Subject" value={subjectId} options={subjects} onChange={setSubjectId} />
      </>
    ),
    student: (
      <>
        <SelectField label="Academic year" value={historyYear} options={yearOptions} onChange={setHistoryYear} />
        <SelectField label="Student" value={historyStudentId} options={students.map((student) => ({ id: student.id, name: `${student.name} (${student.roll_number})` }))} onChange={setHistoryStudentId} />
        <SelectField label="Subject (optional)" value={historySubjectId} options={historySubjects} onChange={setHistorySubjectId} placeholder="All subjects" />
      </>
    ),
    class: <SelectField label="Academic year" value={classYear} options={yearOptions} onChange={setClassYear} />,
  };

  const tableRows = {
    daily: shownRows.map((row) => (
      <tr key={row.id}><td>{formatTime(row.time)}</td><td>{row.student_name}</td><td>{row.subject_name}</td>
        <td><Badge tone={row.status === 'PRESENT' ? 'success' : 'warning'}>{row.status}</Badge></td></tr>
    )),
    subject: shownRows.map((row) => (
      <tr key={row.student_id}><td>{row.student_name}</td><td>{row.present_count}</td><td>{row.total_count}</td>
        <td><div className="progress-label"><span>{Number(row.percentage).toFixed(1)}%</span>
          {row.percentage < 75 ? <Badge tone="warning">Below 75%</Badge> : null}</div>
          <div className="progress-bar"><span style={progressStyle(row.percentage)} /></div></td></tr>
    )),
    student: shownRows.map((row) => (
      <tr key={row.id}><td>{row.date}</td><td>{formatTime(row.time)}</td><td>{row.subject_name}</td>
        <td><Badge tone={row.status === 'PRESENT' ? 'success' : 'warning'}>{row.status}</Badge></td></tr>
    )),
    class: shownRows.map((row) => (
      <tr key={row.subject_id}><td>{row.subject_name}</td><td>{row.present_count}</td><td>{row.absent_count}</td><td>{row.total_count}</td>
        <td><div className="progress-label"><span>{Number(row.percentage).toFixed(1)}%</span></div>
          <div className="progress-bar"><span style={progressStyle(row.percentage)} /></div></td></tr>
    )),
  };
  const tableHeaders = {
    daily: ['Time', 'Student', 'Subject', 'Status'],
    subject: ['Student', 'Present', 'Total', 'Percentage'],
    student: ['Date', 'Time', 'Subject', 'Status'],
    class: ['Subject', 'Present', 'Absent', 'Total', 'Percentage'],
  };

  return (
    <div className="management-page">
      <PageHeader title="Attendance Reports" description="Review attendance by date, subject, student, or class." />
      <div className="report-tabs" role="tablist" aria-label="Attendance report type">
        {tabs.map((tab) => (
          <Button key={tab.id} variant={activeTab === tab.id ? 'primary' : 'secondary'} role="tab" aria-selected={activeTab === tab.id} onClick={() => setActiveTab(tab.id)}>
            {tab.label}
          </Button>
        ))}
      </div>

      {yearsLoading ? <Spinner label="Loading academic years..." /> : null}
      {!yearsLoading && yearsError ? <ErrorMessage message={yearsError} onRetry={loadYears} /> : null}
      {!yearsLoading && !yearsError && years.length === 0 ? <EmptyState title="No academic years" description="There are no academic years available for reports." /> : null}

      {!yearsLoading && !yearsError && years.length > 0 ? (
        <Card className="full-width">
          <div className="report-filters">
            {selectOptions[activeTab]}
            <Button variant="secondary" disabled={Boolean(loading[activeTab]) || !shownRows.length} onClick={() => downloadCsv(csvData.filename, csvData.headers, csvData.rows)}>
              Download CSV
            </Button>
          </div>
          {loading[activeTab] ? <Spinner label={`Loading ${tabs.find((tab) => tab.id === activeTab)?.label.toLowerCase()} report...`} /> : null}
          {!loading[activeTab] && errors[activeTab] ? <ErrorMessage message={errors[activeTab]} /> : null}
          {!loading[activeTab] && !errors[activeTab] ? (
            shownRows.length ? <Table headers={tableHeaders[activeTab]} rows={tableRows[activeTab]} /> :
              <EmptyState title="No report rows" description="No attendance records match the selected filters." />
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
