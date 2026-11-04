import { NavLink } from 'react-router-dom';

const navConfig = {
  HOD: [
    { to: '/hod/dashboard', label: 'Dashboard' },
    { to: '/timetable', label: 'Timetable' },
    { to: '/timetable/department', label: 'Department Timetable' },
    { to: '/attendance', label: 'Attendance' },
    { to: '/face-registration', label: 'Face Registration' },
  ],
  FACULTY: [
    { to: '/faculty/dashboard', label: 'Dashboard' },
    { to: '/timetable', label: 'My Timetable' },
    { to: '/timetable/faculty', label: 'Year Timetable' },
    { to: '/attendance', label: 'Attendance' },
  ],
  STUDENT: [
    { to: '/student/dashboard', label: 'Dashboard' },
  ],
};

export default function Sidebar({ role, open, onClose }) {
  const items = navConfig[role] || navConfig.STUDENT;

  return (
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="sidebar__brand">
        <span className="brand-mark">✓</span>
        <div>
          <strong>Smart Attendance</strong>
          <small>Dept. of CS</small>
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
