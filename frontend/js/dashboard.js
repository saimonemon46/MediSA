// MediAI — Dashboard JS
const AI_BASE = 'http://localhost:8000';
const PHP_BASE = '../../backend_php';

function getUser() { try { return JSON.parse(sessionStorage.getItem('mediai_user')||'null'); } catch { return null; } }
function logout() { sessionStorage.removeItem('mediai_user'); window.location.href = 'login.html'; }

function fmtDate(d) { return new Date(d).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}); }

async function loadDashboard() {
  const u = getUser();
  if (!u) { window.location.href = 'login.html'; return; }

  document.getElementById('greetName').textContent = u.first_name || 'there';
  document.getElementById('sidebarUserName').textContent = u.first_name + ' ' + u.last_name;

  try {
    // Load stats
    const stats = await fetch(PHP_BASE + '/api/dashboard.php?user_id=' + u.id).then(r=>r.json());
    document.getElementById('statSessions').textContent = stats.sessions ?? 0;
    document.getElementById('statReports').textContent = stats.reports ?? 0;
    document.getElementById('statMeds').textContent = stats.medications ?? 0;
    document.getElementById('statAppts').textContent = stats.appointments ?? 0;

    // Load recent reports
    if (stats.recent_reports?.length) {
      const rows = stats.recent_reports.map(r => `
        <tr>
          <td>${fmtDate(r.created_at)}</td>
          <td>${r.possible_condition}</td>
          <td><span class="badge badge-${r.urgency}">${r.urgency}</span></td>
        </tr>`).join('');
      document.getElementById('reportsBody').innerHTML = rows;
    }
  } catch {
    // Demo data
    document.getElementById('statSessions').textContent = '3';
    document.getElementById('statReports').textContent = '3';
    document.getElementById('statMeds').textContent = '2';
    document.getElementById('statAppts').textContent = '1';
    document.getElementById('reportsBody').innerHTML = `
      <tr><td>12 Mar 2026</td><td>Viral Respiratory Infection</td><td><span class="badge badge-medium">medium</span></td></tr>
      <tr><td>05 Mar 2026</td><td>Migraine</td><td><span class="badge badge-medium">medium</span></td></tr>
      <tr><td>20 Feb 2026</td><td>Allergic Rhinitis</td><td><span class="badge badge-low">low</span></td></tr>`;
    document.getElementById('upcomingAppts').innerHTML = `
      <div class="appt-item">
        <div class="appt-date"><div class="day">20</div><div class="month">Mar</div></div>
        <div class="appt-info">
          <div class="appt-doctor">Dr. Rahman</div>
          <div class="appt-detail">Cardiologist · City Hospital · 10:00 AM</div>
        </div>
      </div>`;
    document.getElementById('medReminders').innerHTML = `
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <span class="med-pill">◇ Paracetamol 500mg · Twice daily</span>
        <span class="med-pill">◇ Cetirizine 10mg · Once daily</span>
      </div>`;
  }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
