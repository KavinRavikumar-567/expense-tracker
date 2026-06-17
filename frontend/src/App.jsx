import React, { useEffect, useState } from 'react';
import { api } from './api';
import { 
  Home, 
  Users, 
  DollarSign, 
  BarChart2, 
  Target, 
  Briefcase, 
  Shield, 
  AlertTriangle,
  Menu,
  X,
  LogOut
} from 'lucide-react';

import Dashboard from './components/Dashboard';
import Members from './components/Members';
import Tracker from './components/Tracker';
import Budget from './components/Budget';
import Goals from './components/Goals';
import Investments from './components/Investments';
import Insurance from './components/Insurance';
import Emergency from './components/Emergency';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Auth States
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  
  // Signup Details State
  const [onboardName, setOnboardName] = useState('');
  const [onboardAge, setOnboardAge] = useState(25);
  const [onboardMode, setOnboardMode] = useState('Bachelor');
  const [onboardIncome, setOnboardIncome] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchUser = () => {
    const cachedUser = sessionStorage.getItem('user');
    if (cachedUser) {
      try {
        const parsed = JSON.parse(cachedUser);
        setUser(parsed);
        setLoading(false);
        return;
      } catch (e) {
        sessionStorage.removeItem('user');
      }
    }
    
    // Fallback double check with API using existing headers
    api.getUser()
      .then(res => {
        if (res) {
          setUser(res);
          sessionStorage.setItem('user', JSON.stringify(res));
        } else {
          setUser(null);
        }
        setLoading(false);
      })
      .catch(() => {
        setUser(null);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    if (!username.trim() || !password) return;

    setSubmitting(true);
    api.login({
      username: username.trim(),
      password
    })
      .then(res => {
        sessionStorage.setItem('user', JSON.stringify(res));
        setUser(res);
        setUsername('');
        setPassword('');
        setSubmitting(false);
        setActiveTab('dashboard');
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleSignupSubmit = (e) => {
    e.preventDefault();
    if (!username.trim() || !password || !onboardName.trim()) return;

    setSubmitting(true);
    api.signup({
      username: username.trim(),
      password,
      name: onboardName.trim(),
      age: parseInt(onboardAge),
      mode: onboardMode,
      monthly_income: parseFloat(onboardIncome || 0)
    })
      .then(() => {
        // Auto Login after successful signup
        api.login({
          username: username.trim(),
          password
        })
          .then(loginRes => {
            sessionStorage.setItem('user', JSON.stringify(loginRes));
            setUser(loginRes);
            setUsername('');
            setPassword('');
            setOnboardName('');
            setOnboardIncome('');
            setSubmitting(false);
            setActiveTab('dashboard');
          });
      })
      .catch(err => {
        alert(err.message);
        setSubmitting(false);
      });
  };

  const handleLogout = () => {
    if (window.confirm("Are you sure you want to log out of your session?")) {
      sessionStorage.removeItem('user');
      setUser(null);
      setActiveTab('dashboard');
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-dark)', color: 'var(--text-primary)' }}>
        <h2>Loading Finance Manager...</h2>
      </div>
    );
  }

  // 1. Authenticate Wizard (Login / Signup tab cards)
  if (!user) {
    return (
      <div className="onboarding-screen">
        <div className="onboarding-box">
          <h1 className="onboarding-title">Antigravity Finance</h1>
          <p className="onboarding-subtitle">Personal & Family Finance Portal</p>
          
          <div className="tabs-header" style={{ marginBottom: '24px' }}>
            <button 
              className={`tab-btn ${authMode === 'login' ? 'active' : ''}`} 
              onClick={() => setAuthMode('login')}
              style={{ width: '50%', textAlign: 'center' }}
            >
              Log In
            </button>
            <button 
              className={`tab-btn ${authMode === 'signup' ? 'active' : ''}`} 
              onClick={() => setAuthMode('signup')}
              style={{ width: '50%', textAlign: 'center' }}
            >
              Sign Up
            </button>
          </div>

          {authMode === 'login' ? (
            <form onSubmit={handleLoginSubmit}>
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Username</label>
                <input 
                  type="text" 
                  value={username} 
                  onChange={e => setUsername(e.target.value)} 
                  placeholder="Enter username" 
                  required 
                  style={{ width: '100%' }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label>Password</label>
                <input 
                  type="password" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  placeholder="Enter password" 
                  required 
                  style={{ width: '100%' }}
                />
              </div>

              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Authenticating...' : 'Sign In'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignupSubmit}>
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Choose Username</label>
                <input 
                  type="text" 
                  value={username} 
                  onChange={e => setUsername(e.target.value)} 
                  placeholder="E.g., ravis23" 
                  required 
                  style={{ width: '100%' }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Choose Password</label>
                <input 
                  type="password" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                  placeholder="Choose password" 
                  required 
                  style={{ width: '100%' }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Full Name</label>
                <input 
                  type="text" 
                  value={onboardName} 
                  onChange={e => setOnboardName(e.target.value)} 
                  placeholder="E.g., Ravi Sharma" 
                  required 
                  style={{ width: '100%' }}
                />
              </div>

              <div className="form-grid" style={{ marginBottom: '16px' }}>
                <div className="form-group">
                  <label>Age</label>
                  <input 
                    type="number" 
                    min="1" 
                    max="120" 
                    value={onboardAge} 
                    onChange={e => setOnboardAge(e.target.value)} 
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>Income (₹/mo)</label>
                  <input 
                    type="number" 
                    min="0" 
                    value={onboardIncome} 
                    onChange={e => setOnboardIncome(e.target.value)} 
                    placeholder="85000" 
                    required 
                  />
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label>Workspace Mode</label>
                <select value={onboardMode} onChange={e => setOnboardMode(e.target.value)} style={{ width: '100%' }}>
                  <option value="Bachelor">Bachelor Mode (Single, optional dependents)</option>
                  <option value="Family">Family Mode (Full household tracking)</option>
                </select>
              </div>

              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Registering...' : 'Register Profile'}
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  // 2. Main Portal Screen
  const renderTabContent = () => {
    switch (activeTab) {
      case 'dashboard': return <Dashboard user={user} />;
      case 'members': return <Members user={user} onUpdateUser={fetchUser} />;
      case 'tracker': return <Tracker />;
      case 'budget': return <Budget />;
      case 'goals': return <Goals />;
      case 'investments': return <Investments />;
      case 'insurance': return <Insurance />;
      case 'emergency': return <Emergency user={user} />;
      default: return <Dashboard user={user} />;
    }
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'members', label: 'Members & Profiles', icon: Users },
    { id: 'tracker', label: 'Ledger Tracker', icon: DollarSign },
    { id: 'budget', label: 'Budget Planner', icon: BarChart2 },
    { id: 'goals', label: 'Savings Goals', icon: Target },
    { id: 'investments', label: 'Investments', icon: Briefcase },
    { id: 'insurance', label: 'Insurance Manager', icon: Shield },
    { id: 'emergency', label: 'Emergency Fund', icon: AlertTriangle },
  ];

  return (
    <div className="app-layout">
      {/* Mobile Header Toggle */}
      <div 
        style={{ display: 'none', position: 'fixed', top: 12, left: 12, zIndex: 100, backgroundColor: 'var(--bg-card)', padding: '8px', borderRadius: '8px', cursor: 'pointer', border: '1px solid var(--bg-border)' }}
        className="mobile-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </div>

      {/* Sidebar Navigation */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <h2>Antigravity</h2>
          <span>{user.name} ({user.mode})</span>
        </div>
        
        <nav className="sidebar-nav">
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button 
                key={item.id} 
                onClick={() => {
                  setActiveTab(item.id);
                  setSidebarOpen(false);
                }} 
                className={`nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
          
          <button 
            onClick={handleLogout} 
            className="nav-item"
            style={{ marginTop: 'auto', borderTop: '1px solid var(--bg-border)', borderRadius: 0, color: 'var(--color-red)', fontWeight: '600' }}
          >
            <LogOut size={16} />
            Log Out
          </button>
        </nav>

        <div className="sidebar-footer">
          📅 Today: {new Date().toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
        </div>
      </aside>

      {/* Main Content Router */}
      <main className="main-content">
        {renderTabContent()}
      </main>
    </div>
  );
}
