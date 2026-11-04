import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

const clearAuthAndRedirect = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('smart_attendance_auth');
  sessionStorage.removeItem('token');
  window.dispatchEvent(new Event('auth-logout'));
  window.location.assign('/login');
};

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');

  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/auth/login');
    if (error.response?.status === 401 && !isLoginRequest) {
      clearAuthAndRedirect();
    }
    return Promise.reject(error);
  }
);

export default api;
