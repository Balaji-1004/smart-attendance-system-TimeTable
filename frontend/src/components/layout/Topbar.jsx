import { useAuth } from '../../context/AuthContext';
import Badge from '../ui/Badge';

export default function Topbar({ title, onToggleSidebar }) {
  const { username, role, logout } = useAuth();

  return (
    <header className="topbar">
      <div className="topbar__left">
        <button type="button" className="hamburger" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          ☰
        </button>
        <h2>{title}</h2>
      </div>
      <div className="topbar__right">
        <Badge tone="primary">{role}</Badge>
        <span className="topbar__user">{username || 'User'}</span>
        <button type="button" className="button button-secondary" onClick={logout}>Log out</button>
      </div>
    </header>
  );
}
