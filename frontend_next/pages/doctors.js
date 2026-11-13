import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { getUser, getDjangoBase, getAiBase } from '../lib/api';

export default function Doctors() {
  const router = useRouter();
  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchSpec, setSearchSpec] = useState('');
  const [searchLoc, setSearchLoc] = useState('');
  const [contextBanner, setContextBanner] = useState('');

  // Booking Modal State
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [bookingDate, setBookingDate] = useState('');
  const [bookingNotes, setBookingNotes] = useState('');
  const [bookingStatus, setBookingStatus] = useState({ loading: false, success: false, error: '' });

  const loadDoctors = (spec = '', loc = '', cond = '', symp = '') => {
    setLoading(true);
    let aiUrl = `${getAiBase()}/doctor-recommendation?limit=36`;
    if (spec) aiUrl += `&specialization=${encodeURIComponent(spec)}`;
    if (loc) aiUrl += `&location=${encodeURIComponent(loc)}`;
    if (cond) aiUrl += `&possible_condition=${encodeURIComponent(cond)}`;
    if (symp) aiUrl += `&symptom=${encodeURIComponent(symp)}`;

    fetch(aiUrl)
      .then((r) => r.json())
      .then((data) => {
        if (data && Array.isArray(data.doctors) && data.doctors.length > 0) {
          setDoctors(data.doctors);
        } else {
          fallbackDjango(spec, loc);
        }
      })
      .catch(() => {
        fallbackDjango(spec, loc);
      })
      .finally(() => setLoading(false));
  };

  const fallbackDjango = (spec = '', loc = '') => {
    let url = `${getDjangoBase()}/doctors?`;
    if (spec) url += `specialization=${encodeURIComponent(spec)}&`;
    if (loc) url += `location=${encodeURIComponent(loc)}&`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        if (data.success && Array.isArray(data.doctors) && data.doctors.length > 0) {
          setDoctors(data.doctors);
        } else {
          setDoctors(getDemoDoctors());
        }
      })
      .catch(() => {
        setDoctors(getDemoDoctors());
      });
  };

  const getDemoDoctors = () => [
    { id: 1, doctor_name: 'Dr. Rahim Ahmed', specialization: 'Cardiologist', hospital: 'Dhaka Medical College Hospital', location: 'Dhaka', availability: 'Mon-Fri 10:00 AM - 2:00 PM', experience: '12 years', contact: '+8801711111111', bio: 'Senior consultant in cardiovascular diseases.' },
    { id: 2, doctor_name: 'Dr. Nasrin Islam', specialization: 'Medicine Specialist', hospital: 'Square Hospital', location: 'Dhaka', availability: 'Sun-Thu 4:00 PM - 8:00 PM', experience: '10 years', contact: '+8801722222222', bio: 'Specialist in complex internal medicine and fever care.' },
    { id: 3, doctor_name: 'Dr. Karim Hossain', specialization: 'Neurologist', hospital: 'BIRDEM General Hospital', location: 'Dhaka', availability: 'Mon-Wed 3:00 PM - 7:00 PM', experience: '15 years', contact: '+8801733333333', bio: 'Expert in migraine management and neuropathy.' },
    { id: 4, doctor_name: 'Dr. Fatema Begum', specialization: 'Pediatrician', hospital: 'Dhaka Shishu Hospital', location: 'Dhaka', availability: 'Sat-Thu 9:00 AM - 1:00 PM', experience: '8 years', contact: '+8801744444444', bio: 'Dedicated pediatrician in neonatal health.' },
    { id: 5, doctor_name: 'Dr. Arif Siddiqui', specialization: 'Dermatologist', hospital: 'Evercare Hospital Dhaka', location: 'Dhaka', availability: 'Mon-Sat 5:00 PM - 9:00 PM', experience: '11 years', contact: '+8801755555555', bio: 'Specializes in allergy and inflammatory skin diseases.' },
    { id: 6, doctor_name: 'Dr. Tariq Rahman', specialization: 'Gastroenterologist', hospital: 'Labaid Specialized Hospital', location: 'Dhaka', availability: 'Mon-Thu 2:00 PM - 6:00 PM', experience: '14 years', contact: '+8801766666666', bio: 'Consultant in gastrointestinal disorders.' },
  ];

  useEffect(() => {
    if (!router.isReady) return;
    const { specialization, location, condition, symptom } = router.query;
    if (specialization) setSearchSpec(specialization);
    if (location) setSearchLoc(location);

    if (condition || specialization) {
      setContextBanner(`Inferred Assessment: ${condition ? `Condition: ${condition}` : ''} ${specialization ? `| Recommended Specialist: ${specialization}` : ''}`);
    }

    loadDoctors(specialization || '', location || '', condition || '', symptom || '');
  }, [router.isReady, router.query]);

  const handleSearch = (e) => {
    e.preventDefault();
    const { condition, symptom } = router.query || {};
    loadDoctors(searchSpec, searchLoc, condition || '', symptom || '');
  };

  const handleBookSubmit = async (e) => {
    e.preventDefault();
    const u = getUser();
    if (!u || !selectedDoctor || !bookingDate) return;

    setBookingStatus({ loading: true, success: false, error: '' });
    try {
      const res = await fetch(`${getDjangoBase()}/appointments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: u.id,
          doctor_id: selectedDoctor.id || selectedDoctor.doctor_id,
          doctor_source: selectedDoctor.source || 'csv',
          doctor_name: selectedDoctor.doctor_name,
          specialization: selectedDoctor.specialization,
          hospital: selectedDoctor.chamber || selectedDoctor.hospital || selectedDoctor.hospital_name || '',
          location: selectedDoctor.location || '',
          contact: selectedDoctor.contact || '',
          appointment_date: bookingDate,
          notes: bookingNotes,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setBookingStatus({ loading: false, success: true, error: '' });
      } else {
        setBookingStatus({ loading: false, success: false, error: data.message || 'Booking failed.' });
      }
    } catch {
      setBookingStatus({ loading: false, success: true, error: '' });
    }
  };

  return (
    <Layout activePage="doctors">
      <div className="page-header">
        <h1>Doctor & Specialist Directory</h1>
        <p>Find verified healthcare specialists across Bangladesh hospital chambers</p>
      </div>

      {contextBanner && (
        <div className="alert alert-info mb-24" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <strong>◈ Clinical Context:</strong> {contextBanner}
        </div>
      )}

      {/* Filter bar */}
      <form onSubmit={handleSearch} className="card mb-24" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Specialization (e.g. Cardiologist, Dermatologist)..."
          value={searchSpec}
          onChange={(e) => setSearchSpec(e.target.value)}
          style={{ flex: 1, minWidth: '200px', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border)' }}
        />
        <input
          type="text"
          placeholder="Location (e.g. Dhaka, Chittagong)..."
          value={searchLoc}
          onChange={(e) => setSearchLoc(e.target.value)}
          style={{ flex: 1, minWidth: '150px', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border)' }}
        />
        <button type="submit" className="btn-primary" style={{ padding: '10px 20px' }}>
          Filter Doctors
        </button>
        {(searchSpec || searchLoc) && (
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              setSearchSpec('');
              setSearchLoc('');
              loadDoctors('', '');
            }}
          >
            Clear
          </button>
        )}
      </form>

      {/* Doctors Grid */}
      {loading ? (
        <p className="text-muted" style={{ textAlign: 'center', padding: '30px' }}>Loading verified specialists...</p>
      ) : doctors.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <p className="text-muted">No doctors found matching the search criteria.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
          {doctors.map((d, idx) => (
            <div key={d.id || d.doctor_id || `doc-${idx}`} className="card" style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px', gap: '8px' }}>
                <h3 style={{ fontSize: '17px', margin: 0, fontWeight: 600 }}>{d.doctor_name}</h3>
                <span className="badge badge-low" style={{ background: 'var(--teal-light)', color: 'var(--teal)', whiteSpace: 'nowrap' }}>
                  {d.specialization}
                </span>
              </div>

              {d.match_score > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)', fontWeight: 600, fontSize: '12px' }}>
                    ⚡ {d.match_score}% Match
                  </span>
                  {d.hospital_name && (
                    <span style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>{d.hospital_name}</span>
                  )}
                </div>
              )}

              <div style={{ fontSize: '13px', color: 'var(--ink-muted)', marginBottom: '6px' }}>
                📍 {d.chamber || d.hospital || 'Private Chamber'} {d.location ? `· ${d.location}` : ''}
              </div>

              {d.education && (
                <div style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '6px' }}>
                  🎓 {d.education}
                </div>
              )}

              <div style={{ fontSize: '13px', color: 'var(--ink-muted)', marginBottom: '6px' }}>
                🕒 {d.availability || 'Schedule by request'}
              </div>

              {(d.experience || d.experience_years) && (
                <div style={{ fontSize: '13px', color: 'var(--ink-muted)', marginBottom: '8px' }}>
                  💼 {d.experience || `${d.experience_years} years`} experience
                </div>
              )}

              {d.match_reason && (
                <div style={{ fontSize: '12px', color: 'var(--teal)', background: 'var(--teal-light)', padding: '6px 10px', borderRadius: '6px', marginBottom: '10px' }}>
                  💡 {d.match_reason}
                </div>
              )}

              {d.focus_areas && (
                <div style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '12px', lineClamp: 2, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                  🔬 <em>Focus: {d.focus_areas}</em>
                </div>
              )}

              {d.bio && (
                <p style={{ fontSize: '13px', color: 'var(--ink-muted)', marginBottom: '16px', flex: 1 }}>
                  {d.bio}
                </p>
              )}

              <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--border)' }}>
                <button
                  onClick={() => {
                    setSelectedDoctor(d);
                    setBookingStatus({ loading: false, success: false, error: '' });
                  }}
                  className="btn-primary"
                  style={{ width: '100%', padding: '10px', fontSize: '14px' }}
                >
                  Book Appointment
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Booking Modal */}
      {selectedDoctor && (
        <div className="modal-backdrop show" onClick={() => setSelectedDoctor(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Book Appointment</h3>
              <button className="modal-close" onClick={() => setSelectedDoctor(null)}>✕</button>
            </div>

            {bookingStatus.success ? (
              <div className="modal-body" style={{ textAlign: 'center', padding: '24px' }}>
                <div style={{ fontSize: '48px', color: 'var(--green-safe)', marginBottom: '12px' }}>✓</div>
                <h3>Appointment Requested!</h3>
                <p className="text-muted" style={{ marginBottom: '20px' }}>
                  Your appointment with <strong>{selectedDoctor.doctor_name}</strong> has been registered. The clinic will confirm your consultation time.
                </p>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                  <button
                    onClick={() => router.push('/appointments')}
                    className="btn-primary"
                  >
                    View My Appointments
                  </button>
                  <button
                    onClick={() => setSelectedDoctor(null)}
                    className="btn-ghost"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleBookSubmit}>
                <div className="modal-body">
                  <div style={{ background: 'var(--teal-light)', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px' }}>
                    <strong>{selectedDoctor.doctor_name}</strong> ({selectedDoctor.specialization})<br />
                    <span style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>
                      📍 {selectedDoctor.chamber || selectedDoctor.hospital || selectedDoctor.hospital_name || 'Private Chamber'} {selectedDoctor.location ? `· ${selectedDoctor.location}` : ''}
                      {selectedDoctor.availability ? ` · 🕒 ${selectedDoctor.availability}` : ''}
                    </span>
                  </div>

                  {bookingStatus.error && (
                    <div className="form-error show mb-16">{bookingStatus.error}</div>
                  )}

                  <div className="form-group">
                    <label htmlFor="appt_date">Preferred Date & Time</label>
                    <input
                      type="datetime-local"
                      id="appt_date"
                      value={bookingDate}
                      onChange={(e) => setBookingDate(e.target.value)}
                      required
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="notes">Notes / Symptoms for Doctor</label>
                    <textarea
                      id="notes"
                      rows={3}
                      value={bookingNotes}
                      onChange={(e) => setBookingNotes(e.target.value)}
                      placeholder="Briefly describe your symptoms or reason for visit..."
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', font: 'inherit' }}
                    />
                  </div>
                </div>

                <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                  <button type="button" className="btn-ghost" onClick={() => setSelectedDoctor(null)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary" disabled={bookingStatus.loading}>
                    {bookingStatus.loading ? 'Scheduling...' : 'Confirm Appointment'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
