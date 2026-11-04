import { useState } from 'react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(username, password);
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Login failed. Please check your credentials.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <Card className="auth-card">
        <div className="auth-mark" aria-hidden="true">✓</div>
        <p className="auth-kicker">Student Smart Attendance System</p>
        <h1>Sign in</h1>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter username"
              required
            />
          </div>

          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
              required
            />
          </div>

          {error ? <p className="form-error" role="alert">{error}</p> : null}

          <Button type="submit" variant="primary" loading={loading} className="auth-submit">
            Login
          </Button>
        </form>
      </Card>
    </main>
  );
}
