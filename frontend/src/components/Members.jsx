import React, { useEffect, useState } from 'react';
import { api } from '../api';

export default function Members({ user, onUpdateUser }) {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [age, setAge] = useState(25);
  const [relationship, setRelationship] = useState(user.mode === 'Bachelor' ? 'Dependent' : 'Spouse');
  const [income, setIncome] = useState(0);
  const [isDependent, setIsDependent] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const fetchMembers = () => {
    setLoading(true);
    api.getMembers()
      .then(res => {
        setMembers(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchMembers();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    api.addMember({
      name: name.trim(),
      age: parseInt(age),
      relationship,
      monthly_income: parseFloat(income),
      is_dependent: isDependent
    })
      .then(() => {
        setName('');
        setIncome(0);
        setIsDependent(true);
        setSubmitting(false);
        fetchMembers();
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleDelete = (id) => {
    if (window.confirm("Are you sure you want to delete this member? All associated transactions and budgets will be lost.")) {
      api.deleteMember(id)
        .then(() => {
          fetchMembers();
        })
        .catch(err => {
          alert(err.message);
        });
    }
  };

  const primaryProfile = members.find(m => m.relationship === 'Self');
  const otherMembers = members.filter(m => m.relationship !== 'Self');

  if (loading && members.length === 0) return <div>Loading profiles...</div>;

  return (
    <div>
      <h2 className="section-title">Profiles & Family Management</h2>
      <p className="section-subtitle">Manage family contributors, dependents, and personal configurations for {user.mode} Mode.</p>

      {/* Primary User Information */}
      <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '16px' }}>Primary User</h3>
      {primaryProfile && (
        <div style={{ backgroundColor: '#ffffff', border: '1px solid var(--bg-border)', borderLeft: '5px solid var(--color-green)', padding: '20px', borderRadius: '8px', marginBottom: '32px' }}>
          <div className="flex-between">
            <div>
              <h4 style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
                {primaryProfile.name} <span className="badge badge-green" style={{ marginLeft: '8px' }}>Primary (Self)</span>
              </h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginTop: '6px' }}>
                Age: {primaryProfile.age} &nbsp;|&nbsp; Monthly Income: <b>₹{primaryProfile.monthly_income.toLocaleString()}</b>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Family Members list */}
      <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '16px' }}>Family Members & Dependents</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '40px' }}>
        {otherMembers.length === 0 ? (
          <div className="card">No family profiles added yet. Use the form below to add members.</div>
        ) : (
          otherMembers.map(m => {
            const badgeColor = m.is_dependent === 1 ? 'badge-gold' : 'badge-green';
            const statusLabel = m.is_dependent === 1 ? 'Dependent' : 'Contributor';
            
            return (
              <div key={m.id} className="card" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h4 style={{ fontWeight: 'bold', fontSize: '1rem' }}>
                    {m.name} 
                    <span className="badge badge-blue" style={{ marginLeft: '8px' }}>{m.relationship}</span>
                    <span className={`badge ${badgeColor}`} style={{ marginLeft: '6px' }}>{statusLabel}</span>
                  </h4>
                  <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '4px' }}>
                    Age: {m.age} &nbsp;|&nbsp; Income: <b>₹{m.monthly_income.toLocaleString()}</b>
                  </p>
                </div>
                <button className="btn btn-danger" style={{ padding: '6px 12px', fontSize: '0.85rem' }} onClick={() => handleDelete(m.id)}>
                  Remove
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Form to Add Member */}
      <div className="form-container">
        <h3 className="form-title">Add New Profile</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label>Name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="E.g., Priya" required />
            </div>

            <div className="form-group">
              <label>Age</label>
              <input type="number" min="1" max="120" value={age} onChange={e => setAge(e.target.value)} required />
            </div>

            <div className="form-group">
              <label>Relationship</label>
              <select value={relationship} onChange={e => setRelationship(e.target.value)}>
                {user.mode === 'Bachelor' ? (
                  <>
                    <option value="Dependent">Dependent</option>
                    <option value="Other">Other</option>
                  </>
                ) : (
                  <>
                    <option value="Spouse">Spouse</option>
                    <option value="Child">Child</option>
                    <option value="Parent">Parent</option>
                    <option value="Other">Other</option>
                  </>
                )}
              </select>
            </div>

            <div className="form-group">
              <label>Monthly Income (₹)</label>
              <input type="number" min="0" value={income} onChange={e => setIncome(e.target.value)} required />
            </div>

            <div className="form-group-full" style={{ flexDirection: 'row', alignItems: 'center', gap: '8px' }}>
              <input 
                type="checkbox" 
                id="isDependent" 
                checked={isDependent} 
                onChange={e => setIsDependent(e.target.checked)} 
                style={{ width: 'auto', margin: 0 }}
              />
              <label htmlFor="isDependent" style={{ cursor: 'pointer' }}>Mark as Dependent (relies on family income for expenses)</label>
            </div>
          </div>

          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Adding...' : 'Add Profile'}
          </button>
        </form>
      </div>
    </div>
  );
}
