import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { getUser, fmtDate, getDjangoBase } from '../lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState({
    sessions: 0,
    reports: 0,
    medications: 0,
    appointments: 0,
    recent_reports: [],
  });
  const [user, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const u = getUser();
    if (u) {
      setCurrentUser(u);
      fetch(`${getDjangoBase()}/dashboard?user_id=${u.id}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.success) {
            setStats(data);
          }
        })
        .catch(() => {
          // Demo fallback data
          setStats({
            sessions: 2,
            reports: 1,
            medications: 2,
            appointments: 1,
            recent_reports: [
              {
                id: 1,
                created_at: new Date().toISOString(),
                possible_condition: 'Viral Syndrome / Probable Dengue',
                urgency: 'medium',
              },
            ],
          });
        })
        .finally(() => setLoading(false));
    }
  }, []);

  return (
    <Layout activePage="dashboard">
      <div className="page-header">
        <h1>
          Good day, <span>{user?.first_name || 'there'}</span>
        </h1>
        <p>Here's your comprehensive healthcare summary</p>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-label">Triage Sessions</div>
          <div className="stat-value">{loading ? '–' : stats.sessions}</div>
          <div className="stat-desc">Total assessments</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Reports</div>
          <div className="stat-value">{loading ? '–' : stats.reports}</div>
          <div className="stat-desc">Generated this month</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Medications</div>
          <div className="stat-value">{loading ? '–' : stats.medications}</div>
          <div className="stat-desc">Active reminders</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Appointments</div>
          <div className="stat-value">{loading ? '–' : stats.appointments}</div>
          <div className="stat-desc">Upcoming visits</div>
        </div>
      </div>

      <div className="alert alert-info mb-24" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <span style={{ marginRight: '8px', fontWeight: 'bold' }}>◎</span>
          <span>Start a new AI symptom check backed by medical retrieval & multi-turn clinical reasoning.</span>
        </div>
        <Link href="/symptom-chat" className="btn-primary" style={{ padding: '8px 16px', fontSize: '14px' }}>
          Start Triage Now
        </Link>
      </div>

      <div className="grid-2">
        {/* Recent Reports */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div className="card-title" style={{ margin: 0 }}>Recent Triage Reports</div>
            <Link href="/reports" style={{ fontSize: '13px', color: 'var(--teal)' }}>
              View all →
            </Link>
          </div>
          <div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Condition</th>
                  <th>Urgency</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_reports?.length > 0 ? (
                  stats.recent_reports.map((r, i) => (
                    <tr key={i}>
                      <td>{fmtDate(r.created_at)}</td>
                      <td><strong>{r.possible_condition}</strong></td>
                      <td>
                        <span className={`badge badge-${r.urgency || 'medium'}`}>
                          {r.urgency || 'medium'}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="3" className="text-muted" style={{ padding: '20px', textAlign: 'center' }}>
                      No recent triage reports found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Actions & Reminders */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <div className="card-title">Quick Actions</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px' }}>
              <Link href="/symptom-chat" className="btn-ghost" style={{ textAlign: 'center', padding: '12px 8px' }}>
                ◎ AI Triage
              </Link>
              <Link href="/documents" className="btn-ghost" style={{ textAlign: 'center', padding: '12px 8px' }}>
                ⬡ Prescription OCR
              </Link>
              <Link href="/doctors" className="btn-ghost" style={{ textAlign: 'center', padding: '12px 8px' }}>
                ⊕ Find Doctors
              </Link>
              <Link href="/research-evaluation" className="btn-ghost" style={{ textAlign: 'center', padding: '12px 8px' }}>
                ◫ FRAG Benchmark
              </Link>
            </div>
          </div>

          <div className="card">
            <div className="card-title">Active Medication Reminders</div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <span className="med-pill">◇ Paracetamol 500mg · Three times daily</span>
              <span className="med-pill">◇ Oral Rehydration Salts (ORS) · As needed</span>
            </div>
            <div style={{ marginTop: '16px' }}>
              <Link href="/medications" style={{ fontSize: '13px', color: 'var(--teal)' }}>
                Manage medication schedule →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
