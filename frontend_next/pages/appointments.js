import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { getUser, fmtDate, fmtTime, getDjangoBase } from '../lib/api';

export default function Appointments() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadAppointments = () => {
    const u = getUser();
    if (!u) return;

    fetch(`${getDjangoBase()}/appointments?user_id=${u.id}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.success && Array.isArray(data.appointments)) {
          setAppointments(data.appointments);
        }
      })
      .catch(() => {
        // Demo fallback
        setAppointments([
          {
            id: 1,
            doctor_name: 'Dr. Nasrin Islam',
            specialization: 'Medicine Specialist',
            hospital: 'Square Hospital',
            location: 'Dhaka',
            contact: '+8801722222222',
            appointment_date: new Date(Date.now() + 2 * 86400000).toISOString(),
            status: 'confirmed',
            notes: 'Follow-up consultation for persistent viral fever and lab review.',
          },
        ]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAppointments();
  }, []);

  const updateStatus = async (id, status) => {
    try {
      await fetch(`${getDjangoBase()}/appointments`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, status }),
      });
      loadAppointments();
    } catch {
      setAppointments((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status } : a))
      );
    }
  };

  return (
    <Layout activePage="appointments">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1>Doctor Consultations & Appointments</h1>
          <p>Manage your upcoming and past doctor visits</p>
        </div>
        <Link href="/doctors" className="btn-primary">
          + Book New Appointment
        </Link>
      </div>

      <div className="card">
        {loading ? (
          <p className="text-muted" style={{ textAlign: 'center', padding: '24px' }}>Loading appointments...</p>
        ) : appointments.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p className="text-muted">No appointments scheduled.</p>
            <Link href="/doctors" className="btn-primary" style={{ marginTop: '12px', display: 'inline-block' }}>
              Find a doctor and book an appointment
            </Link>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Date & Time</th>
                <th>Doctor</th>
                <th>Specialization</th>
                <th>Hospital / Chamber</th>
                <th>Status</th>
                <th>Notes</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{fmtDate(a.appointment_date)}</strong>
                    <div style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>{fmtTime(a.appointment_date)}</div>
                  </td>
                  <td><strong>{a.doctor_name}</strong></td>
                  <td>{a.specialization}</td>
                  <td>{a.hospital} {a.location ? `(${a.location})` : ''}</td>
                  <td>
                    <span className={`badge ${a.status === 'confirmed' ? 'badge-low' : a.status === 'completed' ? 'badge-low' : a.status === 'cancelled' ? 'badge-high' : 'badge-medium'}`}>
                      {a.status}
                    </span>
                  </td>
                  <td style={{ maxWidth: '200px', fontSize: '13px', color: 'var(--ink-muted)' }}>
                    {a.notes || '—'}
                  </td>
                  <td>
                    {a.status !== 'cancelled' && a.status !== 'completed' && (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => updateStatus(a.id, 'cancelled')}
                          className="btn-ghost"
                          style={{ padding: '4px 10px', fontSize: '12px', color: 'var(--red-urgent)' }}
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => updateStatus(a.id, 'completed')}
                          className="btn-ghost"
                          style={{ padding: '4px 10px', fontSize: '12px', color: 'var(--green-safe)' }}
                        >
                          Complete
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
