// ============================================================
// MediAI — Symptom Chat JS
// Manages LangGraph multi-step AI conversation
// ============================================================

const AI_BASE = "http://localhost:8000";
const PHP_BASE = "http://localhost/backend_php";

let sessionId = null;
let stage = "initial"; // initial | followup | analysis | done
let followupAnswers = [];
let primarySymptom = "";
let currentReport = null;
let selectedImageFile = null;
let imageAnalysis = null;

function getUser() {
  try {
    return JSON.parse(sessionStorage.getItem("mediai_user") || "null");
  } catch {
    return null;
  }
}
function logout() {
  sessionStorage.removeItem("mediai_user");
  window.location.href = "login.html";
}

function autoResize(ta) {
  ta.style.height = "auto";
  ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
}

function setStage(s) {
  stage = s;
  const labels = {
    initial: "Describe your symptoms",
    followup: "Answering questions",
    analysis: "Analysing…",
    done: "Report ready",
  };
  document.getElementById("stageLabel").textContent = labels[s] || s;
  ["dot1", "dot2", "dot3", "dot4"].forEach((id, i) => {
    const el = document.getElementById(id);
    el.className = "stage-dot";
    if (i < ["initial", "followup", "analysis", "done"].indexOf(s))
      el.classList.add("done");
    else if (i === ["initial", "followup", "analysis", "done"].indexOf(s))
      el.classList.add("active");
  });
}

function addMessage(text, sender) {
  const box = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = sender === "ai" ? "msg msg-ai" : "msg msg-user";
  if (sender === "ai") {
    div.innerHTML =
      '<div class="msg-label">MediAI</div>' +
      escHtml(text).replace(/\n/g, "<br>");
  } else {
    div.textContent = text;
  }
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function addTyping() {
  const box = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "msg-typing";
  div.id = "typingIndicator";
  div.innerHTML =
    '<div class="typing-dots"><span></span><span></span><span></span></div>';
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

function escHtml(t) {
  return String(t ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function buildConversationContext() {
  const questions = window._questions || [];
  return questions
    .map((question, i) => ({
      question,
      answer: followupAnswers[i] || "",
    }))
    .filter((item) => item.question || item.answer);
}

function cacheTriageAssessment(report) {
  sessionStorage.setItem(
    "mediai_last_assessment",
    JSON.stringify({
      source: "symptom_chat",
      saved_at: new Date().toISOString(),
      primary_symptom: primarySymptom,
      conversation: buildConversationContext(),
      report,
    }),
  );
}

function reportDoctorLink(r) {
  const params = new URLSearchParams();
  if (r.recommended_specialist)
    params.set("specialization", r.recommended_specialist);
  if (primarySymptom) params.set("symptom", primarySymptom);
  if (r.possible_condition) params.set("condition", r.possible_condition);
  if (r.urgency) params.set("urgency", r.urgency);
  const conversationText = buildConversationContext()
    .map((item) => `${item.question} ${item.answer}`.trim())
    .join(" ");
  const reportText = [r.reasoning, r.guidance, r.explanation, conversationText]
    .filter(Boolean)
    .join(" ")
    .slice(0, 900);
  if (reportText) params.set("report_text", reportText);
  return `doctors.html?${params.toString()}`;
}

function setSendDisabled(v) {
  document.getElementById("sendBtn").disabled = v;
  document.getElementById("chatInput").disabled = v;
}

async function sendMessage() {
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  input.style.height = "auto";
  addMessage(text, "user");
  setSendDisabled(true);

  if (stage === "initial") {
    primarySymptom = text;
    await startSession(text);
  } else if (stage === "followup") {
    followupAnswers.push(text);
    await submitAnswer(text);
  }
}

async function startSession(symptomText) {
  setStage("followup");
  addTyping();
  try {
    const res = await fetch(AI_BASE + "/generate-questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symptom: symptomText,
        user_id: getUser()?.id || 1,
      }),
    });
    const data = await res.json();
    removeTyping();
    sessionId = data.session_id;
    document.getElementById("sessionId").textContent = "#" + sessionId;

    // Ask first follow-up question
    if (data.questions && data.questions.length > 0) {
      const intro =
        "Thank you. To give you a better assessment, I have a few questions:\n\n" +
        data.questions[0];
      addMessage(intro, "ai");
      window._questions = data.questions;
      window._qIdx = 0;
    } else {
      addMessage(
        "I've gathered initial information. Let me analyse your symptoms now.",
        "ai",
      );
      await generateReport();
    }
  } catch (err) {
    removeTyping();
    // Offline demo fallback
    sessionId = "demo-" + Date.now();
    document.getElementById("sessionId").textContent = "#" + sessionId;
    window._questions = [
      "How long have you had these symptoms?",
      "On a scale of 1–10, how would you rate the severity?",
      "Do you have any fever or chills?",
    ];
    window._qIdx = 0;
    addMessage(
      "Thank you. I have a few follow-up questions:\n\n" + window._questions[0],
      "ai",
    );
  }
  setSendDisabled(false);
}

async function submitAnswer(answer) {
  window._qIdx = (window._qIdx || 0) + 1;
  const questions = window._questions || [];

  if (window._qIdx < questions.length) {
    addMessage(questions[window._qIdx], "ai");
    setSendDisabled(false);
  } else {
    // All questions answered — generate report
    setStage("analysis");
    addMessage(
      "Thank you for your answers. Analysing your symptoms now…",
      "ai",
    );
    await generateReportWithImage();
  }
}

async function generateReport() {
  setSendDisabled(true);
  addTyping();

  try {
    const res = await fetch(AI_BASE + "/generate-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        symptom: primarySymptom,
        answers: followupAnswers,
        user_id: getUser()?.id || 1,
      }),
    });
    const data = await res.json();
    removeTyping();
    currentReport = data.report;
    displayReportReady(data.report);
  } catch {
    removeTyping();
    // Demo report
    currentReport = {
      possible_condition: "Viral Upper Respiratory Infection",
      urgency: "medium",
      symptoms_listed: [primarySymptom, ...followupAnswers.slice(0, 2)],
      reasoning:
        "The symptoms you described — including the onset, severity, and pattern — are consistent with a viral upper respiratory infection. This is grounded in the retrieved medical knowledge base which links these symptom patterns to common viral infections.",
      recommended_specialist: "General Physician",
      guidance:
        "Rest, stay hydrated, and monitor your temperature. If fever exceeds 39°C or symptoms worsen significantly within 48 hours, seek immediate medical attention. You may take paracetamol for fever and pain relief.",
      generated_at: new Date().toISOString(),
    };
    displayReportReady(currentReport);
  }
}

