import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const INVESTMENT_TYPES = ["MF", "SIP", "FD", "PPF", "Stocks", "Gold", "RD"];
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF19A3', '#19FFD8'];

export default function Investments() {
  const [members, setMembers] = useState([]);
  const [investments, setInvestments] = useState([]);
  const [loading, setLoading] = useState(true);

  // Form states
  const [memberId, setMemberId] = useState('');
  const [type, setType] = useState('MF');
  const [name, setName] = useState('');
  const [investedAmount, setInvestedAmount] = useState('');
  const [currentValue, setCurrentValue] = useState('');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [submitting, setSubmitting] = useState(false);

  // Valuation update state
  const [updatingInvId, setUpdatingInvId] = useState(null);
  const [newValuation, setNewValuation] = useState('');

  const fetchData = async () => {
    try {
      const [mList, iList] = await Promise.all([
        api.getMembers(),
        api.getInvestments()
      ]);
      setMembers(mList);
      setInvestments(iList);
      if (mList.length > 0 && !memberId) {
        setMemberId(mList[0].id.toString());
      }
      setLoading(false);
    } catch (err) {
      alert("Error loading investments: " + err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!memberId || !name || !investedAmount || !currentValue) return;

    setSubmitting(true);
    api.addInvestment({
      member_id: parseInt(memberId),
      type,
      name: name.trim(),
      invested_amount: parseFloat(investedAmount),
      current_value: parseFloat(currentValue),
      start_date: startDate
    })
      .then(() => {
        setName('');
        setInvestedAmount('');
        setCurrentValue('');
        setSubmitting(false);
        fetchData();
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleUpdateValuation = (id) => {
    const val = parseFloat(newValuation);
    if (isNaN(val) || val < 0) {
      alert("Please enter a valid valuation.");
      return;
    }

    api.updateInvestmentValuation(id, val)
      .then(() => {
        setUpdatingInvId(null);
        setNewValuation('');
        fetchData();
      })
      .catch(err => alert(err.message));
  };

  const handleDelete = (id) => {
    if (window.confirm("Are you sure you want to delete this investment record?")) {
      api.deleteInvestment(id)
        .then(() => fetchData())
        .catch(err => alert(err.message));
    }
  };

  // Portfolio aggregates
  const totalInvested = investments.reduce((sum, i) => sum + i.invested_amount, 0);
  const totalCurrent = investments.reduce((sum, i) => sum + i.current_value, 0);
  const totalReturns = totalCurrent - totalInvested;
  const totalRoi = totalInvested > 0 ? (totalReturns / totalInvested * 100) : 0;

  // Weighted CAGR
  const validCagrInv = investments.filter(i => i.cagr > 0);
  const weightedCagr = validCagrInv.reduce((sum, i) => sum + (i.cagr * i.invested_amount), 0) / (validCagrInv.reduce((sum, i) => sum + i.invested_amount, 0) || 1);

  // Group allocations for Pie Chart
  const typeSums = {};
  investments.forEach(i => {
    typeSums[i.type] = (typeSums[i.type] || 0) + i.current_value;
  });
  const pieData = Object.keys(typeSums).map(t => ({
    name: t,
    value: typeSums[t]
  }));

  if (loading) return <div>Loading investments...</div>;

  return (
    <div>
      <h2 className="section-title">Investment Portfolio Tracker</h2>
      <p className="section-subtitle">Track family assets, monitor valuations, and calculate compound growth rates (CAGR).</p>

      {/* KPI summary tiles */}
      <div className="card-grid">
        <div className="card card-accent-blue">
          <div className="card-header">Total Invested</div>
          <div className="card-value">₹{totalInvested.toLocaleString()}</div>
        </div>

        <div className="card card-accent-green">
          <div className="card-header">Current Value</div>
          <div className="card-value">₹{totalCurrent.toLocaleString()}</div>
        </div>

        <div className="card" style={{ borderLeft: `5px solid ${totalReturns >= 0 ? '#10b981' : '#ef4444'}` }}>
          <div className="card-header">Total Returns</div>
          <div className="card-value" style={{ color: totalReturns >= 0 ? '#10b981' : '#ef4444' }}>
            ₹{totalReturns.toLocaleString()} <span style={{ fontSize: '0.85rem' }}>({totalRoi.toFixed(2)}% ROI)</span>
          </div>
        </div>

        <div className="card card-accent-gold">
          <div className="card-header">Weighted CAGR</div>
          <div className="card-value" style={{ color: '#f59e0b' }}>{weightedCagr.toFixed(2)}%</div>
        </div>
      </div>

      {/* Two Column details */}
      <div className="dashboard-columns">
        {/* Table log */}
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>💼 Asset Holdings</h3>
          
          {investments.length === 0 ? (
            <div className="card">No investment holdings logged yet.</div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Type</th>
                    <th>Name</th>
                    <th>Invested</th>
                    <th>Current Value</th>
                    <th>Returns</th>
                    <th>CAGR</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {investments.map(i => {
                    const isUpdating = updatingInvId === i.id;
                    return (
                      <tr key={i.id}>
                        <td>{i.member_name}</td>
                        <td>
                          <span className="badge badge-gray">{i.type}</span>
                        </td>
                        <td>{i.name}</td>
                        <td>₹{i.invested_amount.toLocaleString()}</td>
                        <td style={{ fontWeight: 'bold' }}>₹{i.current_value.toLocaleString()}</td>
                        <td style={{ color: i.returns >= 0 ? '#10b981' : '#ef4444' }}>
                          ₹{i.returns.toLocaleString()} ({i.roi.toFixed(1)}%)
                        </td>
                        <td style={{ color: '#f59e0b', fontWeight: 'bold' }}>{i.cagr.toFixed(1)}%</td>
                        <td>
                          {isUpdating ? (
                            <div style={{ display: 'flex', gap: '6px' }}>
                              <input 
                                type="number" 
                                placeholder="Value ₹" 
                                value={newValuation} 
                                onChange={e => setNewValuation(e.target.value)} 
                                style={{ padding: '4px 8px', width: '90px', fontSize: '0.8rem' }}
                              />
                              <button className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => handleUpdateValuation(i.id)}>
                                Save
                              </button>
                              <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => setUpdatingInvId(null)}>
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', gap: '6px' }}>
                              <button 
                                className="btn btn-secondary" 
                                style={{ padding: '4px 8px', fontSize: '0.75rem' }} 
                                onClick={() => {
                                  setUpdatingInvId(i.id);
                                  setNewValuation(i.current_value.toString());
                                }}
                              >
                                Update Val
                              </button>
                              <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleDelete(i.id)}>
                                Delete
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Allocation Pie Chart */}
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>📊 Asset Allocations</h3>
          
          {pieData.length === 0 ? (
            <div className="card">No investment holdings found to show breakdown.</div>
          ) : (
            <div className="card" style={{ height: 320, padding: 12, marginBottom: '24px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `₹${value.toLocaleString()}`} />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Form to Add Investment */}
          <div className="form-container" style={{ maxWidth: 'none' }}>
            <h3 className="form-title">Log Investment Holding</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Owner / Family Member</label>
                <select value={memberId} onChange={e => setMemberId(e.target.value)} required>
                  {members.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Asset Type</label>
                <select value={type} onChange={e => setType(e.target.value)}>
                  {INVESTMENT_TYPES.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Asset Name</label>
                <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="E.g., SBI Bluechip Mutual Fund" required />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Invested Amount (₹)</label>
                <input type="number" min="0.01" step="0.01" value={investedAmount} onChange={e => setInvestedAmount(e.target.value)} required />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Current Value (₹)</label>
                <input type="number" min="0" step="0.01" value={currentValue} onChange={e => setCurrentValue(e.target.value)} required />
              </div>

              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label>Purchase / Start Date</label>
                <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} required />
              </div>

              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Logging...' : 'Add Investment'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
