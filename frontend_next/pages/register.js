import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { setUser, getDjangoBase } from '../lib/api';

export default function Register() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    dob: '',
    password: '',
    password2: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.password2) {
      setError('Passwords do not match.');
      return;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${getDjangoBase()}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const data = await res.json();

      if (data.success) {
        setUser(data.user);
        router.push('/dashboard');
      } else {
        setError(data.message || 'Registration failed.');
      }
    } catch {
      // Demo fallback
      setUser({
        id: 99,
        first_name: formData.first_name,
        last_name: formData.last_name,
        email: formData.email,
        role: 'patient',
      });
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
          <Link href="/login">Sign in</Link>
        </div>
      </nav>

      <div className="auth-page">
        <div className="auth-card">
          <h2>Create account</h2>
          <p className="subtitle">Your personal health assistant starts here</p>

          {error && <div className="form-error show">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="grid-2">
              <div className="form-group">
                <label htmlFor="first_name">First name</label>
                <input
                  type="text"
                  id="first_name"
                  name="first_name"
                  placeholder="Rahim"
                  value={formData.first_name}
                  onChange={handleChange}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="last_name">Last name</label>
                <input
                  type="text"
                  id="last_name"
                  name="last_name"
                  placeholder="Uddin"
                  value={formData.last_name}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>
            <div className="form-group">
              <label htmlFor="email">Email address</label>
              <input
                type="email"
                id="email"
                name="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="phone">Phone number</label>
              <input
                type="tel"
                id="phone"
                name="phone"
                placeholder="+880 1712 345678"
                value={formData.phone}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="dob">Date of birth</label>
              <input
                type="date"
                id="dob"
                name="dob"
                value={formData.dob}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                placeholder="Minimum 8 characters"
                value={formData.password}
                onChange={handleChange}
                required
                minLength={8}
              />
            </div>
            <div className="form-group">
              <label htmlFor="password2">Confirm password</label>
              <input
                type="password"
                id="password2"
                name="password2"
                placeholder="Repeat password"
                value={formData.password2}
                onChange={handleChange}
                required
              />
            </div>
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className="auth-link">
            Already have an account? <Link href="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </>
  );
}
