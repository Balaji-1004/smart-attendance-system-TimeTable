import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AppShell from './components/layout/AppShell';
import ProtectedRoute from './routes/ProtectedRoute';
import Login from './pages/Login';
import HODDashboard from './pages/HODDashboard';
import FacultyDashboard from './pages/FacultyDashboard';
import StudentDashboard from './pages/StudentDashboard';
import TimetableView from './pages/TimetableView';
import FacultyTimetableView from './pages/FacultyTimetableView';
import DepartmentTimetableView from './pages/DepartmentTimetableView';
import AttendanceSessionPage from './pages/AttendanceSession';
import FaceRegistration from './pages/FaceRegistration';
import AcademicYearsPage from './pages/AcademicYearsPage';
import ProgrammesPage from './pages/ProgrammesPage';
import FacultyPage from './pages/FacultyPage';
import SubjectsPage from './pages/SubjectsPage';
import LabsPage from './pages/LabsPage';
import StudentsPage from './pages/StudentsPage';
import FacultyAvailabilityPage from './pages/FacultyAvailabilityPage';
import AttendanceReports from './pages/AttendanceReports';
import NotFound from './pages/NotFound';

function getDefaultDashboard(role) {
  if (role === 'HOD') return '/hod/dashboard';
  if (role === 'FACULTY') return '/faculty/dashboard';
  if (role === 'STUDENT') return '/student/dashboard';
  return '/login';
}

function AppRoutes() {
  const { token, role } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={token ? <Navigate to={getDefaultDashboard(role)} replace /> : <Login />} />
      <Route path="/" element={<Navigate to={token ? getDefaultDashboard(role) : '/login'} replace />} />

      <Route path="/hod/dashboard" element={<ProtectedRoute roles={['HOD']}><AppShell><HODDashboard /></AppShell></ProtectedRoute>} />
      <Route path="/academic-years" element={<ProtectedRoute roles={['HOD']}><AppShell><AcademicYearsPage /></AppShell></ProtectedRoute>} />
      <Route path="/programmes" element={<ProtectedRoute roles={['HOD']}><AppShell><ProgrammesPage /></AppShell></ProtectedRoute>} />
      <Route path="/faculty" element={<ProtectedRoute roles={['HOD']}><AppShell><FacultyPage /></AppShell></ProtectedRoute>} />
      <Route path="/subjects" element={<ProtectedRoute roles={['HOD']}><AppShell><SubjectsPage /></AppShell></ProtectedRoute>} />
      <Route path="/labs" element={<ProtectedRoute roles={['HOD']}><AppShell><LabsPage /></AppShell></ProtectedRoute>} />
      <Route path="/students" element={<ProtectedRoute roles={['HOD']}><AppShell><StudentsPage /></AppShell></ProtectedRoute>} />
      <Route path="/faculty-availability" element={<ProtectedRoute roles={['HOD']}><AppShell><FacultyAvailabilityPage /></AppShell></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute roles={['HOD', 'FACULTY']}><AppShell><AttendanceReports /></AppShell></ProtectedRoute>} />
      <Route path="/faculty/dashboard" element={<ProtectedRoute roles={['FACULTY']}><AppShell><FacultyDashboard /></AppShell></ProtectedRoute>} />
      <Route path="/student/dashboard" element={<ProtectedRoute roles={['STUDENT']}><AppShell><StudentDashboard /></AppShell></ProtectedRoute>} />

      <Route path="/timetable" element={<ProtectedRoute roles={['HOD', 'FACULTY']}><AppShell><TimetableView /></AppShell></ProtectedRoute>} />
      <Route path="/timetable/faculty" element={<ProtectedRoute roles={['FACULTY']}><AppShell><FacultyTimetableView /></AppShell></ProtectedRoute>} />
      <Route path="/timetable/department" element={<ProtectedRoute roles={['HOD']}><AppShell><DepartmentTimetableView /></AppShell></ProtectedRoute>} />

      <Route path="/attendance" element={<ProtectedRoute roles={['HOD', 'FACULTY']}><AppShell><AttendanceSessionPage /></AppShell></ProtectedRoute>} />
      <Route path="/face-registration" element={<ProtectedRoute roles={['HOD']}><AppShell><FaceRegistration /></AppShell></ProtectedRoute>} />
      <Route path="/my-face-registration" element={<ProtectedRoute roles={['FACULTY']}><AppShell><FaceRegistration mode="self" /></AppShell></ProtectedRoute>} />

      <Route path="*" element={token ? <AppShell><NotFound /></AppShell> : <Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
