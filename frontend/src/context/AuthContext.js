import { createContext, useContext, useEffect, useMemo, useState, createElement } from 'react';
import api from '../services/api';

const defaultAuthState = {
  token: '',
  username: '',
  role: '',
  department_id: null,
  faculty_id: null,
  student_id: null,
};

const STORAGE_KEY = 'smart_attendance_auth';

function readStoredAuth() {
  const localEntry = localStorage.getItem(STORAGE_KEY);
  if (localEntry) {
    try {
      const parsed = JSON.parse(localEntry);
      return {
        token: parsed.token || '',
        username: parsed.username || '',
        role: parsed.role || '',
        department_id: parsed.department_id ?? null,
        faculty_id: parsed.faculty_id ?? null,
        student_id: parsed.student_id ?? null,
      };
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
  return {
    ...defaultAuthState,
    token,
  };
}

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(() => readStoredAuth());

  useEffect(() => {
    const handleLogout = () => {
      setAuth(defaultAuthState);
      localStorage.removeItem('token');
      localStorage.removeItem(STORAGE_KEY);
      sessionStorage.removeItem('token');
    };

    window.addEventListener('auth-logout', handleLogout);
    return () => window.removeEventListener('auth-logout', handleLogout);
  }, []);

  useEffect(() => {
    if (auth.token) {
      localStorage.setItem('token', auth.token);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
    } else {
      localStorage.removeItem('token');
      localStorage.removeItem(STORAGE_KEY);
      sessionStorage.removeItem('token');
    }
  }, [auth]);

  const login = async (username, password) => {
    const response = await api.post('/auth/login', { username, password });
    const nextAuth = {
      token: response.data.access_token,
      username: response.data.username,
      role: response.data.role,
      department_id: response.data.department_id ?? null,
      faculty_id: response.data.faculty_id ?? null,
      student_id: response.data.student_id ?? null,
    };

    setAuth(nextAuth);
    return nextAuth;
  };

  const logout = () => {
    setAuth(defaultAuthState);
    localStorage.removeItem('token');
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem('token');
    window.dispatchEvent(new Event('auth-logout'));
  };

  const value = useMemo(
    () => ({
      ...auth,
      login,
      logout,
    }),
    [auth]
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}

export default AuthContext;
