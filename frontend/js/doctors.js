// MediAI - Doctors JS
const AI_BASE = 'http://localhost:8000';
const PHP_BASE = '../../backend_php';

function getUser() { try { return JSON.parse(sessionStorage.getItem('mediai_user') || 'null'); } catch { return null; } }
function logout() { sessionStorage.removeItem('mediai_user'); window.location.href = 'login.html'; }
function escHtml(t) { return String(t ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

let selectedDoctor = null;
let currentDoctors = [];
let currentAssessment = null;

const DEMO_DOCTORS = [
  { id: 1, source: 'demo', doctor_name: 'Dr. Rahim Ahmed', specialization: 'Cardiologist', hospital: 'Dhaka Medical College', location: 'Dhaka', availability: 'Mon-Fri', match_reason: 'Demo cardiology match' },
  { id: 2, source: 'demo', doctor_name: 'Dr. Nasrin Islam', specialization: 'Medicine Specialist', hospital: 'Square Hospital', location: 'Dhaka', availability: 'Sun-Thu', match_reason: 'Demo general medicine match' },
  { id: 3, source: 'demo', doctor_name: 'Dr. Karim Hossain', specialization: 'Neurologist', hospital: 'BIRDEM General Hospital', location: 'Dhaka', availability: 'Mon-Wed', match_reason: 'Demo neurology match' },
  { id: 4, source: 'demo', doctor_name: 'Dr. Fatema Begum', specialization: 'Pediatrician', hospital: 'Shishu Hospital', location: 'Chittagong', availability: 'Sat-Thu', match_reason: 'Demo pediatrics match' },
  { id: 5, source: 'demo', doctor_name: 'Dr. Arif Siddiqui', specialization: 'Dermatologist', hospital: 'Apollo Hospital', location: 'Dhaka', availability: 'Mon-Sat', match_reason: 'Demo dermatology match' },
  { id: 6, source: 'demo', doctor_name: 'Dr. Tariq Rahman', specialization: 'Gastroenterologist', hospital: 'Labaid Specialized', location: 'Dhaka', availability: 'Mon-Thu', match_reason: 'Demo gastroenterology match' },
];

function getStoredAssessment() {
  try { return JSON.parse(sessionStorage.getItem('mediai_last_assessment') || 'null'); } catch { return null; }
}

function conversationToText(conversation) {
  if (!Array.isArray(conversation)) return '';
  return conversation.map(item => {
    if (!item || typeof item !== 'object') return String(item || '');
    return [item.question, item.answer, item.content, item.text].filter(Boolean).join(' ');
  }).filter(Boolean).join(' ');
}

function buildAssessmentFromInputs() {
  const stored = getStoredAssessment() || {};
  const report = stored.report || stored;
  const doc = stored.document_analysis || {};
  const params = new URLSearchParams(window.location.search);
  const diagnoses = Array.isArray(doc.diagnoses) ? doc.diagnoses : [];
  const symptoms = Array.isArray(report.symptoms_listed) ? report.symptoms_listed : [];
  const conversation = Array.isArray(stored.conversation) ? stored.conversation : [];
  const conversationText = conversationToText(conversation);

  return {
    source: stored.source || 'manual',
    symptom: params.get('symptom') || stored.primary_symptom || stored.symptom || symptoms.join(', ') || '',
    possible_condition: params.get('condition') || report.possible_condition || diagnoses[0] || '',
    urgency: params.get('urgency') || report.urgency || '',
    specialist: params.get('specialization') || report.recommended_specialist || stored.specialist || '',
    report_text: params.get('report_text') || [report.reasoning, report.guidance, report.explanation, doc.notes, diagnoses.join(', '), conversationText].filter(Boolean).join(' '),
    conversation,
    report,
    document_analysis: doc,
  };
}

function summariseAssessment(a) {
  return [
    a.possible_condition ? `Condition: ${a.possible_condition}` : '',
    a.urgency ? `Urgency: ${String(a.urgency).toUpperCase()}` : '',
    a.symptom ? `Symptoms: ${a.symptom}` : '',
  ].filter(Boolean).join(' | ');
}

function applyAssessmentToForm() {
  currentAssessment = buildAssessmentFromInputs();
  const params = new URLSearchParams(window.location.search);
  const spec = params.get('specialization') || currentAssessment.specialist;
  const loc = params.get('location') || '';
  const context = params.get('symptom') || currentAssessment.symptom || currentAssessment.possible_condition;

  if (spec) document.getElementById('searchSpec').value = spec;
  if (loc) document.getElementById('searchLocation').value = loc;
  if (context) document.getElementById('searchContext').value = context;

  const banner = document.getElementById('assessmentContextBanner');
  const summary = summariseAssessment(currentAssessment);
  if (summary) {
    banner.style.display = 'flex';
    banner.innerHTML = `<span>${escHtml(summary)}</span>`;
  }
}

function renderDoctors(doctors) {
  currentDoctors = doctors || [];
  const grid = document.getElementById('doctorGrid');
  const empty = document.getElementById('doctorEmpty');
  if (!currentDoctors.length) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }

  empty.style.display = 'none';
  grid.innerHTML = currentDoctors.map(d => {
    const schedule = d.availability || (d.experience ? `${d.experience} years experience` : 'Schedule flexible');
    const focus = d.focus_areas ? String(d.focus_areas).split(',').slice(0, 3).join(', ') : '';
    const score = d.match_score ? `<span class="badge badge-low">${escHtml(d.match_score)} match</span>` : '';
    return `
      <div class="doctor-card">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
          <div class="doctor-avatar">+</div>
          ${score}
        </div>
        <div class="doctor-name">${escHtml(d.doctor_name)}</div>
        <div class="doctor-spec">${escHtml(d.specialization)}</div>
        <div class="doctor-hospital">${escHtml(d.hospital || 'Clinic details available at booking')}</div>
        <div class="text-muted mt-8">${escHtml(d.location || 'Location not listed')} | ${escHtml(schedule)}</div>
        ${d.education ? `<div class="text-muted mt-8">${escHtml(d.education)}</div>` : ''}
        ${focus ? `<div class="text-muted mt-8">Focus: ${escHtml(focus)}</div>` : ''}
        ${d.match_reason ? `<div class="alert alert-info mt-16" style="padding:10px 12px;margin-bottom:0">${escHtml(d.match_reason)}</div>` : ''}
        <button class="btn-book" data-book-id="${escHtml(d.id)}">Book Appointment</button>
      </div>`;
  }).join('');

  grid.querySelectorAll('[data-book-id]').forEach(btn => {
    btn.addEventListener('click', () => openBookModal(btn.getAttribute('data-book-id')));
  });
}

async function searchDoctors() {
  const spec = document.getElementById('searchSpec').value.trim();
  const loc = document.getElementById('searchLocation').value.trim();
  const contextText = document.getElementById('searchContext').value.trim();
  currentAssessment = buildAssessmentFromInputs();

  const payload = {
    specialization: spec,
    location: loc,
    symptom: contextText || currentAssessment.symptom,
    possible_condition: currentAssessment.possible_condition,
    report_text: currentAssessment.report_text,
    urgency: currentAssessment.urgency,
    conversation: currentAssessment.conversation || [],
    report: currentAssessment.report || null,
    limit: 24,
  };

  try {
    let res = await fetch(`${AI_BASE}/doctor-recommendation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.status === 404 || res.status === 405) {
      const params = new URLSearchParams();
      Object.entries(payload).forEach(([key, value]) => {
        if (typeof value === 'string' && value) params.set(key, value);
      });
      params.set('limit', String(payload.limit));
      res = await fetch(`${AI_BASE}/doctor-recommendation?${params.toString()}`);
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Doctor recommendation failed.');
    renderDoctors(data.doctors || []);
    renderResultMeta(data);
  } catch {
    let filtered = DEMO_DOCTORS;
    if (spec) filtered = filtered.filter(d => d.specialization.toLowerCase().includes(spec.toLowerCase()));
    if (loc) filtered = filtered.filter(d => d.location.toLowerCase().includes(loc.toLowerCase()));
    renderDoctors(filtered);
    document.getElementById('doctorResultMeta').textContent = 'Showing offline demo doctors because the AI service is unavailable.';
  }
}

function renderResultMeta(data) {
  const meta = document.getElementById('doctorResultMeta');
  const specs = data.specialists_considered?.length ? data.specialists_considered.join(', ') : data.inferred_specialization;
  const conditions = data.possible_conditions?.length ? ` Possible conditions considered: ${data.possible_conditions.slice(0, 3).join(', ')}.` : '';
  const contextBits = [];
  if (data.assessment_context?.used_conversation) contextBits.push('conversation');
  if (data.assessment_context?.used_report) contextBits.push('report');
  const contextText = contextBits.length ? ` Context used: ${contextBits.join(' and ')}.` : '';
  meta.textContent = specs ? `Matched using: ${specs}.${conditions}${contextText}` : '';
}

function filterSpec(spec) {
  document.getElementById('searchSpec').value = spec;
  searchDoctors();
}

function buildBookingNote(doctor) {
  const a = currentAssessment || buildAssessmentFromInputs();
  const summary = summariseAssessment(a);
  const conversation = conversationToText(a.conversation).slice(0, 260);
  const parts = [
    summary ? `Assessment summary: ${summary}` : '',
    doctor?.match_reason ? `Doctor match: ${doctor.match_reason}` : '',
    a.report_text ? `Report notes: ${a.report_text.slice(0, 260)}` : '',
    conversation ? `Conversation context: ${conversation}` : '',
  ].filter(Boolean);
  return parts.join('\n');
}

function openBookModal(id) {
  selectedDoctor = currentDoctors.find(d => String(d.id) === String(id)) || null;
  if (!selectedDoctor) return;

  document.getElementById('bookDoctorName').textContent = 'Book with ' + selectedDoctor.doctor_name;
  document.getElementById('bookModal').style.display = 'flex';
  const assessment = currentAssessment || buildAssessmentFromInputs();
  const summary = document.getElementById('bookingDoctorSummary');
  const details = [
    selectedDoctor.specialization,
    selectedDoctor.hospital,
    selectedDoctor.location,
    selectedDoctor.match_reason,
  ].filter(Boolean).join(' | ');
  if (details) {
    summary.style.display = 'block';
    summary.innerHTML = `<span>${escHtml(details)}</span>`;
  } else {
    summary.style.display = 'none';
  }
  const today = new Date();
  if (String(assessment.urgency || '').toLowerCase() !== 'high') today.setDate(today.getDate() + 1);
  document.getElementById('apptDate').min = today.toISOString().split('T')[0];
  document.getElementById('apptDate').value = today.toISOString().split('T')[0];
  document.getElementById('visitType').value = String(assessment.urgency || '').toLowerCase() === 'high' ? 'Urgent review' : 'In-person consultation';
  document.getElementById('apptTime').value = '09:00';
  document.getElementById('contactPreference').value = 'Call me';
  document.getElementById('apptNotes').value = buildBookingNote(selectedDoctor);
}

function closeBookModal() { document.getElementById('bookModal').style.display = 'none'; }

function toMysqlDateTime(date, time12h) {
  const [time, meridiem] = String(time12h || '').trim().split(' ');
  let [hours, minutes] = (time || '09:00').split(':').map(Number);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return `${date} 09:00:00`;
  if (meridiem === 'PM' && hours < 12) hours += 12;
  if (meridiem === 'AM' && hours === 12) hours = 0;
  return `${date} ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:00`;
}

async function confirmBooking() {
  const u = getUser();
  const date = document.getElementById('apptDate').value;
  const time = document.getElementById('apptTime').value;
  const notes = document.getElementById('apptNotes').value;
  const visitType = document.getElementById('visitType').value;
  const contactPreference = document.getElementById('contactPreference').value;
  if (!date) { alert('Please select a date.'); return; }
  if (!selectedDoctor) { alert('Please select a doctor.'); return; }

  try {
    const fd = new FormData();
    fd.append('user_id', u?.id || 1);
    fd.append('doctor_id', selectedDoctor.id || 0);
    fd.append('doctor_source', selectedDoctor.source || 'csv');
    fd.append('doctor_name', selectedDoctor.doctor_name || '');
    fd.append('specialization', selectedDoctor.specialization || '');
    fd.append('hospital', selectedDoctor.hospital || '');
    fd.append('location', selectedDoctor.location || '');
    fd.append('contact', selectedDoctor.contact || '');
    fd.append('appointment_date', toMysqlDateTime(date, time));
    fd.append('notes', [
      `Visit type: ${visitType}`,
      `Contact preference: ${contactPreference}`,
      notes,
    ].filter(Boolean).join('\n'));
    const res = await fetch(PHP_BASE + '/api/appointments.php', { method: 'POST', body: fd });
    const data = await res.json();
    if (data.success) { closeBookModal(); alert('Appointment booked successfully!'); }
    else throw new Error(data.message || 'Failed to save appointment.');
  } catch (err) {
    alert(err?.message || 'Could not book the appointment. Please try again.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const u = getUser();
  const el = document.getElementById('sidebarUserName');
  if (el) el.textContent = u ? u.first_name + ' ' + u.last_name : 'Guest';
  applyAssessmentToForm();
  searchDoctors();
});
