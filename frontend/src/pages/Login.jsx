import { useState } from 'react';
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
    <main style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', fontFamily: 'Arial, sans-serif', background: '#f3f4f6' }}>
      <form onSubmit={handleSubmit} style={{ width: '360px', background: '#fff', padding: '24px', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.08)' }}>
        <h2 style={{ marginTop: 0, marginBottom: '20px', textAlign: 'center' }}>Smart Attendance System</h2>

        <div style={{ marginBottom: '16px' }}>
          <label htmlFor="username" style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Username</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box' }}
            placeholder="Enter username"
            required
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label htmlFor="password" style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            style={{ width: '100%', padding: '10px 12px', border: '1px solid #d1d5db', borderRadius: '6px', boxSizing: 'border-box' }}
            placeholder="Enter password"
            required
          />
        </div>

        {error ? <p style={{ color: '#b91c1c', marginBottom: '16px' }}>{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          style={{ width: '100%', padding: '10px 12px', border: 'none', borderRadius: '6px', background: '#2563eb', color: '#fff', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 600 }}
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </main>
  );
}
