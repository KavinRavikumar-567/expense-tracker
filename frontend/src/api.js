const API_BASE = '/api';

async function request(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  
  const userJson = sessionStorage.getItem('user');
  if (userJson) {
    try {
      const user = JSON.parse(userJson);
      if (user && user.id) {
        headers['X-User-Id'] = user.id.toString();
      }
    } catch (e) {
      console.error("Failed to parse user session", e);
    }
  }

  const res = await fetch(url, { ...options, headers });
  
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  
  if (res.status === 204) return null;
  return res.json().catch(() => null);
}

export const api = {
  getUser: () => request(`${API_BASE}/user`),
  signup: (payload) => request(`${API_BASE}/signup`, { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => request(`${API_BASE}/login`, { method: 'POST', body: JSON.stringify(payload) }),
  
  getMembers: () => request(`${API_BASE}/members`),
  addMember: (member) => request(`${API_BASE}/members`, { method: 'POST', body: JSON.stringify(member) }),
  deleteMember: (id) => request(`${API_BASE}/members/${id}`, { method: 'DELETE' }),
  
  getTransactions: () => request(`${API_BASE}/transactions`),
  addTransaction: (tx) => request(`${API_BASE}/transactions`, { method: 'POST', body: JSON.stringify(tx) }),
  deleteTransaction: (id) => request(`${API_BASE}/transactions/${id}`, { method: 'DELETE' }),
  
  getBudgets: (month) => request(`${API_BASE}/budgets?month=${month}`),
  setBudget: (budget) => request(`${API_BASE}/budgets`, { method: 'POST', body: JSON.stringify(budget) }),
  deleteBudget: (id) => request(`${API_BASE}/budgets/${id}`, { method: 'DELETE' }),
  
  getGoals: () => request(`${API_BASE}/goals`),
  createGoal: (goal) => request(`${API_BASE}/goals`, { method: 'POST', body: JSON.stringify(goal) }),
  updateGoalProgress: (id, savedAmount) => request(`${API_BASE}/goals/${id}`, { method: 'PUT', body: JSON.stringify({ saved_amount: savedAmount }) }),
  deleteGoal: (id) => request(`${API_BASE}/goals/${id}`, { method: 'DELETE' }),
  
  getInvestments: () => request(`${API_BASE}/investments`),
  addInvestment: (inv) => request(`${API_BASE}/investments`, { method: 'POST', body: JSON.stringify(inv) }),
  updateInvestmentValuation: (id, currentVal) => request(`${API_BASE}/investments/${id}`, { method: 'PUT', body: JSON.stringify({ current_value: currentVal }) }),
  deleteInvestment: (id) => request(`${API_BASE}/investments/${id}`, { method: 'DELETE' }),
  
  getInsurance: () => request(`${API_BASE}/insurance`),
  addInsurance: (ins) => request(`${API_BASE}/insurance`, { method: 'POST', body: JSON.stringify(ins) }),
  deleteInsurance: (id) => request(`${API_BASE}/insurance/${id}`, { method: 'DELETE' }),
  
  getEmergencyFund: () => request(`${API_BASE}/emergency-fund`),
  updateEmergencyFund: (amount) => request(`${API_BASE}/emergency-fund`, { method: 'POST', body: JSON.stringify({ current_amount: amount }) }),
  
  getInsights: () => request(`${API_BASE}/insights`),
  getDashboard: () => request(`${API_BASE}/dashboard`),
};
