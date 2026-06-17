import React, { useEffect, useState } from 'react';
import { api } from '../api';

export default function Goals() {
  const [members, setMembers] = useState([]);
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);

  // Form states
  const [nameDetail, setNameDetail] = useState('');
  const [goalCat, setGoalCat] = useState('Education');
  const [targetAmount, setTargetAmount] = useState('');
  const [savedAmount, setSavedAmount] = useState('');
  const [monthlyContribution, setMonthlyContribution] = useState('');
  const [deadline, setDeadline] = useState(new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().split('T')[0]);
  const [assigneeId, setAssigneeId] = useState('Family'); // 'Family' or member_id
  const [submitting, setSubmitting] = useState(false);

  // Inline editing state
  const [editingGoalId, setEditingGoalId] = useState(null);
  const [editingValue, setEditingValue] = useState('');

  const fetchData = async () => {
    try {
      const [mList, gList] = await Promise.all([
        api.getMembers(),
        api.getGoals()
      ]);
      setMembers(mList);
      setGoals(gList);
      setLoading(false);
    } catch (err) {
      alert("Error loading goals data: " + err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!targetAmount) return;

    setSubmitting(true);
    const memberIdVal = assigneeId === 'Family' ? null : parseInt(assigneeId);
    const goalName = nameDetail.trim() ? `${goalCat}: ${nameDetail.trim()}` : goalCat;

    api.createGoal({
      member_id: memberIdVal,
      name: goalName,
      target_amount: parseFloat(targetAmount),
      saved_amount: parseFloat(savedAmount || 0),
      monthly_contribution: parseFloat(monthlyContribution || 0),
      deadline
    })
      .then(() => {
        setNameDetail('');
        setTargetAmount('');
        setSavedAmount('');
        setMonthlyContribution('');
        setSubmitting(false);
        fetchData();
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleUpdateSavings = (id, currentVal) => {
    const val = parseFloat(editingValue);
    if (isNaN(val) || val < 0 || val > currentVal.target_amount) {
      alert("Please enter a valid savings amount.");
      return;
    }

    api.updateGoalProgress(id, val)
      .then(() => {
        setEditingGoalId(null);
        setEditingValue('');
        fetchData();
      })
      .catch(err => alert(err.message));
  };

  const handleDelete = (id) => {
    if (window.confirm("Are you sure you want to delete this savings goal?")) {
      api.deleteGoal(id)
        .then(() => fetchData())
        .catch(err => alert(err.message));
    }
  };

  const calculateGoalDetails = (g) => {
    const target = g.target_amount;
    const saved = g.saved_amount;
    const monthly = g.monthly_contribution;
    const deadlineStr = g.deadline;

    const percent = target > 0 ? (saved / target * 100) : 0;
    const pctClamped = Math.min(100, percent);

    let monthsRem = null;
    let projectedCompletion = "Never (increase contribution)";

    if (saved >= target) {
      monthsRem = 0;
      projectedCompletion = "Completed";
    } else if (monthly > 0) {
      const remaining = target - saved;
      monthsRem = remaining / monthly;

      const today = new Date();
      const totalMonths = today.getMonth() + Math.round(monthsRem);
      const newMonth = (totalMonths % 12);
      const newYear = today.getFullYear() + Math.floor(totalMonths / 12);
      
      const monthsArr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      projectedCompletion = `${monthsArr[newMonth]} ${newYear}`;
    }

    // Determine status (On Track / Delayed / Completed / Unfunded)
    let status = 'On Track';
    let statusColor = '#10b981';

    if (saved >= target) {
      status = 'Completed';
      statusColor = '#10b981';
    } else if (monthly <= 0) {
      status = 'Unfunded';
      statusColor = '#ef4444';
    } else {
      try {
        const dlDate = new Date(deadlineStr);
        const today = new Date();
        const monthsToDl = (dlDate.getFullYear() - today.getFullYear()) * 12 + (dlDate.getMonth() - today.getMonth());
        
        if (monthsRem !== null && monthsRem <= monthsToDl) {
          status = 'On Track';
          statusColor = '#10b981';
        } else {
          status = 'Delayed';
          statusColor = '#f59e0b';
        }
      } catch (err) {
        status = 'N/A';
        statusColor = '#94a3b8';
      }
    }

    return {
      percent: pctClamped,
      monthsRemaining: monthsRem,
      projectedCompletion,
      status,
      statusColor
    };
  };

  if (loading) return <div>Loading goals...</div>;

  return (
    <div>
      <h2 className="section-title">Savings Goal Tracker</h2>
      <p className="section-subtitle">Define long-term savings goals, assign them to members, and check projected timelines.</p>

      {/* Grid: Left is goals list, Right is add goal form */}
      <div className="dashboard-columns">
        {/* Active Goals List */}
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>🎯 Active Goals</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {goals.map(g => {
              const details = calculateGoalDetails(g);
              const isEditing = editingGoalId === g.id;

              return (
                <div key={g.id} className="card" style={{ borderLeft: `5px solid ${details.statusColor}`, padding: '20px' }}>
                  <div className="flex-between" style={{ marginBottom: '8px' }}>
                    <h4 style={{ fontWeight: 'bold', fontSize: '1.05rem', margin: 0 }}>
                      {g.name}
                      <span className="badge badge-gray" style={{ marginLeft: '8px' }}>{g.member_name}</span>
                    </h4>
                    <span className="badge" style={{ backgroundColor: `${details.statusColor}22`, color: details.statusColor, border: `1px solid ${details.statusColor}44`, fontWeight: 'bold' }}>
                      {details.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                    Target: <b>₹{g.target_amount.toLocaleString()}</b> &nbsp;|&nbsp; 
                    Saved: <b>₹{g.saved_amount.toLocaleString()}</b> &nbsp;|&nbsp; 
                    Monthly: <b>₹{g.monthly_contribution.toLocaleString()}/mo</b>
                  </div>

                  {/* Progress bar */}
                  <div className="progress-bar-container">
                    <div className="progress-bar-fill" style={{ width: `${details.percent}%`, backgroundColor: details.statusColor }}></div>
                  </div>

                  <div className="flex-between" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
                    <span>{details.percent.toFixed(1)}% Saved</span>
                    <span>Deadline: {new Date(g.deadline).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--bg-border)' }}>
                    <div style={{ fontSize: '0.85rem' }}>
                      📅 Projected Completion: <b>{details.projectedCompletion}</b>
                      {details.monthsRemaining > 0 && ` (~${details.monthsRemaining.toFixed(1)} months)`}
                    </div>

                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      {isEditing ? (
                        <>
                          <input 
                            type="number" 
                            placeholder="Saved ₹" 
                            value={editingValue} 
                            onChange={e => setEditingValue(e.target.value)} 
                            style={{ padding: '4px 8px', width: '90px', fontSize: '0.8rem' }}
                          />
                          <button className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => handleUpdateSavings(g.id, g)}>
                            Save
                          </button>
                          <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => setEditingGoalId(null)}>
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '6px 12px', fontSize: '0.8rem' }} 
                            onClick={() => {
                              setEditingGoalId(g.id);
                              setEditingValue(g.saved_amount.toString());
                            }}
                          >
                            Update Saved
                          </button>
                          <button className="btn btn-danger" style={{ padding: '6px 12px', fontSize: '0.8rem' }} onClick={() => handleDelete(g.id)}>
                            Delete
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {goals.length === 0 && (
              <div className="card">No goals set yet. Set a goal in the form on the right.</div>
            )}
          </div>
        </div>

        {/* Create Goal Form */}
        <div>
          <div className="form-container" style={{ maxWidth: 'none' }}>
            <h3 className="form-title">Create New Goal</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Goal Category</label>
                <select value={goalCat} onChange={e => setGoalCat(e.target.value)}>
                  <option value="Education">Education</option>
                  <option value="Home">Home</option>
                  <option value="Vehicle">Vehicle</option>
                  <option value="Vacation">Vacation</option>
                  <option value="Emergency">Emergency</option>
                  <option value="Custom">Custom</option>
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Goal Details / Name</label>
                <input type="text" value={nameDetail} onChange={e => setNameDetail(e.target.value)} placeholder="E.g., Ravi's MBA College Fund" required />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Target Amount (₹)</label>
                <input type="number" min="1" value={targetAmount} onChange={e => setTargetAmount(e.target.value)} placeholder="E.g., 200000" required />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Initial Saved Amount (₹)</label>
                <input type="number" min="0" value={savedAmount} onChange={e => setSavedAmount(e.target.value)} placeholder="E.g., 50000" />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Monthly Contribution (₹)</label>
                <input type="number" min="0" value={monthlyContribution} onChange={e => setMonthlyContribution(e.target.value)} placeholder="E.g., 5000" />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Target Deadline</label>
                <input type="date" value={deadline} onChange={e => setDeadline(e.target.value)} required />
              </div>

              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label>Assign Goal To</label>
                <select value={assigneeId} onChange={e => setAssigneeId(e.target.value)}>
                  <option value="Family">Family (Combined)</option>
                  {members.map(m => (
                    <option key={m.id} value={m.id.toString()}>{m.name}</option>
                  ))}
                </select>
              </div>

              <button type="submit" className="btn btn-primary btn-full">
                Create Goal
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
