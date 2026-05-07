// MediAI - Medications JS
const PHP_BASE = '../../backend_php';

function getUser() { try { return JSON.parse(sessionStorage.getItem('mediai_user') || 'null'); } catch { return null; } }
function logout() { sessionStorage.removeItem('mediai_user'); window.location.href = 'login.html'; }
function escHtml(t) { return String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

const FREQ_LABELS = {
  once_daily: 'Once daily',
  twice_daily: 'Twice daily',
  three_times: 'Three times daily',
  four_times: 'Four times daily',
  every_8h: 'Every 8 hours',
  every_6h: 'Every 6 hours',
  as_needed: 'As needed',
  weekly: 'Weekly',
};

let meds = [];

function fmtDate(value) {
  return value ? new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '-';
}

function renderMeds() {
  const el = document.getElementById('medList');
  if (!meds.length) {
    el.innerHTML = '<p class="text-muted">No medications scheduled.</p>';
    return;
  }

  el.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Medication</th><th>Dosage</th><th>Frequency</th><th>Dates</th><th>Source</th><th></th></tr></thead>
      <tbody>
        ${meds.map(m => `
          <tr>
            <td>
              <span class="med-pill">${escHtml(m.medicine_name)}</span>
              ${m.instructions ? `<div class="text-muted mt-8">${escHtml(m.instructions)}</div>` : ''}
            </td>
            <td>${escHtml(m.dosage || '-')}</td>
            <td>${escHtml(FREQ_LABELS[m.frequency] || m.frequency || '-')}</td>
            <td>${fmtDate(m.start_date)}${m.end_date ? ' - ' + fmtDate(m.end_date) : ''}</td>
            <td>${escHtml(m.document_name || 'Manual')}</td>
            <td><button onclick="removeMed(${Number(m.id)})" style="background:none;border:none;cursor:pointer;color:var(--ink-muted);font-size:16px" title="Remove">x</button></td>
          </tr>`).join('')}
      </tbody>
    </table>`;
}

async function addMedication() {
  const name = document.getElementById('medName').value.trim();
  const dose = document.getElementById('medDose').value.trim();
  const freq = document.getElementById('medFreq').value;
  const start = document.getElementById('medStart').value;
  const end = document.getElementById('medEnd').value;
  const instructions = document.getElementById('medInstructions').value.trim();
  if (!name) {
    alert('Please enter a medication name.');
    return;
  }

  const u = getUser();

  try {
    const fd = new FormData();
    fd.append('user_id', u?.id || 1);
    fd.append('medicine_name', name);
    fd.append('dosage', dose);
    fd.append('frequency', freq);
    if (start) fd.append('start_date', start);
    if (end) fd.append('end_date', end);
    fd.append('instructions', instructions);
    const res = await fetch(PHP_BASE + '/api/medications.php', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || 'Failed to save medication.');
  } catch (err) {
    alert(err?.message || 'Could not save this medication.');
    return;
  }

  await loadMeds();
  ['medName', 'medDose', 'medInstructions'].forEach(id => { document.getElementById(id).value = ''; });
  document.getElementById('medEnd').value = '';
}

async function removeMed(id) {
  if (!confirm('Remove this medication?')) return;
  const u = getUser();
  try {
    const res = await fetch(PHP_BASE + '/api/medications.php', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, user_id: u?.id || 1 })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || 'Failed to remove medication.');
    await loadMeds();
  } catch (err) {
    alert(err?.message || 'Could not remove this medication.');
  }
}

async function loadMeds() {
  const u = getUser();
  try {
    const res = await fetch(PHP_BASE + '/api/medications.php?user_id=' + (u?.id || 1));
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.message || 'Could not load medications.');
    meds = data.medications || [];
    renderMeds();
  } catch (err) {
    document.getElementById('medList').innerHTML = `<p class="text-muted">${escHtml(err?.message || 'Could not load medications.')}</p>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const u = getUser();
  const el = document.getElementById('sidebarUserName');
  if (el) el.textContent = u ? u.first_name + ' ' + u.last_name : 'Guest';
  document.getElementById('medStart').value = new Date().toISOString().split('T')[0];
  loadMeds();
});
