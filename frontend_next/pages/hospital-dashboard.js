import React, { useState } from 'react';
import Link from 'next/link';

export default function HospitalDashboard() {
  const [filter, setFilter] = useState('all');

  const intakePatients = [
    {
      id: 1,
      ticket: 'T-101',
      name: 'Tanvir Hossain',
      age: 42,
      gender: 'Male',
      urgency: 'high',
      condition: 'Acute Dyspnea & Chest Discomfort',
      symptoms: 'Sudden onset shortness of breath, left chest pressure, sweating.',
      arrivalTime: '10 mins ago',
      assignedDoctor: 'Dr. Rahim Ahmed (Cardiologist)',
    },
    {
      id: 2,
      ticket: 'T-102',
      name: 'Nusrat Jahan',
      age: 28,
      gender: 'Female',
      urgency: 'medium',
      condition: 'Probable Dengue / Acute Febrile Illness',
      symptoms: 'High fever for 3 days, severe retro-orbital headache, generalized rash.',
      arrivalTime: '25 mins ago',
      assignedDoctor: 'Dr. Nasrin Islam (Medicine Specialist)',
    },
    {
      id: 3,
      ticket: 'T-103',
      name: 'Mohammad Faruk',
      age: 61,
      gender: 'Male',
      urgency: 'medium',
      condition: 'Acute Gastroenteritis & Dehydration',
      symptoms: 'Vomiting, diarrhea for 24h, mild hypotension.',
      arrivalTime: '40 mins ago',
      assignedDoctor: 'Dr. Tariq Rahman (Gastroenterologist)',
    },
    {
      id: 4,
      ticket: 'T-104',
      name: 'Rupom Roy',
      age: 8,
      gender: 'Male',
      urgency: 'low',
      condition: 'Pediatric Allergic Rhinitis & Cough',
      symptoms: 'Nocturnal dry cough, sneezing, clear nasal discharge.',
      arrivalTime: '1 hour ago',
      assignedDoctor: 'Dr. Fatema Begum (Pediatrician)',
    },
    {
      id: 5,
      ticket: 'T-105',
      name: 'Shamima Akter',
      age: 34,
      gender: 'Female',
      urgency: 'low',
      condition: 'Contact Dermatitis (Forearm)',
      symptoms: 'Pruritic erythematous papules following topical detergent exposure.',
      arrivalTime: '1.5 hours ago',
      assignedDoctor: 'Dr. Arif Siddiqui (Dermatologist)',
    },
  ];

  const filteredPatients = intakePatients.filter((p) => {
    if (filter === 'all') return true;
    return p.urgency === filter;
  });

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Link href="/dashboard" style={{ textDecoration: 'none', color: 'inherit' }}>
            Medi<span>SA</span>
          </Link>
        </div>
        <nav className="sidebar-nav">
          <Link href="/hospital-dashboard" className="active">
            <span className="nav-icon">◈</span> Intake Queue
          </Link>
          <Link href="/dashboard">
            <span className="nav-icon">◉</span> Patient Portal
          </Link>
          <Link href="/reports">
            <span className="nav-icon">◉</span> Triage Reports
          </Link>
          <Link href="/doctors">
            <span className="nav-icon">⊕</span> Doctors
          </Link>
          <Link href="/research-evaluation">
            <span className="nav-icon">◫</span> Research Evaluation
          </Link>
        </nav>
        <div className="sidebar-user">
          <strong>Hospital Admin</strong>
          <Link href="/">Back to home</Link>
        </div>
      </aside>

      <main className="main-content">
        <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1>Hospital Emergency & Outpatient Intake Queue</h1>
            <p>Real-time AI-prioritized patient intake stream</p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => setFilter('all')}
              className={`btn-ghost ${filter === 'all' ? 'active' : ''}`}
              style={{ background: filter === 'all' ? 'var(--teal-light)' : 'transparent', fontWeight: 600 }}
            >
              All ({intakePatients.length})
            </button>
            <button
              onClick={() => setFilter('high')}
              className="btn-ghost"
              style={{ color: 'var(--red-urgent)', background: filter === 'high' ? 'var(--red-light)' : 'transparent', fontWeight: 600 }}
            >
              High Priority (1)
            </button>
            <button
              onClick={() => setFilter('medium')}
              className="btn-ghost"
              style={{ color: 'var(--amber)', background: filter === 'medium' ? 'var(--amber-light)' : 'transparent', fontWeight: 600 }}
            >
              Medium Priority (2)
            </button>
            <button
              onClick={() => setFilter('low')}
              className="btn-ghost"
              style={{ color: 'var(--green-safe)', background: filter === 'low' ? 'var(--green-light)' : 'transparent', fontWeight: 600 }}
            >
              Low Priority (2)
            </button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-label">Active Queue</div>
            <div className="stat-value">{intakePatients.length}</div>
            <div className="stat-desc">Waiting in triage</div>
          </div>
          <div className="stat-card">
            <div className="stat-label" style={{ color: 'var(--red-urgent)' }}>High / Urgent</div>
            <div className="stat-value" style={{ color: 'var(--red-urgent)' }}>1</div>
            <div className="stat-desc">Immediate physician review</div>
          </div>
          <div className="stat-card">
            <div className="stat-label" style={{ color: 'var(--amber)' }}>Medium Urgency</div>
            <div className="stat-value" style={{ color: 'var(--amber)' }}>2</div>
            <div className="stat-desc">Standard consult required</div>
          </div>
          <div className="stat-card">
            <div className="stat-label" style={{ color: 'var(--green-safe)' }}>Low Urgency</div>
            <div className="stat-value" style={{ color: 'var(--green-safe)' }}>2</div>
            <div className="stat-desc">Non-acute / outpatient</div>
          </div>
        </div>

        {/* Patient Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredPatients.map((p) => (
            <div
              key={p.id}
              className="card"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '20px',
                borderLeft: `5px solid ${p.urgency === 'high' ? 'var(--red-urgent)' : p.urgency === 'medium' ? 'var(--amber)' : 'var(--green-safe)'}`,
                padding: '20px',
              }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  background: 'var(--teal-light)',
                  color: 'var(--teal)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 600,
                  fontSize: '14px',
                  flexShrink: 0,
                }}
              >
                {p.ticket}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                  <h3 style={{ margin: 0, fontSize: '17px' }}>{p.name}</h3>
                  <span style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>
                    {p.gender}, {p.age} yrs
                  </span>
                  <span className={`badge badge-${p.urgency}`} style={{ textTransform: 'uppercase', fontSize: '11px' }}>
                    {p.urgency} Urgency
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--ink-muted)', marginLeft: 'auto' }}>
                    🕒 Arrived {p.arrivalTime}
                  </span>
                </div>

                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink)', marginBottom: '4px' }}>
                  Preliminary AI Finding: {p.condition}
                </div>

                <p style={{ fontSize: '13px', color: 'var(--ink-muted)', margin: '0 0 6px 0' }}>
                  {p.symptoms}
                </p>

                <div style={{ fontSize: '12px', color: 'var(--teal)' }}>
                  Assigned Consultant: <strong>{p.assignedDoctor}</strong>
                </div>
              </div>

              <div>
                <button className="btn-primary" style={{ padding: '8px 16px', fontSize: '13px', whiteSpace: 'nowrap' }}>
                  Examine Patient →
                </button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
