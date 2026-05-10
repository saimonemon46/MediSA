// MediAI - Reports JS
const PHP_BASE = "../../backend_php";

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
function escHtml(t) {
  return String(t ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
function fmtDate(d) {
  return new Date(d).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const DEMO_REPORTS = [
  {
    id: 1,
    possible_condition: "Viral Upper Respiratory Infection",
    urgency: "medium",
    recommended_specialist: "Medicine Specialist",
    reasoning:
      "Symptoms including fever, sore throat, and nasal congestion match viral URI patterns in the medical knowledge base.",
    guidance:
      "Rest, hydration, paracetamol for fever. Seek care if symptoms worsen after 5 days.",
    symptoms_listed: ["Fever 38.2 C", "Sore throat", "Runny nose", "Fatigue"],
    created_at: "2026-03-12T10:30:00",
  },
  {
    id: 2,
    possible_condition: "Migraine",
    urgency: "medium",
    recommended_specialist: "Neurologist",
    reasoning:
      "Unilateral throbbing headache with photophobia and nausea is a classic migraine pattern supported by the symptom knowledge base.",
    guidance:
      "Rest in a dark quiet room. Take prescribed migraine medication. Track triggers.",
    symptoms_listed: [
      "Severe headache",
      "Nausea",
      "Light sensitivity",
      "Throbbing sensation",
    ],
    created_at: "2026-03-05T14:20:00",
  },
  {
    id: 3,
    possible_condition: "Allergic Rhinitis",
    urgency: "low",
    recommended_specialist: "Medicine Specialist",
    reasoning:
      "Persistent sneezing, watery eyes, and nasal congestion without fever strongly suggests allergic rhinitis per the medical knowledge base.",
    guidance:
      "Antihistamines recommended. Identify and avoid allergen triggers.",
    symptoms_listed: [
      "Sneezing",
      "Watery eyes",
      "Nasal congestion",
      "Itchy nose",
    ],
    created_at: "2026-02-20T09:15:00",
  },
];

function urgencyClass(u) {
  return (
    { high: "badge-high", medium: "badge-medium", low: "badge-low" }[u] ||
    "badge-medium"
  );
}

function reportDoctorLink(r) {
  const params = new URLSearchParams();
  if (r.recommended_specialist)
    params.set("specialization", r.recommended_specialist);
  if (Array.isArray(r.symptoms_listed) && r.symptoms_listed.length)
    params.set("symptom", r.symptoms_listed.join(", "));
  if (r.possible_condition) params.set("condition", r.possible_condition);
  if (r.urgency) params.set("urgency", r.urgency);
  const reportText = [r.reasoning, r.guidance, r.explanation]
    .filter(Boolean)
    .join(" ")
    .slice(0, 700);
  if (reportText) params.set("report_text", reportText);
  return `doctors.html?${params.toString()}`;
}

function renderReportImage(r) {
  if (!r.image_path && !r.image_analysis) return "";

  const path = r.image_path || r.image_analysis?.image_path;
  const analysis = r.image_analysis;
  const url = path ? `${PHP_BASE}/${path}` : "";

  let analysisHtml = "";
  if (analysis) {
    analysisHtml = `
      <div style="margin-top:12px">
        <div style="font-weight:500">${escHtml(analysis.image_type || "Symptom image")}</div>
        <p style="margin:4px 0">${escHtml((analysis.visible_observations || []).join(" ") || analysis.possible_relevance || "Image was included as supportive context.")}</p>
        ${(analysis.red_flags || []).length ? `<p style="color:var(--red-danger);font-weight:500;margin:4px 0">Red flags: ${escHtml(analysis.red_flags.join(", "))}</p>` : ""}
        <p class="text-muted" style="font-size:12px;margin:4px 0">AI Confidence: ${escHtml(analysis.confidence || "low")}. Clinician review recommended.</p>
      </div>
    `;
  }

  return `
    <div class="report-section" style="margin-bottom:18px">
      <h4>Uploaded image review</h4>
      ${url ? `<img src="${escHtml(url)}" alt="Uploaded symptom image" style="max-width:100%;border-radius:12px;border:1px solid var(--border);display:block;margin-bottom:12px">` : ""}
      ${analysisHtml}
    </div>
  `;
}

function cacheReportAssessment(r) {
  sessionStorage.setItem(
    "mediai_last_assessment",
    JSON.stringify({
      source: "report",
      saved_at: new Date().toISOString(),
      report: r,
    }),
  );
}

function renderReportsList(reports) {
  const el = document.getElementById("reportsList");
  if (!reports.length) {
    el.innerHTML =
      '<div class="card"><p class="text-muted" style="text-align:center;padding:40px 0">No reports yet. <a href="symptom-chat.html" class="text-teal">Start a symptom check -></a></p></div>';
    return;
  }
  el.innerHTML = reports
    .map(
      (r) => `
    <div class="report-card mb-24" style="cursor:pointer" onclick="openReport(${r.id})">
      <div class="report-header">
        <h2>${escHtml(r.possible_condition)}</h2>
        <div class="report-date">${fmtDate(r.created_at)}</div>
        <div style="margin-top:10px"><span class="badge" style="background:rgba(255,255,255,0.2);color:#fff">${(r.urgency || "medium").toUpperCase()} URGENCY</span></div>
      </div>
      <div class="report-body">
        <div style="display:flex;gap:32px;flex-wrap:wrap">
          <div>
            <div class="text-muted" style="font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Recommended Specialist</div>
            <div style="font-weight:500">${escHtml(r.recommended_specialist)}</div>
          </div>
          <div>
            <div class="text-muted" style="font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">Symptoms Reported</div>
            <div>${(r.symptoms_listed || [])
              .slice(0, 3)
              .map((s) => escHtml(s))
              .join(", ")}</div>
          </div>
        </div>
        ${r.image_path ? `<div style="margin-top:16px"><img src="${escHtml(PHP_BASE + "/" + r.image_path)}" alt="Report image" style="max-width:100%;height:auto;border-radius:10px;border:1px solid var(--border)"></div>` : ""}
        <div style="margin-top:16px;font-size:13px;color:var(--ink-muted)">Click to view full report -></div>
      </div>
    </div>`,
    )
    .join("");
}

function openReport(id) {
  const r = (window._reports || DEMO_REPORTS).find((x) => x.id === id);
  if (!r) return;
  cacheReportAssessment(r);
  const symptoms = (r.symptoms_listed || [])
    .map((s) => `<li>${escHtml(s)}</li>`)
    .join("");
  document.getElementById("reportDetail").innerHTML = `
    <div class="report-header">
      <h2>${escHtml(r.possible_condition)}</h2>
      <div class="report-date">${fmtDate(r.created_at)}</div>
    </div>
    <div class="report-body">
      <div class="report-section">
        <h4>Urgency</h4>
        <span class="badge ${urgencyClass(r.urgency)}">${(r.urgency || "medium").toUpperCase()}</span>
      </div>
      <div class="report-section">
        <h4>Symptoms reported</h4>
        <ul class="symptoms-list">${symptoms}</ul>
      </div>
      <div class="report-section">
        <h4>AI reasoning (RAG-grounded)</h4>
        <p>${escHtml(r.reasoning)}</p>
      </div>
      ${renderReportImage(r)}
      <div class="report-section">
        <h4>Recommended specialist</h4>
        <p style="font-weight:500">${escHtml(r.recommended_specialist)}</p>
      </div>
      <div class="report-section">
        <h4>Guidance</h4>
        <p>${escHtml(r.guidance)}</p>
      </div>
      <div class="mt-16">
        <a href="${reportDoctorLink(r)}" class="btn-primary" style="display:inline-block;font-size:14px;padding:10px 20px">Find ${escHtml(r.recommended_specialist)} -></a>
      </div>
    </div>`;
  document.getElementById("reportModal").style.display = "block";
}

async function loadReports() {
  const u = getUser();
  try {
    const res = await fetch(
      PHP_BASE + "/api/reports.php?user_id=" + (u?.id || 1),
    );
    const data = await res.json();
    window._reports = data.reports;
    renderReportsList(data.reports || []);
  } catch {
    window._reports = DEMO_REPORTS;
    renderReportsList(DEMO_REPORTS);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const u = getUser();
  const el = document.getElementById("sidebarUserName");
  if (el) el.textContent = u ? u.first_name + " " + u.last_name : "Guest";
  loadReports();
  document
    .getElementById("reportModal")
    .addEventListener("click", function (e) {
      if (e.target === this) this.style.display = "none";
    });
});
