// MediSA Frontend API Client & State Helpers

export const getDjangoBase = () => {
  if (typeof window !== 'undefined') {
    return '/api-django';
  }
  return process.env.DJANGO_URL ? `${process.env.DJANGO_URL}/api` : 'http://localhost:8082/api';
};

export const getAiBase = () => {
  if (typeof window !== 'undefined') {
    return '/api-ai';
  }
  return process.env.AI_URL || 'http://localhost:8000';
};

export function getUser() {
  if (typeof window === 'undefined') return null;
  try {
    return JSON.parse(sessionStorage.getItem('mediai_user') || 'null');
  } catch {
    return null;
  }
}

export function setUser(user) {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem('mediai_user', JSON.stringify(user));
}

export function clearUser() {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem('mediai_user');
}

export function logout() {
  clearUser();
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
}

export function fmtDate(d) {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return String(d);
  }
}

export function fmtTime(d) {
  if (!d) return '';
  try {
    return new Date(d).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}
