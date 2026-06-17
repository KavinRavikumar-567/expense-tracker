import React, { useEffect, useState } from 'react';
import { api } from '../api';

const INSURANCE_TYPES = ["Life", "Health", "Term", "Vehicle", "Home"];

export default function Insurance() {
  const [members, setMembers] = useState([]);
  const [insurance, setInsurance] = useState([]);
  const [loading, setLoading] = useState(true);

  // Form states
  const [memberId, setMemberId] = useState('');
  const [type, setType] = useState('Health');
  const [provider, setProvider] = useState('');
  const [premium, setPremium] = useState('');
  const [sumAssured, setSumAssured] = useState('');
  const [renewalDate, setRenewalDate] = useState(new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0]);
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      const [mList, iList] = await Promise.all([
        api.getMembers(),
        api.getInsurance()
      ]);
      setMembers(mList);
      setInsurance(iList);
      if (mList.length > 0 && !memberId) {
        setMemberId(mList[0].id.toString());
      }
      setLoading(false);
    } catch (err) {
      alert("Error loading insurance: " + err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!memberId || !provider || !premium || !sumAssured) return;

    setSubmitting(true);
    api.addInsurance({
      member_id: parseInt(memberId),
      type,
      provider: provider.trim(),
      premium: parseFloat(premium),
      sum_assured: parseFloat(sumAssured),
      renewal_date: renewalDate
    })
      .then(() => {
        setProvider('');
        setPremium('');
        setSumAssured('');
        setSubmitting(false);
        fetchData();
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleDelete = (id) => {
    if (window.confirm("Are you sure you want to delete this insurance policy?")) {
      api.deleteInsurance(id)
        .then(() => fetchData())
        .catch(err => alert(err.message));
    }
  };

  // 1. Renewal alerts
  const checkRenewalState = (renewalStr) => {
    try {
      const renewalDate = new Date(renewalStr);
      const today = new Date();
      // Reset hours
      today.setHours(0, 0, 0, 0);
      renewalDate.setHours(0, 0, 0, 0);
      
      const diffTime = renewalDate.getTime() - today.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays < 0) {
        return { alert: true, color: '#ef4444', text: `EXPIRED by ${Math.abs(diffDays)} days` };
      } else if (diffDays <= 30) {
        return { alert: true, color: '#f59e0b', text: `Due in ${diffDays} days` };
      }
    } catch (err) {}
    return { alert: false };
  };

  // 2. Coverage Gaps Rule Check
  const analyzeGaps = () => {
    const alerts = [];
    if (insurance.length === 0) {
      alerts.push({
        level: 'Critical',
        message: 'No insurance policies logged! Your family is completely exposed to financial risks.'
      });
      return alerts;
    }

    const healthPolicies = insurance.filter(i => i.type === 'Health');
    if (healthPolicies.length === 0) {
      alerts.push({
        level: 'Critical',
        message: 'No Health Insurance found! Medical emergencies can wipe out your savings.'
      });
    } else {
      const insuredIds = new Set(healthPolicies.map(hp => hp.member_id));
      const missingHealth = members.filter(m => !insuredIds.has(m.id)).map(m => m.name);
      if (missingHealth.length > 0) {
        alerts.push({
          level: 'Warning',
          message: `Health insurance is missing for: ${missingHealth.join(', ')}.`
        });
      }
    }

    // Has kids, no term
    const hasKids = members.some(m => m.relationship === 'Child');
    const hasTerm = insurance.some(i => i.type === 'Term' || i.type === 'Life');
    if (hasKids && !hasTerm) {
      alerts.push({
        level: 'Warning',
        message: 'You have children but no Term Life Insurance! Dependents\' future is at risk.'
      });
    }

    return alerts;
  };

  const gapAlerts = analyzeGaps();
  const renewalItems = insurance.map(i => ({ i, state: checkRenewalState(i.renewal_date) })).filter(item => item.state.alert);

  if (loading) return <div>Loading insurance...</div>;

  return (
    <div>
      <h2 className="section-title">Insurance Manager</h2>
      <p className="section-subtitle">Track family policies, monitor upcoming premiums, and discover coverage gaps.</p>

      {/* Two Column Layout */}
      <div className="dashboard-columns">
        {/* Risk Alerts & Table */}
        <div>
          {/* Risk Alerts Panel */}
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>🛡️ Gap Analysis & Alerts</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
            {gapAlerts.map((alert, idx) => {
              const borderCol = alert.level === 'Critical' ? '#ef4444' : '#f59e0b';
              return (
                <div key={idx} className="alert-item" style={{ borderLeft: `4px solid ${borderCol}` }}>
                  <span className="alert-category" style={{ color: borderCol }}>{alert.level} RISK</span>
                  <div className="alert-message">{alert.message}</div>
                </div>
              );
            })}
            
            {gapAlerts.length === 0 && (
              <div className="card" style={{ borderLeft: '4px solid #10b981', color: '#10b981' }}>
                🎉 Primary insurance coverages look healthy!
              </div>
            )}
          </div>

          {/* Renewal alerts */}
          {renewalItems.length > 0 && (
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>🚨 Renewal Alerts</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {renewalItems.map(({ i, state }, idx) => (
                  <div key={idx} style={{ backgroundColor: `${state.color}22`, border: `1px solid ${state.color}`, color: '#ffffff', borderRadius: '8px', padding: '16px' }}>
                    ⚠️ Policy <b>{i.type} ({i.provider})</b> for <b>{i.member_name}</b> is <span style={{ color: state.color, fontWeight: 'bold' }}>{state.text}</span>.
                    <div style={{ fontSize: '0.85rem', marginTop: '4px', opacity: 0.85 }}>
                      Renewal Date: {i.renewal_date} &nbsp;|&nbsp; Premium: ₹{i.premium.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active Policies Table */}
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>🛡️ Active Coverages</h3>
          {insurance.length === 0 ? (
            <div className="card">No active policies found. Log a policy in the form on the right.</div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Type</th>
                    <th>Provider</th>
                    <th>Annual Premium</th>
                    <th>Sum Assured</th>
                    <th>Renewal Date</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {insurance.map(i => (
                    <tr key={i.id}>
                      <td>{i.member_name}</td>
                      <td>
                        <span className="badge badge-blue">{i.type}</span>
                      </td>
                      <td>{i.provider}</td>
                      <td style={{ fontWeight: 'bold' }}>₹{i.premium.toLocaleString()}</td>
                      <td style={{ fontWeight: 'bold' }}>₹{i.sum_assured.toLocaleString()}</td>
                      <td>{i.renewal_date}</td>
                      <td>
                        <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleDelete(i.id)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Form to Add Policy */}
        <div>
          <div className="form-container" style={{ maxWidth: 'none' }}>
            <h3 className="form-title">Log Insurance Policy</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Policy Holder (Member)</label>
                <select value={memberId} onChange={e => setMemberId(e.target.value)} required>
                  {members.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Policy Type</label>
                <select value={type} onChange={e => setType(e.target.value)}>
                  {INSURANCE_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Insurance Provider</label>
                <input type="text" value={provider} onChange={e => setProvider(e.target.value)} placeholder="E.g., HDFC Ergo, LIC" required />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Annual Premium (₹)</label>
                <input type="number" min="0" value={premium} onChange={e => setPremium(e.target.value)} placeholder="E.g., 8000" required />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Sum Assured (₹)</label>
                <input type="number" min="0" value={sumAssured} onChange={e => setSumAssured(e.target.value)} placeholder="E.g., 500000" required />
              </div>

              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label>Renewal Date</label>
                <input type="date" value={renewalDate} onChange={e => setRenewalDate(e.target.value)} required />
              </div>

              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Logging...' : 'Log Policy'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
