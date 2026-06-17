import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

const CATEGORIES = ["Food", "Rent", "EMI", "Education", "Medical", "Travel", "Entertainment", "Utilities", "Other"];
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AF19FF', '#FF19A3', '#19FFD8', '#FF7F50', '#808080'];

export default function Tracker() {
  const [members, setMembers] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Form states
  const [memberId, setMemberId] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [type, setType] = useState('Expense');
  const [category, setCategory] = useState('Food');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Filter states
  const [filterMember, setFilterMember] = useState('All');
  const [filterType, setFilterType] = useState('All');
  const [filterCategory, setFilterCategory] = useState('All');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const fetchData = async () => {
    try {
      const [membersList, txList] = await Promise.all([
        api.getMembers(),
        api.getTransactions()
      ]);
      setMembers(membersList);
      setTransactions(txList);
      if (membersList.length > 0 && !memberId) {
        setMemberId(membersList[0].id);
      }
      setLoading(false);
    } catch (err) {
      alert("Error loading tracker data: " + err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!memberId || !amount) return;

    setSubmitting(true);
    api.addTransaction({
      member_id: parseInt(memberId),
      date,
      type,
      category,
      amount: parseFloat(amount),
      note: note.trim()
    })
      .then(() => {
        setAmount('');
        setNote('');
        setSubmitting(false);
        fetchData();
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleDelete = (id) => {
    if (window.confirm("Are you sure you want to delete this transaction?")) {
      api.deleteTransaction(id)
        .then(() => fetchData())
        .catch(err => alert(err.message));
    }
  };

  // Filter transactions
  const filteredTxs = transactions.filter(t => {
    if (filterMember !== 'All' && t.member_name !== filterMember) return false;
    if (filterType !== 'All' && t.type !== filterType) return false;
    if (filterCategory !== 'All' && t.category !== filterCategory) return false;
    if (startDate && t.date < startDate) return false;
    if (endDate && t.date > endDate) return false;
    return true;
  });

  // Calculate totals
  const totalIncome = filteredTxs.filter(t => t.type === 'Income').reduce((sum, t) => sum + t.amount, 0);
  const totalExpense = filteredTxs.filter(t => t.type === 'Expense').reduce((sum, t) => sum + t.amount, 0);
  const netSavings = totalIncome - totalExpense;

  // Prepare Pie Chart data (Expenses by category)
  const expenseTxs = filteredTxs.filter(t => t.type === 'Expense');
  const catSums = {};
  expenseTxs.forEach(t => {
    catSums[t.category] = (catSums[t.category] || 0) + t.amount;
  });

  const pieData = Object.keys(catSums).map(cat => ({
    name: cat,
    value: catSums[cat]
  }));

  if (loading) return <div>Loading tracker...</div>;

  return (
    <div>
      <h2 className="section-title">Income & Expense Tracker</h2>
      <p className="section-subtitle">Record and analyze family cashflows with interactive trend summaries.</p>

      {/* Quick Setup / Add Form */}
      <div className="form-container">
        <h3 className="form-title">Record Transaction</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label>Family Member</label>
              <select value={memberId} onChange={e => setMemberId(e.target.value)} required>
                {members.map(m => (
                  <option key={m.id} value={m.id}>{m.name} ({m.relationship})</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Type</label>
              <select value={type} onChange={e => setType(e.target.value)}>
                <option value="Expense">Expense</option>
                <option value="Income">Income</option>
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
              <label>Amount (₹)</label>
              <input type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} required />
            </div>

            <div className="form-group">
              <label>Date</label>
              <input type="date" value={date} onChange={e => setDate(e.target.value)} required />
            </div>

            <div className="form-group">
              <label>Note / Description</label>
              <input type="text" value={note} onChange={e => setNote(e.target.value)} placeholder="Grocery run, salary bonus..." />
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Recording...' : 'Add Transaction'}
          </button>
        </form>
      </div>

      {/* Filters */}
      <div className="form-container" style={{ maxWidth: 'none' }}>
        <h3 className="form-title">🔍 Filter Ledger</h3>
        <div className="form-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
          <div className="form-group">
            <label>Member</label>
            <select value={filterMember} onChange={e => setFilterMember(e.target.value)}>
              <option value="All">All Members</option>
              {members.map(m => (
                <option key={m.id} value={m.name}>{m.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Type</label>
            <select value={filterType} onChange={e => setFilterType(e.target.value)}>
              <option value="All">All Types</option>
              <option value="Expense">Expense</option>
              <option value="Income">Income</option>
            </select>
          </div>

          <div className="form-group">
            <label>Category</label>
            <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}>
              <option value="All">All Categories</option>
              {CATEGORIES.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Start Date</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
          </div>

          <div className="form-group">
            <label>End Date</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
          </div>
        </div>
      </div>

      {/* KPI summary tiles */}
      <div className="card-grid">
        <div className="card card-accent-green">
          <div className="card-header">Filtered Income</div>
          <div className="card-value">₹{totalIncome.toLocaleString()}</div>
        </div>
        <div className="card card-accent-red">
          <div className="card-header">Filtered Expenses</div>
          <div className="card-value">₹{totalExpense.toLocaleString()}</div>
        </div>
        <div className="card" style={{ borderLeft: `5px solid ${netSavings >= 0 ? '#10b981' : '#ef4444'}` }}>
          <div className="card-header">Filtered Net Savings</div>
          <div className="card-value" style={{ color: netSavings >= 0 ? '#10b981' : '#ef4444' }}>
            ₹{netSavings.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Two Columns: Pie chart & Log List */}
      <div className="dashboard-columns">
        {/* Table list */}
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>💸 Ledger Logs</h3>
          {filteredTxs.length === 0 ? (
            <div className="card">No transactions matching current filters.</div>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Member</th>
                    <th>Category</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Note</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTxs.map(t => (
                    <tr key={t.id}>
                      <td>{t.date}</td>
                      <td>{t.member_name}</td>
                      <td>{t.category}</td>
                      <td>
                        <span className={`badge ${t.type === 'Income' ? 'badge-green' : 'badge-red'}`}>{t.type}</span>
                      </td>
                      <td style={{ fontWeight: 'bold' }}>₹{t.amount.toLocaleString()}</td>
                      <td>{t.note || '-'}</td>
                      <td>
                        <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleDelete(t.id)}>
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

        {/* Expense share Chart */}
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px' }}>📊 Expense Categories</h3>
          {pieData.length === 0 ? (
            <div className="card">No expense data found in current filters to display breakdown.</div>
          ) : (
            <div className="card" style={{ height: 320, padding: 12 }}>
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
        </div>
      </div>
    </div>
  );
}
