// ============================================================
// MediAI - Symptom Chat JS
// Manages LangGraph multi-step AI conversation
// ============================================================

const AI_BASE = 'http://localhost:8000';
const PHP_BASE = '../../backend_php';

let sessionId = null;
let stage = 'initial'; // initial | followup | analysis | done
let followupAnswers = [];
let primarySymptom = '';
let currentReport = null;

function getUser() {
  try { return JSON.parse(sessionStorage.getItem('mediai_user') || 'null'); } catch { return null; }
}
function logout() { sessionStorage.removeItem('mediai_user'); window.location.href = 'login.html'; }

function autoResize(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}

function setStage(s) {
  stage = s;
  const labels = { initial:'Describe your symptoms', followup:'Answering questions', analysis:'Analysing...', done:'Report ready' };
  document.getElementById('stageLabel').textContent = labels[s] || s;
  ['dot1', 'dot2', 'dot3', 'dot4'].forEach((id, i) => {
    const el = document.getElementById(id);
    el.className = 'stage-dot';
    if (i < (['initial', 'followup', 'analysis', 'done'].indexOf(s))) el.classList.add('done');
    else if (i === (['initial', 'followup', 'analysis', 'done'].indexOf(s))) el.classList.add('active');
  });
}

function addMessage(text, sender) {
  const box = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = sender === 'ai' ? 'msg msg-ai' : 'msg msg-user';
  if (sender === 'ai') {
    div.innerHTML = '<div class="msg-label">MediAI</div>' + escHtml(text).replace(/\n/g, '<br>');
  } else {
    div.textContent = text;
  }
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function addTyping() {
  const box = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'msg-typing';
  div.id = 'typingIndicator';
  div.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function escHtml(t) {
  return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function setSendDisabled(v) {
  document.getElementById('sendBtn').disabled = v;
  document.getElementById('chatInput').disabled = v;
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  input.style.height = 'auto';
  addMessage(text, 'user');
  setSendDisabled(true);

  if (stage === 'initial') {
    primarySymptom = text;
    await startSession(text);
  } else if (stage === 'followup') {
    followupAnswers.push(text);
    await submitAnswer(text);
  }
}

async function startSession(symptomText) {
  setStage('followup');
  addTyping();
  try {
    const res = await fetch(AI_BASE + '/generate-questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symptom: symptomText, user_id: getUser()?.id || 1 })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to start the symptom session.');

    removeTyping();
    sessionId = data.session_id;
    document.getElementById('sessionId').textContent = '#' + sessionId;

    if (data.questions && data.questions.length > 0) {
      const intro = 'Thank you. To give you a better assessment, I have a few questions:\n\n' + data.questions[0];
      addMessage(intro, 'ai');
      window._questions = data.questions;
      window._qIdx = 0;
    } else {
      addMessage("I've gathered initial information. Let me analyse your symptoms now.", 'ai');
      await generateReport();
    }
  } catch (err) {
    removeTyping();
    addMessage(err?.message || 'I could not start the symptom session. Please try again.', 'ai');
  }
  setSendDisabled(false);
}

async function submitAnswer(answer) {
  window._qIdx = (window._qIdx || 0) + 1;
  const questions = window._questions || [];

  if (window._qIdx < questions.length) {
    addMessage(questions[window._qIdx], 'ai');
    setSendDisabled(false);
  } else {
    setStage('analysis');
    addMessage('Thank you for your answers. Analysing your symptoms now...', 'ai');
    await generateReport();
  }
}

async function generateReport() {
  setSendDisabled(true);
  addTyping();

  try {
    const res = await fetch(AI_BASE + '/generate-report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        symptom: primarySymptom,
        answers: followupAnswers,
        user_id: getUser()?.id || 1
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to generate report.');

    const saved = await persistReport(data.report);

    removeTyping();
    currentReport = { ...data.report, report_id: saved.report_id };
    cacheAssessment(currentReport);
    displayReportReady(data.report);
  } catch (err) {
    removeTyping();
    addMessage(err?.message || 'I could not generate or save the report just now. Please try again.', 'ai');
    setStage('followup');
    setSendDisabled(false);
  }
}

async function persistReport(report) {
  const payload = {
    user_id: getUser()?.id || 1,
    session_id: sessionId,
    possible_condition: report?.possible_condition || '',
    urgency: report?.urgency || 'medium',
    recommended_specialist: report?.recommended_specialist || '',
    reasoning: report?.reasoning || '',
    guidance: report?.guidance || '',
    explanation: report?.explanation || '',
    symptoms_listed: Array.isArray(report?.symptoms_listed)
      ? report.symptoms_listed
      : [primarySymptom, ...followupAnswers].filter(Boolean)
  };

  const saveRes = await fetch(PHP_BASE + '/api/reports.php', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const saveData = await saveRes.json();
  if (!saveRes.ok || !saveData.success) {
    throw new Error(saveData.message || 'Failed to save report.');
  }
  return saveData;
}

function cacheAssessment(report) {
  const payload = {
    source: 'symptom-chat',
    saved_at: new Date().toISOString(),
    session_id: sessionId,
    primary_symptom: primarySymptom,
    answers: followupAnswers,
    report,
  };
  sessionStorage.setItem('mediai_last_assessment', JSON.stringify(payload));
}

function reportContextText(report) {
  return [
    report?.reasoning || '',
    report?.guidance || '',
    report?.explanation || '',
    Array.isArray(report?.symptoms_listed) ? report.symptoms_listed.join(', ') : '',
    followupAnswers.join(', ')
  ].filter(Boolean).join(' ');
}

function doctorLinkForReport(report) {
  const params = new URLSearchParams();
  if (report?.recommended_specialist) params.set('specialization', report.recommended_specialist);
  if (primarySymptom) params.set('symptom', primarySymptom);
  if (report?.possible_condition) params.set('condition', report.possible_condition);
  if (report?.urgency) params.set('urgency', report.urgency);
  const context = reportContextText(report).slice(0, 700);
  if (context) params.set('report_text', context);
  return `doctors.html?${params.toString()}`;
}

function displayReportReady(report) {
  setStage('done');
  const msg = `Your triage report is ready.\n\nPossible condition: ${report.possible_condition}\nUrgency: ${report.urgency?.toUpperCase()}\nRecommended specialist: ${report.recommended_specialist}\n\nClick "View Report" for the full analysis.`;
  addMessage(msg, 'ai');
  document.getElementById('viewReportBtn').style.display = 'inline-block';
  setSendDisabled(false);
  renderReportPanel(report);
  loadDoctorSuggestions(report);
}

function renderReportPanel(r) {
  const urgencyClass = { high:'badge-high', medium:'badge-medium', low:'badge-low' }[r.urgency] || 'badge-medium';
  const symptoms = Array.isArray(r.symptoms_listed)
    ? r.symptoms_listed.map(s => `<li>${escHtml(s)}</li>`).join('')
    : `<li>${escHtml(primarySymptom)}</li>`;

  document.getElementById('reportContent').innerHTML = `
    <div class="report-header" style="margin:-28px -28px 24px;padding:24px 28px;background:var(--teal);color:#fff;border-radius:var(--radius-lg) var(--radius-lg) 0 0">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;opacity:0.7;margin-bottom:8px">Triage Report</div>
      <div class="condition-name" style="color:#fff">${escHtml(r.possible_condition || '-')}</div>
      <div style="margin-top:8px"><span class="badge ${urgencyClass}" style="background:rgba(255,255,255,0.2);color:#fff">${(r.urgency || 'medium').toUpperCase()} URGENCY</span></div>
    </div>

    <div class="report-section">
      <h4>Symptoms reported</h4>
      <ul class="symptoms-list">${symptoms}</ul>
    </div>

    <div class="report-section">
      <h4>AI reasoning</h4>
      <p>${escHtml(r.reasoning || '-')}</p>
    </div>

    <div class="report-section">
      <h4>Recommended specialist</h4>
      <p style="font-weight:500">${escHtml(r.recommended_specialist || '-')}</p>
    </div>

    <div class="report-section" id="doctorSuggestions">
      <h4>Relevant doctors</h4>
      <p class="text-muted">Loading matched doctors...</p>
    </div>

    <div class="report-section">
      <h4>Guidance</h4>
      <p>${escHtml(r.guidance || '-')}</p>
    </div>

    <div style="font-size:11px;color:var(--ink-muted);margin-top:16px">
      Generated: ${new Date(r.generated_at || Date.now()).toLocaleString()}<br>
      <em>This is AI-assisted triage only. Always consult a qualified medical professional.</em>
    </div>

    <div style="margin-top:20px">
      <a href="${doctorLinkForReport(r)}" class="btn-primary" style="display:block;text-align:center;font-size:14px;padding:12px">Find a ${escHtml(r.recommended_specialist || 'Doctor')} -></a>
    </div>
  `;
}

async function loadDoctorSuggestions(report) {
  const el = document.getElementById('doctorSuggestions');
  if (!el) return;
  const params = new URLSearchParams();
  if (report?.recommended_specialist) params.set('specialization', report.recommended_specialist);
  if (primarySymptom) params.set('symptom', primarySymptom);
  if (report?.possible_condition) params.set('possible_condition', report.possible_condition);
  if (report?.urgency) params.set('urgency', report.urgency);
  params.set('report_text', reportContextText(report).slice(0, 700));
  params.set('limit', '3');

  try {
    const res = await fetch(`${AI_BASE}/doctor-recommendation?${params.toString()}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Could not load doctors.');
    const doctors = data.doctors || [];
    if (!doctors.length) {
      el.innerHTML = '<h4>Relevant doctors</h4><p class="text-muted">No doctor matches found yet.</p>';
      return;
    }
    el.innerHTML = '<h4>Relevant doctors</h4>' + doctors.map(d => `
      <div style="padding:10px 0;border-bottom:1px solid var(--border)">
        <div style="font-weight:500">${escHtml(d.doctor_name)}</div>
        <div class="text-muted">${escHtml(d.specialization)} | ${escHtml(d.location || 'Location not listed')}</div>
        ${d.match_reason ? `<div class="text-muted">${escHtml(d.match_reason)}</div>` : ''}
      </div>
    `).join('') + `<a href="${doctorLinkForReport(report)}" class="btn-book" style="margin-top:14px">View and book matched doctors</a>`;
  } catch {
    el.innerHTML = `<h4>Relevant doctors</h4><a href="${doctorLinkForReport(report)}" class="btn-book">View matched doctors</a>`;
  }
}

function openReport() { document.getElementById('reportPanel').classList.add('open'); }
function closeReport() { document.getElementById('reportPanel').classList.remove('open'); }

document.addEventListener('DOMContentLoaded', () => {
  const u = getUser();
  const el = document.getElementById('sidebarUserName');
  if (el) el.textContent = u ? u.first_name + ' ' + u.last_name : 'Guest';
  setSendDisabled(false);
});
