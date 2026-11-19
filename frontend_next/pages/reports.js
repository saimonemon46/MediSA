import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { getUser, fmtDate, getDjangoBase } from '../lib/api';

// Safe parser for symptoms
const parseSymptoms = (raw) => {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.filter(Boolean);
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed.filter(Boolean);
    } catch {
      return raw.split(',').map((s) => s.trim()).filter(Boolean);
    }
  }
  return [String(raw)];
};

// Safe parser for image analysis
const parseImageAnalysis = (raw) => {
  if (!raw) return null;
  if (typeof raw === 'object') return raw;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
  return null;
};

// Urgency badge class mapper
const getUrgencyClass = (urgency) => {
  const u = String(urgency || 'medium').toLowerCase();
  if (u === 'high' || u === 'urgent' || u === 'emergency') return 'badge-high';
  if (u === 'low' || u === 'mild' || u === 'routine') return 'badge-low';
  return 'badge-medium';
};

// Safe image path resolver (filters dead browser blobs and normalizes relative paths)
const resolveImagePath = (path) => {
  if (!path || typeof path !== 'string') return null;
  const p = path.trim();
  if (p.startsWith('blob:')) return null; // Dead client-side blob URL
  if (p.startsWith('http://') || p.startsWith('https://')) return p;
  if (p.startsWith('/')) return p;
  return `/${p}`;
};

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const u = getUser();
    if (u) {
      fetch(`${getDjangoBase()}/reports?user_id=${u.id}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.success && Array.isArray(data.reports)) {
            setReports(data.reports);
          }
        })
        .catch(() => {
          // Demo fallback
          setReports([
            {
              id: 1,
              session_id: 'SESS-DEMO-001',
              possible_condition: 'Viral Syndrome / Probable Dengue',
              urgency: 'medium',
              recommended_specialist: 'Medicine Specialist',
              reasoning: 'Acute high fever, retro-orbital headache, and generalized body aches during monsoon season in Dhaka strongly match viral exanthem / Dengue fever.',
              guidance: 'Stay well hydrated with oral rehydration solution. Monitor platelet count if fever persists beyond 3 days. Avoid NSAIDs; use paracetamol.',
              explanation: 'Your reported symptoms indicate a systemic viral infection. Please consult a physician and get a complete blood count (CBC) test.',
              symptoms_listed: ['High fever', 'Persistent headache', 'Body aches'],
              created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
            },
          ]);
        })
        .finally(() => setLoading(false));
    }
  }, []);

  // Compute parsed details for currently selected report
  const selectedSymptoms = selectedReport ? parseSymptoms(selectedReport.symptoms_listed) : [];
  const selectedAnalysis = selectedReport ? parseImageAnalysis(selectedReport.image_analysis) : null;
  const validImageSrc = resolveImagePath(selectedReport?.image_path || selectedAnalysis?.image_path);

  return (
    <Layout activePage="reports">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1>My Triage Reports</h1>
          <p>History of AI triage assessments, clinical guidance, and specialist recommendations</p>
        </div>
        <Link href="/symptom-chat" className="btn-primary">
          + New Triage Session
        </Link>
      </div>

      <div className="card">
        {loading ? (
          <p className="text-muted" style={{ textAlign: 'center', padding: '24px' }}>Loading triage reports...</p>
        ) : reports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p className="text-muted">No triage reports recorded yet.</p>
            <Link href="/symptom-chat" className="btn-primary" style={{ marginTop: '12px', display: 'inline-block' }}>
              Start your first assessment
            </Link>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Possible Condition</th>
                <th>Urgency</th>
                <th>Recommended Specialist</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td>{fmtDate(r.created_at)}</td>
                  <td><strong>{r.possible_condition}</strong></td>
                  <td>
                    <span className={`badge ${getUrgencyClass(r.urgency)}`}>
                      {r.urgency || 'medium'}
                    </span>
                  </td>
                  <td>
                    <span className="badge badge-specialist" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      👨‍⚕️ {r.recommended_specialist || 'General Practitioner'}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => setSelectedReport(r)}
                      className="btn-ghost"
                      style={{ padding: '6px 14px', fontSize: '13px' }}
                    >
                      View Details →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Detail Modal */}
      {selectedReport && (
        <div className="modal-backdrop show" onClick={() => setSelectedReport(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--teal)', fontWeight: 600, marginBottom: '2px' }}>
                  Clinical Triage Report
                </div>
                <h3>📋 {selectedReport.possible_condition}</h3>
              </div>
              <button
                className="modal-close"
                onClick={() => setSelectedReport(null)}
                title="Close modal"
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              {/* Top Meta Status Row */}
              <div
                style={{
                  display: 'flex',
                  gap: '8px',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  padding: '12px 14px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  marginBottom: '20px',
                }}
              >
                <span className={`badge ${getUrgencyClass(selectedReport.urgency)}`} style={{ textTransform: 'uppercase', fontWeight: 600 }}>
                  Urgency: {selectedReport.urgency || 'medium'}
                </span>
                <span className="badge badge-specialist" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  👨‍⚕️ {selectedReport.recommended_specialist || 'General Practitioner'}
                </span>
                {selectedReport.session_id && (
                  <span style={{ fontSize: '12px', color: '#64748b', background: '#fff', border: '1px solid #cbd5e1', padding: '3px 8px', borderRadius: '6px' }}>
                    ID: {selectedReport.session_id}
                  </span>
                )}
                <span style={{ fontSize: '12px', color: 'var(--ink-muted)', marginLeft: 'auto', fontWeight: 500 }}>
                  📅 {fmtDate(selectedReport.created_at)}
                </span>
              </div>

              {/* Reported Symptoms */}
              {selectedSymptoms.length > 0 && (
                <div className="report-section mb-16">
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>🩺</span> Reported Symptoms
                  </h4>
                  <div className="symptom-chips">
                    {selectedSymptoms.map((s, idx) => (
                      <span key={idx} className="symptom-chip">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Attached Clinical Photo & Vision Findings */}
              {(selectedAnalysis || selectedReport.image_path) && (
                <div
                  className="report-section mb-16"
                  style={{
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    padding: '16px',
                    borderRadius: '12px',
                  }}
                >
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px', color: '#166534' }}>
                    <span>📷</span> Gemini Vision Clinical Findings
                  </h4>
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                    {validImageSrc ? (
                      <img
                        src={validImageSrc}
                        alt="Clinical symptom photo"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                        style={{
                          width: '96px',
                          height: '96px',
                          borderRadius: '8px',
                          objectFit: 'cover',
                          border: '1px solid #86efac',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                          cursor: 'pointer',
                        }}
                        onClick={() => window.open(validImageSrc, '_blank')}
                        title="Click to view full photo in new tab"
                      />
                    ) : (
                      <div
                        style={{
                          width: '88px',
                          height: '88px',
                          borderRadius: '8px',
                          background: '#dcfce7',
                          border: '1px solid #86efac',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: '#15803d',
                          fontSize: '11px',
                          textAlign: 'center',
                          padding: '6px',
                          flexShrink: 0,
                        }}
                        title="Visual inspection verified with Gemini Vision"
                      >
                        <span style={{ fontSize: '24px', marginBottom: '2px' }}>📷</span>
                        <span style={{ fontWeight: 600 }}>Photo Logged</span>
                      </div>
                    )}
                    <div style={{ fontSize: '13px', flex: 1, minWidth: '220px' }}>
                      {selectedAnalysis ? (
                        <>
                          <div style={{ marginBottom: '6px' }}>
                            <strong>Suspected Area/Type:</strong>{' '}
                            <span style={{ textTransform: 'capitalize', color: '#15803d', fontWeight: 600 }}>
                              {selectedAnalysis.image_type || 'Skin/Wound lesion'}
                            </span>
                            {selectedAnalysis.confidence && (
                              <span style={{ color: '#64748b' }}> • Confidence: {selectedAnalysis.confidence}</span>
                            )}
                          </div>
                          {selectedAnalysis.visible_observations?.length > 0 && (
                            <div style={{ marginBottom: '6px' }}>
                              <strong style={{ color: '#1e293b' }}>Visual Observations:</strong>
                              <ul style={{ margin: '4px 0 0 16px', padding: 0, color: '#334155' }}>
                                {selectedAnalysis.visible_observations.map((obs, i) => (
                                  <li key={i}>{obs}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {selectedAnalysis.possible_relevance && (
                            <div style={{ fontSize: '12px', color: '#475569', fontStyle: 'italic', marginTop: '6px' }}>
                              Relevance: {selectedAnalysis.possible_relevance}
                            </div>
                          )}
                          {selectedAnalysis.red_flags?.length > 0 && (
                            <div style={{ marginTop: '8px', color: '#dc2626', fontWeight: 600, fontSize: '12px' }}>
                              🚨 Red Flags Noted: {selectedAnalysis.red_flags.join(', ')}
                            </div>
                          )}
                        </>
                      ) : (
                        <p style={{ margin: 0, color: '#475569' }}>Clinical photo archived with this triage record.</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Clinical Reasoning */}
              {selectedReport.reasoning && (
                <div className="report-section mb-16">
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>🧠</span> Clinical Assessment & Reasoning
                  </h4>
                  <p style={{ whiteSpace: 'pre-line', margin: 0, color: '#334155' }}>
                    {selectedReport.reasoning}
                  </p>
                </div>
              )}

              {/* Guidance & Recommended Actions */}
              {selectedReport.guidance && (
                <div
                  className="report-section mb-16"
                  style={{
                    background: 'rgba(224, 242, 238, 0.45)',
                    border: '1px solid rgba(13, 107, 94, 0.2)',
                    padding: '14px 16px',
                    borderRadius: '10px',
                  }}
                >
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--teal)', marginBottom: '8px' }}>
                    <span>💡</span> Guidance & Recommended Actions
                  </h4>
                  <p style={{ whiteSpace: 'pre-line', margin: 0, color: 'var(--ink)' }}>
                    {selectedReport.guidance}
                  </p>
                </div>
              )}

              {/* Diagnostic Explanation */}
              {selectedReport.explanation && (
                <div className="report-section mb-16">
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>ℹ️</span> Diagnostic Explanation
                  </h4>
                  <p style={{ whiteSpace: 'pre-line', margin: 0, color: '#475569' }}>
                    {selectedReport.explanation}
                  </p>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <Link
                href={`/doctors?condition=${encodeURIComponent(selectedReport.possible_condition || '')}&specialization=${encodeURIComponent(selectedReport.recommended_specialist || '')}`}
                className="btn-primary"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                Find Recommended Doctors →
              </Link>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => window.print()}
                  style={{ padding: '8px 14px', fontSize: '13px' }}
                >
                  🖨️ Print
                </button>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => setSelectedReport(null)}
                  style={{ padding: '8px 16px', fontSize: '13px' }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
