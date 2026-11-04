import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function getDashboardPath(role) {
  if (role === 'HOD') return '/hod/dashboard';
  if (role === 'FACULTY') return '/faculty/dashboard';
  if (role === 'STUDENT') return '/student/dashboard';
  return '/login';
}

export default function ProtectedRoute({ roles, children }) {
  const { token, role } = useAuth();
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (roles && !roles.includes(role)) {
    return <Navigate to={getDashboardPath(role)} replace />;
  }

  return children ?? <Outlet />;
}