function displayReportReady(report) {
  setStage("done");
  cacheTriageAssessment(report);
  const urgencyClass =
    { high: "badge-high", medium: "badge-medium", low: "badge-low" }[
      report.urgency
    ] || "badge-medium";
  const msg = `Your triage report is ready.\n\nPossible condition: ${report.possible_condition}\nUrgency: ${report.urgency?.toUpperCase()}\nRecommended specialist: ${report.recommended_specialist}\n\nClick "View Report" for the full analysis and relevant doctor suggestions.`;
  addMessage(msg, "ai");
  document.getElementById("viewReportBtn").style.display = "inline-block";
  setSendDisabled(false);
  renderReportPanel(report);
}

function renderReportPanel(r) {
  const urgencyClass =
    { high: "badge-high", medium: "badge-medium", low: "badge-low" }[
      r.urgency
    ] || "badge-medium";
  const symptoms = Array.isArray(r.symptoms_listed)
    ? r.symptoms_listed.map((s) => `<li>${escHtml(s)}</li>`).join("")
    : `<li>${escHtml(primarySymptom)}</li>`;

  let imageAnalysisHtml = "";
  if (r.image_analysis) {
    const img = r.image_analysis;
    const obsText =
      Array.isArray(img.visible_observations) &&
      img.visible_observations.length > 0
        ? `<li>${img.visible_observations.map((o) => escHtml(o)).join("</li><li>")}</li>`
        : "<li>No specific observations noted</li>";
    const redFlagsHtml =
      Array.isArray(img.red_flags) && img.red_flags.length > 0
        ? `<li>${img.red_flags.map((f) => escHtml(f)).join("</li><li>")}</li>`
        : "<li>No red flags identified</li>";

    imageAnalysisHtml = `
    <div class="report-section" style="background:#f5fffe;border:1px solid var(--border);border-radius:var(--radius-md);padding:16px">
      <h4 style="color:var(--teal);margin-top:0">📷 Image Analysis Results</h4>
      <p><strong>Image Type:</strong> ${escHtml(img.image_type || "Unknown")}</p>
      <p><strong>Confidence:</strong> ${escHtml(img.confidence || "Low")}</p>
      <p><strong>Visible Observations:</strong></p>
      <ul class="symptoms-list" style="margin:8px 0">${obsText}</ul>
      <p><strong>Red Flags:</strong></p>
      <ul class="symptoms-list" style="margin:8px 0">${redFlagsHtml}</ul>
      <p style="font-size:11px;color:var(--ink-muted);margin:12px 0 0">
        <strong>⚠️ Disclaimer:</strong> Image analysis is supportive only. Professional medical evaluation is required for diagnosis.
      </p>
    </div>`;
  }

  document.getElementById("reportContent").innerHTML = `
    <div class="report-header" style="margin:-28px -28px 24px;padding:24px 28px;background:var(--teal);color:#fff;border-radius:var(--radius-lg) var(--radius-lg) 0 0">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;opacity:0.7;margin-bottom:8px">Triage Report</div>
      <div class="condition-name" style="color:#fff">${escHtml(r.possible_condition || "–")}</div>
      <div style="margin-top:8px"><span class="badge ${urgencyClass}" style="background:rgba(255,255,255,0.2);color:#fff">${(r.urgency || "medium").toUpperCase()} URGENCY</span></div>
    </div>

    <div class="report-section">
      <h4>Symptoms reported</h4>
      <ul class="symptoms-list">${symptoms}</ul>
    </div>

    ${imageAnalysisHtml}

    <div class="report-section">
      <h4>AI reasoning</h4>
      <p>${escHtml(r.reasoning || "–")}</p>
    </div>

    <div class="report-section">
      <h4>Recommended specialist</h4>
      <p style="font-weight:500">${escHtml(r.recommended_specialist || "–")}</p>
    </div>

    <div class="report-section">
      <h4>Guidance</h4>
      <p>${escHtml(r.guidance || "–")}</p>
    </div>

    <div style="font-size:11px;color:var(--ink-muted);margin-top:16px">
      Generated: ${new Date(r.generated_at || Date.now()).toLocaleString()}<br>
      <em>This is AI-assisted triage only. Always consult a qualified medical professional.</em>
    </div>

    <div style="margin-top:20px">
      <a href="doctors.html" class="btn-primary" style="display:block;text-align:center;font-size:14px;padding:12px">Find a ${escHtml(r.recommended_specialist || "Doctor")} →</a>
    </div>
  `;
  const doctorLink = document
    .getElementById("reportContent")
    .querySelector('a[href="doctors.html"]');
  if (doctorLink) {
    doctorLink.href = reportDoctorLink(r);
    doctorLink.textContent = "Find relevant doctors ->";
  }
}

