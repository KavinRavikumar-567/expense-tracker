import React, { useEffect, useState } from 'react';
import { api } from '../api';

export default function Emergency({ user }) {
  const [efData, setEfData] = useState(null);
  const [balanceInput, setBalanceInput] = useState('');
  const [expenseEstimate, setExpenseEstimate] = useState(25000);
  const [updating, setUpdating] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchEmergencyData = async () => {
    try {
      const data = await api.getEmergencyFund();
      setEfData(data);
      setBalanceInput(data.current_amount.toString());
      // Estimate fallback
      const monthly = data.actual_average_expenses > 0 ? data.actual_average_expenses : (user.monthly_income * 0.5 || 25000);
      setExpenseEstimate(monthly);
      setLoading(false);
    } catch (err) {
      alert("Error loading emergency fund: " + err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmergencyData();
  }, []);

  const handleUpdateBalance = (e) => {
    e.preventDefault();
    const val = parseFloat(balanceInput);
    if (isNaN(val) || val < 0) return;

    setUpdating(true);
    api.updateEmergencyFund(val)
      .then(() => {
        setUpdating(false);
        fetchEmergencyData();
      })
      .catch(err => {
        alert(err.message);
        setUpdating(false);
      });
  };

  if (loading) return <div>Loading emergency tracker...</div>;
  if (!efData) return <div>No data available.</div>;

  // Custom calculations on the fly based on user inputs
  const targetMultiplier = user.mode === 'Bachelor' ? 3 : 6;
  const calculatedTarget = expenseEstimate * targetMultiplier;
  const currentVal = parseFloat(balanceInput) || 0;
  const calculatedGap = Math.max(0, calculatedTarget - currentVal);
  const calculatedRatio = expenseEstimate > 0 ? (currentVal / expenseEstimate) : 0;
  
  let calculatedStatus = 'Healthy';
  if (user.mode === 'Bachelor') {
    if (calculatedRatio < 1.0) calculatedStatus = 'Critical';
    else if (calculatedRatio < 3.0) calculatedStatus = 'Building';
    else calculatedStatus = 'Healthy';
  } else {
    if (calculatedRatio < 2.0) calculatedStatus = 'Critical';
    else if (calculatedRatio < 6.0) calculatedStatus = 'Building';
    else calculatedStatus = 'Healthy';
  }

  let statusColor = '#10b981';
  if (calculatedStatus === 'Critical') statusColor = '#ef4444';
  else if (calculatedStatus === 'Building') statusColor = '#f59e0b';

  const percentAchieved = Math.min(100, calculatedTarget > 0 ? (currentVal / calculatedTarget * 100) : 0);

  return (
    <div>
      <h2 className="section-title">Emergency Fund Tracker</h2>
      <p className="section-subtitle">Maintain liquidity reserves to safeguard against financial shocks ({user.mode} Mode).</p>

      {/* Inputs Section */}
      <div className="form-container" style={{ maxWidth: 'none' }}>
        <h3 className="form-title">Adjust Reserve Metrics</h3>
        <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <form onSubmit={handleUpdateBalance} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="form-group">
              <label>Current Emergency Fund Balance (₹)</label>
              <input 
                type="number" 
                min="0" 
                value={balanceInput} 
                onChange={e => setBalanceInput(e.target.value)} 
                required 
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={updating}>
              {updating ? 'Updating...' : 'Update Balance'}
            </button>
          </form>

          <div className="form-group">
            <label>Monthly Expense Estimate (₹)</label>
            <input 
              type="number" 
              min="1" 
              value={expenseEstimate} 
              onChange={e => setExpenseEstimate(parseFloat(e.target.value))} 
              required 
            />
            {efData.actual_average_expenses > 0 ? (
              <p style={{ fontSize: '0.8rem', color: '#10b981', marginTop: '6px' }}>
                📈 Verified average: ₹{efData.actual_average_expenses.toLocaleString()}/mo (from transactions)
              </p>
            ) : (
              <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '6px' }}>
                💡 Default estimate based on 50% of registered income.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="card-grid" style={{ marginTop: '24px' }}>
        <div className="card card-accent-blue">
          <div className="card-header">Target reserve ({targetMultiplier}x)</div>
          <div className="card-value">₹{calculatedTarget.toLocaleString()}</div>
        </div>

        <div className="card card-accent-green">
          <div className="card-header">Current Amount</div>
          <div className="card-value">₹{currentVal.toLocaleString()}</div>
        </div>

        <div className="card" style={{ borderLeft: `5px solid ${calculatedGap === 0 ? '#10b981' : '#ef4444'}` }}>
          <div className="card-header">Deficit / Gap</div>
          <div className="card-value" style={{ color: calculatedGap === 0 ? '#10b981' : '#ef4444' }}>
            ₹{calculatedGap.toLocaleString()}
          </div>
        </div>

        <div className="card" style={{ borderLeft: `5px solid ${statusColor}` }}>
          <div className="card-header">Reserve Health status</div>
          <div className="card-value" style={{ color: statusColor }}>
            {calculatedStatus} <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>({calculatedRatio.toFixed(1)}x)</span>
          </div>
        </div>
      </div>

      {/* Progress health meter */}
      <div className="card" style={{ marginTop: '24px', padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '8px' }}>Fund Progress Gauge</h3>
        <div className="progress-bar-container" style={{ height: '24px' }}>
          <div 
            className="progress-bar-fill" 
            style={{ width: `${percentAchieved}%`, backgroundColor: statusColor, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffffff', fontSize: '0.8rem', fontWeight: 'bold' }}
          >
            {percentAchieved.toFixed(1)}% Achieved
          </div>
        </div>
      </div>

      {/* Suggestion box */}
      <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginTop: '40px', marginBottom: '16px' }}>Top-up Suggestions</h3>
      {calculatedGap <= 0 ? (
        <div className="card" style={{ borderLeft: '4px solid #10b981', color: '#10b981' }}>
          🎉 Your emergency fund is fully capitalized! Keep this sum liquid in low-risk savings or flexi-FDs.
        </div>
      ) : (
        <div>
          <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <div className="card" style={{ borderTop: '4px solid #ef4444', textAlign: 'center' }}>
              <div className="card-header">Reach in 6 Months</div>
              <div className="card-value">₹{(calculatedGap / 6).toLocaleString(undefined, { maximumFractionDigits: 0 })} <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>/mo</span></div>
            </div>
            <div className="card" style={{ borderTop: '4px solid #f59e0b', textAlign: 'center' }}>
              <div className="card-header">Reach in 12 Months</div>
              <div className="card-value">₹{(calculatedGap / 12).toLocaleString(undefined, { maximumFractionDigits: 0 })} <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>/mo</span></div>
            </div>
            <div className="card" style={{ borderTop: '4px solid #10b981', textAlign: 'center' }}>
              <div className="card-header">Reach in 24 Months</div>
              <div className="card-value">₹{(calculatedGap / 24).toLocaleString(undefined, { maximumFractionDigits: 0 })} <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>/mo</span></div>
            </div>
          </div>

          <div className="card" style={{ borderLeft: '4px solid #f59e0b', marginTop: '24px' }}>
            💡 <b>Strategic Recommendation</b>: Establish an automated standing instruction of <b>₹{(calculatedGap / 12).toLocaleString(undefined, { maximumFractionDigits: 0 })}/month</b>. 
            This safely bridges your security buffer gap in 1 year without compromising immediate liquidity requirements.
          </div>
        </div>
      )}
    </div>
  );
}
