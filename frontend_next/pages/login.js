import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { setUser, getDjangoBase } from '../lib/api';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${getDjangoBase()}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();

      if (data.success) {
        setUser(data.user);
        router.push('/dashboard');
      } else {
        setError(data.message || 'Invalid email or password.');
      }
    } catch {
      // Demo fallback
      setUser({ id: 1, first_name: 'John', last_name: 'Doe', email: email || 'john.doe@example.com', role: 'patient' });
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <nav className="navbar">
        <Link href="/" className="nav-brand" style={{ textDecoration: 'none' }}>
          Medi<span>SA</span>
        </Link>
        <div className="nav-links">
          <Link href="/register">Create account</Link>
        </div>
      </nav>

      <div className="auth-page">
        <div className="auth-card">
          <h2>Welcome back</h2>
          <p className="subtitle">Sign in to your health dashboard</p>

          {error && <div className="form-error show">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <input
                type="email"
                id="email"
                name="email"
                placeholder="john.doe@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                placeholder="password123"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div style={{ marginTop: '16px', padding: '12px', background: 'var(--teal-light)', borderRadius: '8px', fontSize: '13px', color: 'var(--ink)' }}>
            <strong>Demo Credentials:</strong><br />
            Email: <code>john.doe@example.com</code><br />
            Password: <code>password123</code>
          </div>

          <p className="auth-link">
            Don't have an account? <Link href="/register">Sign up free</Link>
          </p>
        </div>
      </div>
    </>
  );
}
