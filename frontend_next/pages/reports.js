import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { getUser, fmtDate, getDjangoBase } from '../lib/api';

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

  return (
    <Layout activePage="reports">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1>My Triage Reports</h1>
          <p>History of AI triage assessments and clinical guidance</p>
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
                <th>Specialist</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td>{fmtDate(r.created_at)}</td>
                  <td><strong>{r.possible_condition}</strong></td>
                  <td>
                    <span className={`badge badge-${r.urgency || 'medium'}`}>
                      {r.urgency || 'medium'}
                    </span>
                  </td>
                  <td>{r.recommended_specialist || 'General Practitioner'}</td>
                  <td>
                    <button
                      onClick={() => setSelectedReport(r)}
                      className="btn-ghost"
                      style={{ padding: '6px 14px', fontSize: '13px' }}
                    >
                      View Details
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
          <div className="modal-box" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '650px' }}>
            <div className="modal-header">
              <h3>{selectedReport.possible_condition}</h3>
              <button className="modal-close" onClick={() => setSelectedReport(null)}>✕</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                <span className={`badge badge-${selectedReport.urgency || 'medium'}`} style={{ textTransform: 'uppercase' }}>
                  Urgency: {selectedReport.urgency || 'medium'}
                </span>
                <span className="badge badge-low">
                  Specialist: {selectedReport.recommended_specialist || 'General Medicine'}
                </span>
                <span style={{ fontSize: '13px', color: 'var(--ink-muted)', marginLeft: 'auto' }}>
                  {fmtDate(selectedReport.created_at)}
                </span>
              </div>

              {selectedReport.symptoms_listed?.length > 0 && (
                <div className="report-section mb-16">
                  <h4>Reported Symptoms</h4>
                  <ul className="symptoms-list">
                    {selectedReport.symptoms_listed.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedReport.reasoning && (
                <div className="report-section mb-16">
                  <h4>Clinical Reasoning</h4>
                  <p>{selectedReport.reasoning}</p>
                </div>
              )}

              {selectedReport.guidance && (
                <div className="report-section mb-16">
                  <h4>Guidance & Recommended Actions</h4>
                  <p>{selectedReport.guidance}</p>
                </div>
              )}

              {selectedReport.explanation && (
                <div className="report-section mb-16">
                  <h4>Diagnostic Explanation</h4>
                  <p>{selectedReport.explanation}</p>
                </div>
              )}

              {(selectedReport.image_analysis || selectedReport.image_path) && (
                <div
                  className="report-section mb-16"
                  style={{
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    padding: '14px',
                    borderRadius: '10px',
                  }}
                >
                  <h4 style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '10px', color: 'var(--ink)' }}>
                    <span>📷</span> Attached Clinical Photo & Vision Findings
                  </h4>
                  <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                    {selectedReport.image_path && (
                      <img
                        src={selectedReport.image_path}
                        alt="Symptom photo"
                        style={{
                          width: '84px',
                          height: '84px',
                          borderRadius: '8px',
                          objectFit: 'cover',
                          border: '1px solid #cbd5e1',
                          boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
                          cursor: 'pointer',
                        }}
                        onClick={() => window.open(selectedReport.image_path, '_blank')}
                        title="Click to view full photo"
                      />
                    )}
                    <div style={{ fontSize: '13px', flex: 1, minWidth: '220px' }}>
                      {typeof selectedReport.image_analysis === 'object' && selectedReport.image_analysis ? (
                        <>
                          <div style={{ marginBottom: '6px' }}>
                            <strong>Type:</strong>{' '}
                            <span style={{ textTransform: 'capitalize' }}>
                              {selectedReport.image_analysis.image_type || 'Clinical lesion / finding'}
                            </span>
                            {selectedReport.image_analysis.confidence && (
                              <span style={{ color: 'var(--ink-muted)' }}> • Confidence: {selectedReport.image_analysis.confidence}</span>
                            )}
                          </div>
                          {selectedReport.image_analysis.visible_observations?.length > 0 && (
                            <div style={{ marginBottom: '6px' }}>
                              <strong style={{ color: '#334155' }}>Visual Observations:</strong>
                              <ul style={{ margin: '4px 0 0 16px', padding: 0, color: '#475569' }}>
                                {selectedReport.image_analysis.visible_observations.map((obs, i) => (
                                  <li key={i}>{obs}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {selectedReport.image_analysis.possible_relevance && (
                            <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic', marginTop: '6px' }}>
                              {selectedReport.image_analysis.possible_relevance}
                            </div>
                          )}
                          {selectedReport.image_analysis.red_flags?.length > 0 && (
                            <div style={{ marginTop: '8px', color: '#dc2626', fontWeight: 600, fontSize: '12px' }}>
                              🚨 Red Flags: {selectedReport.image_analysis.red_flags.join(', ')}
                            </div>
                          )}
                        </>
                      ) : (
                        <p style={{ margin: 0 }}>{String(selectedReport.image_analysis || 'Image received and archived.')}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Link
                href={`/doctors?condition=${encodeURIComponent(selectedReport.possible_condition)}&specialization=${encodeURIComponent(selectedReport.recommended_specialist || '')}`}
                className="btn-primary"
              >
                Find Recommended Doctors →
              </Link>
              <button className="btn-ghost" onClick={() => setSelectedReport(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
