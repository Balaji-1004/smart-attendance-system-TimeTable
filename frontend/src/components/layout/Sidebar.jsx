import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

const navConfig = {
  HOD: [
    { to: '/hod/dashboard', label: 'Dashboard' },
    { to: '/programmes', label: 'Programmes' },
    { to: '/academic-years', label: 'Academic Years' },
    { to: '/faculty', label: 'Faculty' },
    { to: '/subjects', label: 'Subjects' },
    { to: '/labs', label: 'Labs' },
    { to: '/students', label: 'Students' },
    { to: '/faculty-availability', label: 'Faculty Availability' },
    { to: '/timetable', label: 'Timetable' },
    { to: '/timetable/department', label: 'Department Timetable' },
    { to: '/attendance', label: 'Attendance' },
    { to: '/reports', label: 'Reports' },
    { to: '/face-registration', label: 'Face Registration' },
  ],
  FACULTY: [
    { to: '/faculty/dashboard', label: 'Dashboard' },
    { to: '/timetable', label: 'My Timetable' },
    { to: '/timetable/faculty', label: 'Year Timetable' },
    { to: '/attendance', label: 'Attendance' },
    { to: '/reports', label: 'Reports' },
    { to: '/my-face-registration', label: 'My Face Registration' },
  ],
  STUDENT: [
    { to: '/student/dashboard', label: 'Dashboard' },
  ],
};

export default function Sidebar({ role, open, onClose }) {
  const { token } = useAuth();
  const [departmentName, setDepartmentName] = useState('Department');
  const items = navConfig[role] || navConfig.STUDENT;

  useEffect(() => {
    if (!token) {
      setDepartmentName('Department');
      return;
    }

    api.get('/departments/me')
      .then((response) => {
        setDepartmentName(response?.data?.name || 'Department');
      })
      .catch(() => {
        setDepartmentName('Department');
      });
  }, [token]);

  return (
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="sidebar__brand">
        <span className="brand-mark">✓</span>
        <div>
          <strong>Smart Attendance</strong>
          <small>{departmentName}</small>
        </div>
      </div>
      <nav className="sidebar__nav">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}
            onClick={onClose}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
