import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Topbar from './Topbar';
import Sidebar from './Sidebar';

const pageTitles = {
  '/hod/dashboard': 'HOD Dashboard',
  '/academic-years': 'Academic Years',
  '/programmes': 'Programmes',
  '/faculty': 'Faculty',
  '/subjects': 'Subjects',
  '/labs': 'Labs',
  '/students': 'Students',
  '/faculty-availability': 'Faculty Availability',
  '/faculty/dashboard': 'Faculty Dashboard',
  '/student/dashboard': 'Student Dashboard',
  '/timetable': 'Academic Year Timetable',
  '/timetable/faculty': 'Faculty Timetable',
  '/timetable/department': 'Department Timetable',
  '/attendance': 'Attendance Session',
  '/reports': 'Attendance Reports',
  '/face-registration': 'Face Registration',
  '/my-face-registration': 'My Face Registration',
};

export default function AppShell({ children }) {
  const { role } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const title = pageTitles[location.pathname] || 'Smart Attendance System';

  return (
    <div className="app-shell">
      <Sidebar role={role} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {sidebarOpen ? <button type="button" className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar" /> : null}
      <div className="app-shell__main">
        <Topbar title={title} onToggleSidebar={() => setSidebarOpen((value) => !value)} />
        <main className="content-area">{children}</main>
      </div>
    </div>
  );
}
