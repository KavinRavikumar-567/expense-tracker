import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function Dashboard({ user }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getDashboard()
      .then(res => {
        setData(res);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading dashboard...</div>;
  if (error) return <div className="text-red">Error loading dashboard: {error}</div>;
  if (!data) return <div>No dashboard data found.</div>;

  const currentMonthName = new Date().toLocaleString('default', { month: 'long', year: 'numeric' });

  // Prepare chart data
  const chartData = [
    {
      name: currentMonthName,
      Income: data.monthly_income,
      Expense: data.monthly_expenses
    }
  ];

  return (
    <div>
      <h2 className="section-title">Welcome back, {user.name}!</h2>
      <p className="section-subtitle">Here is your {user.mode}-level financial overview for this month.</p>

      {/* KPI Grid */}
      <div className="card-grid">
        <div className="card card-accent-green">
          <div className="card-header">Income vs Expense</div>
          <div className="card-value">₹{data.monthly_income.toLocaleString()} <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>/ ₹{data.monthly_expenses.toLocaleString()}</span></div>
          <div className="card-subtext">This Month ({currentMonthName})</div>
        </div>

        <div className="card" style={{ borderLeft: `5px solid ${data.net_savings >= 0 ? '#10b981' : '#ef4444'}` }}>
          <div className="card-header">Net Savings</div>
          <div className="card-value" style={{ color: data.net_savings >= 0 ? '#10b981' : '#ef4444' }}>
            ₹{data.net_savings.toLocaleString()}
          </div>
          <div className="card-subtext">Cash surplus after expenses</div>
        </div>

        {data.emergency_fund && (
          <div className="card" style={{ borderLeft: `5px solid ${data.emergency_fund.status === 'Healthy' ? '#10b981' : (data.emergency_fund.status === 'Building' ? '#f59e0b' : '#ef4444')}` }}>
            <div className="card-header">Emergency Fund</div>
            <div className="card-value">₹{data.emergency_fund.current_amount.toLocaleString()}</div>
            <div className="card-subtext">Multiplier: {data.emergency_fund.ratio.toFixed(1)}x expenses ({data.emergency_fund.status})</div>
          </div>
        )}

        <div className="card card-accent-gold">
          <div className="card-header">Investments Valued</div>
          <div className="card-value">₹{data.investments.total_current.toLocaleString()}</div>
          <div className="card-subtext" style={{ color: data.investments.absolute_returns >= 0 ? '#10b981' : '#ef4444' }}>
            Gains: ₹{data.investments.absolute_returns.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Columns: Insights and Small Tables */}
      <div className="dashboard-columns">
        {/* Left Column: Insights */}
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>🧠 Smart Insights & Alerts</h3>
          {data.insights.length === 0 ? (
            <div className="card">No insights generated yet. Add transactions or goals to populate insights.</div>
          ) : (
            <div className="alert-list">
              {data.insights.map((item, idx) => {
                let borderCol = '#10b981';
                if (item.level === 'Critical') borderCol = '#ef4444';
                else if (item.level === 'Warning') borderCol = '#f59e0b';
                else if (item.level === 'Info') borderCol = '#3b82f6';

                return (
                  <div key={idx} className="alert-item" style={{ borderLeft: `4px solid ${borderCol}` }}>
                    <span className="alert-category" style={{ color: borderCol }}>{item.category}</span>
                    <div className="alert-message">{item.message}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Budgets & Recents */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>📊 Budget Overview</h3>
            <div className="card" style={{ borderLeft: '4px solid #3b82f6' }}>
              <h5 style={{ fontWeight: 600, marginBottom: '6px' }}>Monthly Budget Progress</h5>
              {data.budget_summary.total_budgets_defined === 0 ? (
                <p className="card-subtext">No budgets defined for this month yet.</p>
              ) : (
                <div>
                  <p style={{ fontSize: '1.1rem', fontWeight: 'bold', marginBottom: '8px' }}>
                    {data.budget_summary.safe} Safe | {data.budget_summary.warning} Warning | {data.budget_summary.over} Over
                  </p>
                  <p className="card-subtext">Values calculated across defined monthly categories.</p>
                </div>
              )}
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>💸 Recent Activity</h3>
            {data.recent_transactions.length === 0 ? (
              <div className="card">No transactions recorded yet.</div>
            ) : (
              <div className="table-container" style={{ margin: 0 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Category</th>
                      <th>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_transactions.map((tx) => (
                      <tr key={tx.id}>
                        <td>{tx.member_name}</td>
                        <td>{tx.category}</td>
                        <td className={tx.type === 'Income' ? 'text-green' : 'text-red'}>
                          {tx.type === 'Income' ? '+' : '-'}₹{tx.amount.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bar Chart at bottom */}
      <div className="card" style={{ marginTop: '32px', padding: '24px' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>📊 Cashflow Chart</h3>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="name" stroke="#7c7b77" />
              <YAxis stroke="#7c7b77" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#ffffff', borderColor: 'rgba(55, 53, 47, 0.12)', color: '#37352f', borderRadius: '8px' }}
                cursor={{ fill: 'rgba(0, 0, 0, 0.02)' }}
              />
              <Legend />
              <Bar dataKey="Income" fill="#0f766e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Expense" fill="#991b1b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
