// MediAI — Appointments JS
const PHP_BASE = '../../backend_php';

function getUser() { try { return JSON.parse(sessionStorage.getItem('mediai_user')||'null'); } catch { return null; } }
function logout() { sessionStorage.removeItem('mediai_user'); window.location.href = 'login.html'; }
function escHtml(t) { return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

const DEMO_APPTS = [
  { id:1, doctor_name:'Dr. Rahim Ahmed', specialization:'Cardiologist', hospital:'Dhaka Medical College', appointment_date:'2026-03-20T10:00:00', status:'confirmed', notes:'Chest pain follow-up' },
  { id:2, doctor_name:'Dr. Nasrin Islam', specialization:'General Physician', hospital:'Square Hospital', appointment_date:'2026-03-25T14:00:00', status:'pending', notes:'' },
];
const DEMO_PAST = [
  { id:3, doctor_name:'Dr. Karim Hossain', specialization:'Neurologist', hospital:'BIRDEM', appointment_date:'2026-02-15T09:00:00', status:'completed', notes:'Migraine consultation' },
];

function renderApptItem(a) {
  const d = new Date(a.appointment_date);
  const statusColor = { confirmed:'badge-low', pending:'badge-medium', completed:'badge-low', cancelled:'badge-high' }[a.status]||'badge-medium';
  return `
    <div class="appt-item">
      <div class="appt-date">
        <div class="day">${d.getDate()}</div>
        <div class="month">${d.toLocaleString('en',{month:'short'})}</div>
      </div>
      <div class="appt-info">
        <div class="appt-doctor">${escHtml(a.doctor_name)}</div>
        <div class="appt-detail">${escHtml(a.specialization)} · ${escHtml(a.hospital)} · ${d.toLocaleTimeString('en',{hour:'2-digit',minute:'2-digit'})}</div>
        ${a.notes?`<div class="text-muted" style="font-size:12px;margin-top:2px">${escHtml(a.notes)}</div>`:''}
      </div>
      <span class="badge ${statusColor}" style="flex-shrink:0">${a.status}</span>
    </div>`;
}

async function loadAppointments() {
  const u = getUser();
  try {
    const res = await fetch(PHP_BASE + '/api/appointments.php?user_id=' + (u?.id||1));
    const data = await res.json();
    const now = new Date();
    const upcoming = (data.appointments||[]).filter(a=>new Date(a.appointment_date)>=now);
    const past = (data.appointments||[]).filter(a=>new Date(a.appointment_date)<now);
    document.getElementById('upcomingList').innerHTML = upcoming.length ? upcoming.map(renderApptItem).join('') : '<p class="text-muted">No upcoming appointments.</p>';
    document.getElementById('pastList').innerHTML = past.length ? past.map(renderApptItem).join('') : '<p class="text-muted">No past appointments.</p>';
  } catch {
    document.getElementById('upcomingList').innerHTML = DEMO_APPTS.map(renderApptItem).join('');
    document.getElementById('pastList').innerHTML = DEMO_PAST.map(renderApptItem).join('');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const u = getUser();
  const el = document.getElementById('sidebarUserName');
  if (el) el.textContent = u ? u.first_name + ' ' + u.last_name : 'Guest';
  loadAppointments();
});
