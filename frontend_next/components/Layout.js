import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { getUser, logout } from '../lib/api';

export default function Layout({ children, activePage = 'dashboard' }) {
  const router = useRouter();
  const [user, setCurrentUser] = useState(null);

  useEffect(() => {
    const u = getUser();
    if (!u) {
      router.push('/login');
    } else {
      setCurrentUser(u);
    }
  }, [router]);

  return (
    <div className="dashboard-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Link href="/dashboard" style={{ textDecoration: 'none', color: 'inherit' }}>
            Medi<span>SA</span>
          </Link>
        </div>
        <nav className="sidebar-nav">
          <Link href="/dashboard" className={activePage === 'dashboard' ? 'active' : ''}>
            <span className="nav-icon">◈</span> Dashboard
          </Link>
          <Link href="/symptom-chat" className={activePage === 'symptom-chat' ? 'active' : ''}>
            <span className="nav-icon">◎</span> Symptom Check
          </Link>
          <Link href="/reports" className={activePage === 'reports' ? 'active' : ''}>
            <span className="nav-icon">◉</span> My Reports
          </Link>
          <Link href="/documents" className={activePage === 'documents' ? 'active' : ''}>
            <span className="nav-icon">⬡</span> Documents
          </Link>
          <Link href="/medications" className={activePage === 'medications' ? 'active' : ''}>
            <span className="nav-icon">◇</span> Medications
          </Link>
          <Link href="/doctors" className={activePage === 'doctors' ? 'active' : ''}>
            <span className="nav-icon">⊕</span> Find Doctors
          </Link>
          <Link href="/appointments" className={activePage === 'appointments' ? 'active' : ''}>
            <span className="nav-icon">▷</span> Appointments
          </Link>
          <Link href="/research-evaluation" className={activePage === 'research-evaluation' ? 'active' : ''}>
            <span className="nav-icon">◫</span> Research Evaluation
          </Link>
        </nav>
        <div className="sidebar-user">
          <strong id="sidebarUserName">
            {user ? `${user.first_name} ${user.last_name}` : 'Loading...'}
          </strong>
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              logout();
            }}
          >
            Sign out
          </a>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">{children}</main>
    </div>
  );
}
