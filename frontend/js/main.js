// ============================================================
// MediAI — Main JS Utilities
// ============================================================

const API_BASE = 'http://localhost:8000'; // FastAPI
const PHP_BASE = '../backend_php';        // PHP backend

// ---- Session helpers ----
function getUser() {
  try { return JSON.parse(sessionStorage.getItem('mediai_user') || 'null'); } catch { return null; }
}
function setUser(u) { sessionStorage.setItem('mediai_user', JSON.stringify(u)); }
function clearUser() { sessionStorage.removeItem('mediai_user'); }
function requireAuth() {
  if (!getUser()) { window.location.href = '../pages/login.html'; return false; }
  return true;
}
function logout() {
  clearUser();
  window.location.href = '../pages/login.html';
}

// ---- AJAX helpers ----
async function apiPost(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}
async function apiGet(url) {
  const res = await fetch(url);
  return res.json();
}
async function phpPost(endpoint, data) {
  const fd = new FormData();
  Object.entries(data).forEach(([k,v]) => fd.append(k, v));
  const res = await fetch(PHP_BASE + endpoint, { method: 'POST', body: fd });
  return res.json();
}
async function phpGet(endpoint) {
  const res = await fetch(PHP_BASE + endpoint);
  return res.json();
}

// ---- Date helpers ----
function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' });
}
function fmtTime(d) {
  return new Date(d).toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' });
}

// ---- Sidebar user ----
document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('sidebarUserName');
  if (el) {
    const u = getUser();
    el.textContent = u ? (u.first_name + ' ' + u.last_name) : 'Guest';
  }
});
