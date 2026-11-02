import { AuthProvider } from './context/AuthContext';
import { useAuth } from './context/AuthContext';
import AttendanceSessionPage from './pages/AttendanceSession';
import FacultyTimetableView from './pages/FacultyTimetableView';
import FaceRegistration from './pages/FaceRegistration';
import Login from './pages/Login';
import TimetableView from './pages/TimetableView';
import { useState } from 'react';

function AuthenticatedApp() {
  const { role, logout } = useAuth();
  const [showYearView, setShowYearView] = useState(role !== 'FACULTY');
  const [activeView, setActiveView] = useState('timetable');

  if (role === 'FACULTY') {
    const timetable = showYearView ? <TimetableView /> : <FacultyTimetableView />;

    return (
      <>
        <div style={{ padding: '12px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => setShowYearView((visible) => !visible)} style={{ marginRight: '8px' }}>
              {showYearView ? 'View my timetable' : 'View year timetable'}
            </button>
            <button type="button" onClick={() => setActiveView('attendance')} style={{ padding: '8px 12px', border: activeView === 'attendance' ? '1px solid #2563eb' : '1px solid #d1d5db', borderRadius: '6px', background: activeView === 'attendance' ? '#eff6ff' : '#fff', cursor: 'pointer' }}>
              Attendance
            </button>
          </div>
          <button type="button" onClick={logout}>Log out</button>
        </div>
        {activeView === 'attendance' ? <AttendanceSessionPage /> : timetable}
      </>
    );
  }

  return (
    <>
      <div style={{ padding: '12px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" onClick={() => setActiveView('timetable')} style={{ padding: '8px 12px', border: activeView === 'timetable' ? '1px solid #2563eb' : '1px solid #d1d5db', borderRadius: '6px', background: activeView === 'timetable' ? '#eff6ff' : '#fff', cursor: 'pointer' }}>
            Timetable
          </button>
          <button type="button" onClick={() => setActiveView('attendance')} style={{ padding: '8px 12px', border: activeView === 'attendance' ? '1px solid #2563eb' : '1px solid #d1d5db', borderRadius: '6px', background: activeView === 'attendance' ? '#eff6ff' : '#fff', cursor: 'pointer' }}>
            Attendance
          </button>
          <button type="button" onClick={() => setActiveView('face-registration')} style={{ padding: '8px 12px', border: activeView === 'face-registration' ? '1px solid #2563eb' : '1px solid #d1d5db', borderRadius: '6px', background: activeView === 'face-registration' ? '#eff6ff' : '#fff', cursor: 'pointer' }}>
            Face Registration
          </button>
        </div>
        <button type="button" onClick={logout}>Log out</button>
      </div>
      {activeView === 'face-registration' ? <FaceRegistration /> : activeView === 'attendance' ? <AttendanceSessionPage /> : <TimetableView />}
    </>
  );
}

function AppContent() {
  const { token } = useAuth();
  return token ? <AuthenticatedApp /> : <Login />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
