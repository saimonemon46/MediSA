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

              {selectedReport.image_analysis && (
                <div className="report-section mb-16" style={{ background: 'var(--teal-light)', padding: '12px', borderRadius: '8px' }}>
                  <h4>Skin / Image Analysis</h4>
                  <p>{typeof selectedReport.image_analysis === 'string' ? selectedReport.image_analysis : JSON.stringify(selectedReport.image_analysis)}</p>
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
