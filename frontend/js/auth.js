// ============================================================
// MediAI — Auth JS (login + register)
// ============================================================

const PHP_BASE = '../../backend_php';

function getUser() {
  try { return JSON.parse(sessionStorage.getItem('mediai_user') || 'null'); } catch { return null; }
}
function setUser(u) { sessionStorage.setItem('mediai_user', JSON.stringify(u)); }
function logout() { sessionStorage.removeItem('mediai_user'); window.location.href = 'login.html'; }

function showError(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.add('show'); }
}
function hideError(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('show');
}

async function handleLogin(e) {
  e.preventDefault();
  hideError('loginError');
  const btn = document.getElementById('loginBtn');
  btn.disabled = true; btn.textContent = 'Signing in...';

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  try {
    const fd = new FormData();
    fd.append('email', email); fd.append('password', password);
    const res = await fetch(PHP_BASE + '/auth/login.php', { method: 'POST', body: fd });
    const data = await res.json();

    if (data.success) {
      setUser(data.user);
      window.location.href = 'dashboard.html';
    } else {
      showError('loginError', data.message || 'Invalid credentials.');
    }
  } catch {
    // Demo mode: allow login with any credentials
    setUser({ id: 1, first_name: 'Demo', last_name: 'User', email, role: 'patient' });
    window.location.href = 'dashboard.html';
  } finally {
    btn.disabled = false; btn.textContent = 'Sign In';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  hideError('regError');

  const pass1 = document.getElementById('password').value;
  const pass2 = document.getElementById('password2').value;
  if (pass1 !== pass2) { showError('regError', 'Passwords do not match.'); return; }

  const btn = document.getElementById('regBtn');
  btn.disabled = true; btn.textContent = 'Creating account...';

  const payload = {
    first_name: document.getElementById('first_name').value,
    last_name: document.getElementById('last_name').value,
    email: document.getElementById('email').value,
    phone: document.getElementById('phone').value,
    dob: document.getElementById('dob').value,
    password: pass1
  };

  try {
    const fd = new FormData();
    Object.entries(payload).forEach(([k,v]) => fd.append(k, v));
    const res = await fetch(PHP_BASE + '/auth/register.php', { method: 'POST', body: fd });
    const data = await res.json();

    if (data.success) {
      setUser(data.user);
      window.location.href = 'dashboard.html';
    } else {
      showError('regError', data.message || 'Registration failed.');
    }
  } catch {
    // Demo mode
    setUser({ id: 1, first_name: payload.first_name, last_name: payload.last_name, email: payload.email, role: 'patient' });
    window.location.href = 'dashboard.html';
  } finally {
    btn.disabled = false; btn.textContent = 'Create Account';
  }
}
