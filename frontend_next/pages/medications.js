import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { getUser, fmtDate, getDjangoBase } from '../lib/api';

export default function Medications() {
  const [medications, setMedications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newMed, setNewMed] = useState({
    medicine_name: '',
    dosage: '',
    frequency: 'once_daily',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    instructions: '',
  });

  const loadMedications = () => {
    const u = getUser();
    if (!u) return;

    fetch(`${getDjangoBase()}/medications?user_id=${u.id}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.success && Array.isArray(data.medications)) {
          setMedications(data.medications);
        }
      })
      .catch(() => {
        // Demo fallback
        setMedications([
          {
            id: 1,
            medicine_name: 'Paracetamol',
            dosage: '500mg',
            frequency: 'three_times',
            start_date: new Date().toISOString(),
            instructions: 'Take after meals for fever relief. Maximum 3000mg/day.',
            active: 1,
          },
          {
            id: 2,
            medicine_name: 'Oral Rehydration Salts (ORS)',
            dosage: '1 sachet in 500ml water',
            frequency: 'as_needed',
            start_date: new Date().toISOString(),
            instructions: 'Sip continuously throughout the day for electrolyte replenishment.',
            active: 1,
          },
        ]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadMedications();
  }, []);

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    const u = getUser();
    if (!u || !newMed.medicine_name) return;

    try {
      await fetch(`${getDjangoBase()}/medications`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: u.id,
          ...newMed,
        }),
      });
      setShowAddModal(false);
      setNewMed({
        medicine_name: '',
        dosage: '',
        frequency: 'once_daily',
        start_date: new Date().toISOString().split('T')[0],
        end_date: '',
        instructions: '',
      });
      loadMedications();
    } catch {
      setMedications((prev) => [{ id: Date.now(), ...newMed, active: 1 }, ...prev]);
      setShowAddModal(false);
    }
  };

  const handleDeactivate = async (id) => {
    const u = getUser();
    if (!u) return;

    try {
      await fetch(`${getDjangoBase()}/medications`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, user_id: u.id }),
      });
      loadMedications();
    } catch {
      setMedications((prev) => prev.filter((m) => m.id !== id));
    }
  };

  const formatFreq = (freq) => {
    switch (freq) {
      case 'once_daily':
        return 'Once Daily';
      case 'twice_daily':
        return 'Twice Daily';
      case 'three_times':
        return 'Three Times Daily';
      case 'four_times':
        return 'Four Times Daily';
      case 'every_8h':
        return 'Every 8 Hours';
      case 'every_6h':
        return 'Every 6 Hours';
      case 'as_needed':
        return 'As Needed';
      case 'weekly':
        return 'Weekly';
      default:
        return freq || 'Once Daily';
    }
  };

  return (
    <Layout activePage="medications">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1>Medication Schedule & Active Reminders</h1>
          <p>Track your prescribed courses and dosage schedules</p>
        </div>
        <button onClick={() => setShowAddModal(true)} className="btn-primary">
          + Add Medication
        </button>
      </div>

      <div className="card">
        {loading ? (
          <p className="text-muted" style={{ textAlign: 'center', padding: '24px' }}>Loading medications...</p>
        ) : medications.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p className="text-muted">No active medications scheduled.</p>
            <button onClick={() => setShowAddModal(true)} className="btn-primary" style={{ marginTop: '12px' }}>
              Add a medication
            </button>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Medicine Name</th>
                <th>Dosage</th>
                <th>Frequency</th>
                <th>Schedule Period</th>
                <th>Instructions & Route</th>
                <th>Prescription Source</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {medications.map((m) => (
                <tr key={m.id}>
                  <td><strong>💊 {m.medicine_name}</strong></td>
                  <td>{m.dosage || '—'}</td>
                  <td>
                    <span className="badge badge-low" style={{ background: 'var(--teal-light)', color: 'var(--teal)' }}>
                      {formatFreq(m.frequency)}
                    </span>
                  </td>
                  <td style={{ fontSize: '13px' }}>
                    {fmtDate(m.start_date)} {m.end_date ? `to ${fmtDate(m.end_date)}` : '(Ongoing)'}
                  </td>
                  <td style={{ fontSize: '13px', color: 'var(--ink-muted)', maxWidth: '240px' }}>
                    {m.instructions || '—'}
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>
                    {m.document_name ? `📄 ${m.document_name}` : 'Self Added'}
                  </td>
                  <td>
                    <button
                      onClick={() => handleDeactivate(m.id)}
                      className="btn-ghost"
                      style={{ padding: '4px 10px', fontSize: '12px', color: 'var(--red-urgent)' }}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Medication Modal */}
      {showAddModal && (
        <div className="modal-backdrop show" onClick={() => setShowAddModal(false)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Active Medication</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>✕</button>
            </div>

            <form onSubmit={handleAddSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label htmlFor="medicine_name">Medicine Name</label>
                  <input
                    type="text"
                    id="medicine_name"
                    placeholder="e.g. Paracetamol, Amoxicillin"
                    value={newMed.medicine_name}
                    onChange={(e) => setNewMed({ ...newMed, medicine_name: e.target.value })}
                    required
                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}
                  />
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label htmlFor="dosage">Dosage</label>
                    <input
                      type="text"
                      id="dosage"
                      placeholder="e.g. 500mg, 1 tablet"
                      value={newMed.dosage}
                      onChange={(e) => setNewMed({ ...newMed, dosage: e.target.value })}
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="frequency">Frequency</label>
                    <select
                      id="frequency"
                      value={newMed.frequency}
                      onChange={(e) => setNewMed({ ...newMed, frequency: e.target.value })}
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    >
                      <option value="once_daily">Once Daily</option>
                      <option value="twice_daily">Twice Daily</option>
                      <option value="three_times">Three Times Daily</option>
                      <option value="four_times">Four Times Daily</option>
                      <option value="every_8h">Every 8 Hours</option>
                      <option value="every_6h">Every 6 Hours</option>
                      <option value="as_needed">As Needed (PRN)</option>
                      <option value="weekly">Weekly</option>
                    </select>
                  </div>
                </div>

                <div className="grid-2">
                  <div className="form-group">
                    <label htmlFor="start_date">Start Date</label>
                    <input
                      type="date"
                      id="start_date"
                      value={newMed.start_date}
                      onChange={(e) => setNewMed({ ...newMed, start_date: e.target.value })}
                      required
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="end_date">End Date (Optional)</label>
                    <input
                      type="date"
                      id="end_date"
                      value={newMed.end_date}
                      onChange={(e) => setNewMed({ ...newMed, end_date: e.target.value })}
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="instructions">Instructions & Advisory</label>
                  <textarea
                    id="instructions"
                    rows={2}
                    placeholder="e.g. Take after breakfast with a full glass of water..."
                    value={newMed.instructions}
                    onChange={(e) => setNewMed({ ...newMed, instructions: e.target.value })}
                    style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)', font: 'inherit' }}
                  />
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button type="button" className="btn-ghost" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save Medication
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