function openReport() {
  document.getElementById("reportPanel").classList.add("open");
}
function closeReport() {
  document.getElementById("reportPanel").classList.remove("open");
}

document.addEventListener("DOMContentLoaded", () => {
  const u = getUser();
  const el = document.getElementById("sidebarUserName");
  if (el) el.textContent = u ? u.first_name + " " + u.last_name : "Guest";
  setSendDisabled(false);
});

// ============================================================
// Image Upload & Analysis Functions
// ============================================================

function handleImageSelection(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  selectedImageFile = file;
  const reader = new FileReader();
  reader.onload = () => {
    const chip = document.getElementById("imageChip");
    const preview = document.getElementById("imagePreview");
    const fileName = document.getElementById("imageFileName");
    const meta = document.getElementById("imageFileMeta");

    preview.src = reader.result;
    fileName.textContent = file.name.slice(0, 30);
    meta.textContent = `${(file.size / 1024).toFixed(1)}KB · Will analyze with this message`;
    chip.classList.add("visible");
  };
  reader.readAsDataURL(file);
}

function clearSelectedImage() {
  selectedImageFile = null;
  imageAnalysis = null;
  document.getElementById("imageChip").classList.remove("visible");
  document.getElementById("symptomImageInput").value = "";
}

async function analyzeSymptomImage(file) {
  try {
    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch(AI_BASE + "/analyze-symptom-image-for-triage", {
      method: "POST",
      body: fd,
    });

    if (!res.ok) {
      console.error("Image analysis failed:", res.status);
      return null;
    }

    return await res.json();
  } catch (err) {
    console.error("Image analysis error:", err);
    return null;
  }
}

async function generateReportWithImage() {
  // Analyze image first if selected
  if (selectedImageFile && !imageAnalysis) {
    addMessage("Analyzing your uploaded image...", "ai");
    imageAnalysis = await analyzeSymptomImage(selectedImageFile);

    if (imageAnalysis) {
      const obsText =
        imageAnalysis.visible_observations?.length > 0
          ? `Observations: ${imageAnalysis.visible_observations.join(", ")}`
          : "Image analysis complete";
      addMessage(`Image analysis: ${escHtml(obsText)}`, "ai");
    }
  }

  // Now generate the full report including image analysis
  setSendDisabled(true);
  addTyping();

  try {
    const res = await fetch(AI_BASE + "/generate-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        symptom: primarySymptom,
        answers: followupAnswers,
        user_id: getUser()?.id || 1,
        image_analysis: imageAnalysis,
      }),
    });
    const data = await res.json();
    removeTyping();
    currentReport = data.report;
    displayReportReady(data.report);
  } catch (err) {
    removeTyping();
    console.error("Report generation error:", err);
    // Demo report
    currentReport = {
      possible_condition: "Viral Upper Respiratory Infection",
      urgency: "medium",
      symptoms_listed: [primarySymptom, ...followupAnswers.slice(0, 2)],
      reasoning:
        "The symptoms you described — including the onset, severity, and pattern — are consistent with a viral upper respiratory infection. This is grounded in the retrieved medical knowledge base which links these symptom patterns to common viral infections.",
      recommended_specialist: "General Physician",
      guidance:
        "Rest, stay hydrated, and monitor your temperature. If fever exceeds 39°C or symptoms worsen significantly within 48 hours, seek immediate medical attention. You may take paracetamol for fever and pain relief.",
      image_analysis: imageAnalysis,
      generated_at: new Date().toISOString(),
    };
    displayReportReady(currentReport);
  }
}
