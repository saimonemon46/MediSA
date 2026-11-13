import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <>
      <nav className="navbar">
        <div className="nav-brand">
          Medi<span>SA</span>
        </div>
        <div className="nav-links">
          <Link href="/login">Sign In</Link>
          <Link href="/register" className="btn-nav">
            Get Started
          </Link>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-badge">AI-Powered Medical Triage & Federated RAG</div>
        <h1>
          Your intelligent
          <br />
          <em>health companion</em>
        </h1>
        <p className="hero-sub">
          Describe your symptoms, receive AI-guided triage analysis backed by a
          structured medical knowledge base and Bangladeshi hospital partitions — not guesswork.
        </p>
        <div className="hero-actions">
          <Link href="/register" className="btn-primary">
            Start Health Check
          </Link>
          <Link href="/login" className="btn-ghost">
            Sign in to Dashboard
          </Link>
          <Link href="/research-evaluation" className="btn-ghost" style={{ borderColor: 'var(--teal)' }}>
            Research Evaluation (FRAG)
          </Link>
        </div>
        <div className="hero-stats">
          <div className="stat">
            <span>FRAG</span>
            <small>Federated hospital retrieval</small>
          </div>
          <div className="stat">
            <span>Next + Django + FastAPI</span>
            <small>Modern 3-tier architecture</small>
          </div>
          <div className="stat">
            <span>LangGraph</span>
            <small>Multi-step clinical reasoning</small>
          </div>
        </div>
      </section>

      <section className="features">
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">◎</div>
            <h3>Symptom Triage</h3>
            <p>
              AI conducts structured follow-ups, tracks patient state with memory,
              and generates a differential diagnostic report.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⬡</div>
            <h3>Doctor Finder</h3>
            <p>
              Matches patients to verified Bangladeshi specialists and hospital chambers
              based on clinical findings, location, and availability.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">◈</div>
            <h3>Prescription OCR</h3>
            <p>
              Upload prescriptions or lab reports. AI extracts medications, dosages,
              frequencies, and creates active reminder schedules.
            </p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">◉</div>
            <h3>Visual Symptom Review</h3>
            <p>
              Supportive multi-modal vision analysis for skin concerns, rashes, wounds,
              and cuts integrated directly into triage reasoning.
            </p>
          </div>
        </div>
      </section>

      <section className="how-it-works">
        <h2>How it works</h2>
        <div className="steps">
          <div className="step">
            <span className="step-num">01</span>
            <h4>Describe symptoms</h4>
            <p>Type what you are experiencing in plain language or attach a photo.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <span className="step-num">02</span>
            <h4>Clinical AI follow-up</h4>
            <p>LangGraph asks targeted questions without repetition.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <span className="step-num">03</span>
            <h4>Diagnostic report</h4>
            <p>Ranked conditions, urgency level, and clinical guidance.</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <span className="step-num">04</span>
            <h4>Specialist booking</h4>
            <p>Direct appointment scheduling with matched medical doctors.</p>
          </div>
        </div>
      </section>

      <footer style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--ink-muted)', fontSize: '14px', borderTop: '1px solid var(--border)' }}>
        MediSA Healthcare Assistant Platform · Powered by Next.js, Django & FastAPI
      </footer>
    </>
  );
}
