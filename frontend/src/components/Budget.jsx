import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const CATEGORIES = ["Food", "Rent", "EMI", "Education", "Medical", "Travel", "Entertainment", "Utilities", "Other"];

export default function Budget() {
  const [members, setMembers] = useState([]);
  const [budgets, setBudgets] = useState([]);
  const [actualExpenses, setActualExpenses] = useState([]);
  
  // Settings
  const [month, setMonth] = useState(new Date().toISOString().substring(0, 7)); // YYYY-MM
  const [viewLevel, setViewLevel] = useState('Family'); // Family or Individual
  const [selectedMemberId, setSelectedMemberId] = useState('');
  
  // Form input
  const [assigneeId, setAssigneeId] = useState('Family'); // 'Family' or member_id
  const [category, setCategory] = useState('Food');
  const [limitAmount, setLimitAmount] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchBudgetData = async () => {
    try {
      const [mList, bList, aList] = await Promise.all([
        api.getMembers(),
        api.getBudgets(month),
        // We calculate actual expenses by loading transactions filtered by month.
        // Wait, backend has an endpoint for actual expenses grouped by category:
        // Or we can just calculate them from transactions list on frontend!
        // To be extremely clean and consistent with Streamlit, let's load all transactions and do the grouping on frontend!
        api.getTransactions()
      ]);
      
      setMembers(mList);
      setBudgets(bList);
      
      // Filter transactions by expense type and month
      const currentTxs = aList.filter(t => t.type === 'Expense' && t.date.substring(0, 7) === month);
      setActualExpenses(currentTxs);
      
      if (mList.length > 0 && !selectedMemberId) {
        setSelectedMemberId(mList[0].id.toString());
      }
      
      setLoading(false);
    } catch (err) {
      alert("Error loading budget data: " + err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBudgetData();
  }, [month]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!limitAmount) return;

    setSubmitting(true);
    const memberIdVal = assigneeId === 'Family' ? null : parseInt(assigneeId);
    
    api.setBudget({
      member_id: memberIdVal,
      month,
      category,
      limit_amount: parseFloat(limitAmount)
    })
      .then(() => {
        setLimitAmount('');
        setSubmitting(false);
        fetchBudgetData();
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleDeleteBudget = (id) => {
    if (window.confirm("Are you sure you want to delete this budget limit?")) {
      api.deleteBudget(id)
        .then(() => fetchBudgetData())
        .catch(err => alert(err.message));
    }
  };

  // Compile comparison data
  const comparisonRows = CATEGORIES.map(cat => {
    let limit = 0;
    let actual = 0;
    
    if (viewLevel === 'Family') {
      // Limit = sum of budgets for this category where member_id is NULL
      // Or if no family-wide budget, sum member-level budgets.
      const familyWide = budgets.find(b => b.category === cat && b.member_id === null);
      if (familyWide) {
        limit = familyWide.limit_amount;
      } else {
        limit = budgets.filter(b => b.category === cat && b.member_id !== null).reduce((sum, b) => sum + b.limit_amount, 0);
      }
      
      actual = actualExpenses.filter(t => t.category === cat).reduce((sum, t) => sum + t.amount, 0);
    } else {
      // Individual Level
      const mId = parseInt(selectedMemberId);
      const indBudget = budgets.find(b => b.category === cat && b.member_id === mId);
      limit = indBudget ? indBudget.limit_amount : 0;
      
      actual = actualExpenses.filter(t => t.category === cat && t.member_id === mId).reduce((sum, t) => sum + t.amount, 0);
    }
    
    const remaining = limit - actual;
    const pctUsed = limit > 0 ? (actual / limit * 100) : (actual > 0 ? Infinity : 0);
    
    let status = 'N/A';
    if (limit > 0) {
      if (pctUsed < 80) status = 'Safe';
      else if (pctUsed <= 100) status = 'Near Limit';
      else status = 'Over Budget';
    } else if (actual > 0) {
      status = 'Unbudgeted';
    }
    
    return {
      category: cat,
      limit,
      actual,
      remaining,
      pctUsed,
      status
    };
  });

  const chartData = comparisonRows.filter(r => r.limit > 0 || r.actual > 0).map(r => ({
    Category: r.category,
    Budget: r.limit,
    Actual: r.actual
  }));

  if (loading) return <div>Loading budgets...</div>;

  return (
    <div>
      <h2 className="section-title">Monthly Budget Planner</h2>
      <p className="section-subtitle">Define category-wise spending limits and compare allocations with real-time expenses.</p>

      {/* Inputs Header: Month picker */}
      <div style={{ display: 'flex', gap: '20px', alignItems: 'center', marginBottom: '24px' }}>
        <div className="form-group" style={{ width: '220px' }}>
          <label>Active Budget Month</label>
          <input type="month" value={month} onChange={e => setMonth(e.target.value)} required />
        </div>
      </div>

      <div className="tabs-header">
        <button className="tab-btn active">📊 Budget Overview</button>
      </div>

      <div className="dashboard-columns">
        {/* Left Column: Set Budget Form & Existing Budgets List */}
        <div>
          <div className="form-container" style={{ maxWidth: 'none' }}>
            <h3 className="form-title">Set Budget Limits for {month}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Assign To</label>
                  <select value={assigneeId} onChange={e => setAssigneeId(e.target.value)}>
                    <option value="Family">Family (Combined)</option>
                    {members.map(m => (
                      <option key={m.id} value={m.id.toString()}>{m.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Category</label>
                  <select value={category} onChange={e => setCategory(e.target.value)}>
                    {CATEGORIES.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>Limit Amount (₹)</label>
                  <input type="number" min="0" value={limitAmount} onChange={e => setLimitAmount(e.target.value)} placeholder="E.g., 5000" required />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Saving...' : 'Save Budget'}
              </button>
            </form>
          </div>

          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>Configured Budgets ({month})</h3>
          {budgets.length === 0 ? (
            <div className="card">No budget limits set for this month yet.</div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Assigned To</th>
                    <th>Category</th>
                    <th>Limit</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {budgets.map(b => (
                    <tr key={b.id}>
                      <td>{b.member_name}</td>
                      <td>{b.category}</td>
                      <td style={{ fontWeight: 'bold' }}>₹{b.limit_amount.toLocaleString()}</td>
                      <td>
                        <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleDeleteBudget(b.id)}>
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

        {/* Right Column: Comparative Analysis */}
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>Analysis Settings</h3>
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="form-group" style={{ marginBottom: '12px' }}>
              <label>View Level</label>
              <select value={viewLevel} onChange={e => setViewLevel(e.target.value)}>
                <option value="Family">Family Level (Combined)</option>
                <option value="Individual">Individual Member Level</option>
              </select>
            </div>
            
            {viewLevel === 'Individual' && (
              <div className="form-group">
                <label>Select Member</label>
                <select value={selectedMemberId} onChange={e => setSelectedMemberId(e.target.value)}>
                  {members.map(m => (
                    <option key={m.id} value={m.id.toString()}>{m.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Cards with progress bars */}
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>Budget Progress</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {comparisonRows.filter(r => r.limit > 0 || r.actual > 0).map((row, idx) => {
              let statusColor = '#10b981';
              if (row.status === 'Over Budget' || row.status === 'Unbudgeted') statusColor = '#ef4444';
              else if (row.status === 'Near Limit') statusColor = '#f59e0b';
              
              const percent = Math.min(100, row.pctUsed);

              return (
                <div key={idx} className="card" style={{ borderLeft: `5px solid ${statusColor}`, padding: '16px' }}>
                  <div className="flex-between" style={{ marginBottom: '6px' }}>
                    <span style={{ fontWeight: 'bold' }}>{row.category}</span>
                    <span className="badge" style={{ backgroundColor: `${statusColor}22`, color: statusColor, border: `1px solid ${statusColor}44` }}>
                      {row.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                    Spent: <b>₹{row.actual.toLocaleString()}</b> / ₹{row.limit.toLocaleString()}
                  </div>
                  {row.limit > 0 && (
                    <>
                      <div className="progress-bar-container">
                        <div className="progress-bar-fill" style={{ width: `${percent}%`, backgroundColor: statusColor }}></div>
                      </div>
                      <div className="flex-between" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        <span>{row.pctUsed.toFixed(1)}% Used</span>
                        <span>Remaining: ₹{row.remaining.toLocaleString()}</span>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
            
            {comparisonRows.filter(r => r.limit > 0 || r.actual > 0).length === 0 && (
              <div className="card">No limits or transactions to display for this month.</div>
            )}
          </div>
        </div>
      </div>

      {/* Comparison Chart */}
      {chartData.length > 0 && (
        <div className="card" style={{ marginTop: '32px', padding: '24px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>📊 Actual vs Budget Chart</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="Category" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }} />
                <Legend />
                <Bar dataKey="Budget" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Actual" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
