import React, { useState, useEffect } from 'react';
import { Shield, LayoutDashboard, UploadCloud, Settings, User, Zap } from 'lucide-react';
import Dashboard from './components/Dashboard';
import Anonymizer from './components/Anonymizer';
import AdminConsole from './components/AdminConsole';
import FastConverter from './components/FastConverter';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [userId, setUserId] = useState('analyst_1');
  const [budget, setBudget] = useState(null);
  const [availableUsers, setAvailableUsers] = useState(['analyst_1', 'analyst_2', 'admin_1']);

  const fetchBudget = async () => {
    try {
      const res = await fetch(`/api/privacy/budget-status/${userId}/`);
      if (res.ok) {
        const data = await res.json();
        setBudget(data.epsilon_remaining);
      } else {
        // If user budget ledger doesn't exist, it is created automatically in Django on first view
        setBudget(10.0);
      }
    } catch (e) {
      console.error("Error fetching budget status:", e);
      setBudget(10.0);
    }
  };

  // Keep budget in sync when active userId changes
  useEffect(() => {
    fetchBudget();
  }, [userId]);

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard userId={userId} budget={budget} fetchBudget={fetchBudget} />;
      case 'anonymizer':
        return <Anonymizer userId={userId} />;
      case 'fast-converter':
        return <FastConverter />;
      case 'admin':
        return <AdminConsole userId={userId} fetchBudget={fetchBudget} />;
      default:
        return <Dashboard userId={userId} budget={budget} fetchBudget={fetchBudget} />;
    }
  };

  const getPageTitle = () => {
    switch (activeTab) {
      case 'dashboard': return { title: "System Analytics", sub: "Differential privacy telemetry and ledger activity logs" };
      case 'anonymizer': return { title: "Dataset Anonymizer", sub: "Load datasets locally, auto-classify sensitivity, and add noise protection" };
      case 'fast-converter': return { title: "Turbo FWF Converter", sub: "Convert fixed-width text files to CSV locally with on-the-fly anonymization" };
      case 'admin': return { title: "Administrative Control", sub: "Provision users, override ledgers, and manage security rules" };
      default: return { title: "System Analytics", sub: "Differential privacy telemetry and ledger activity logs" };
    }
  };

  const { title, sub } = getPageTitle();

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div className="logo-section">
          <div className="logo-icon">🛡️</div>
          <span className="logo-text">ShadowSafe</span>
        </div>

        <ul className="nav-list">
          <li 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard className="nav-icon" /> Dashboard
          </li>

          <li 
            className={`nav-item ${activeTab === 'anonymizer' ? 'active' : ''}`}
            onClick={() => setActiveTab('anonymizer')}
          >
            <UploadCloud className="nav-icon" /> Anonymizer
          </li>
          <li 
            className={`nav-item ${activeTab === 'fast-converter' ? 'active' : ''}`}
            onClick={() => setActiveTab('fast-converter')}
          >
            <Zap className="nav-icon" /> Turbo FWF
          </li>
          <li 
            className={`nav-item ${activeTab === 'admin' ? 'active' : ''}`}
            onClick={() => setActiveTab('admin')}
          >
            <Settings className="nav-icon" /> Admin Panel
          </li>
        </ul>

        {/* User Budget Widget */}
        <div className="user-widget">
          <div className="user-widget-title">Active Security Principal</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <User className="nav-icon" style={{ width: '16px', color: 'var(--text-secondary)' }} />
            <select 
              className="user-select" 
              value={userId} 
              onChange={(e) => setUserId(e.target.value)}
            >
              {availableUsers.map(u => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
          
          <div className="budget-pill">
            <span>Remaining Budget:</span>
            <span className="budget-val">{budget !== null ? `${budget.toFixed(2)} ε` : '10.00 ε'}</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        <div className="header-section">
          <div>
            <h1 className="page-title">{title}</h1>
            <p className="page-subtitle">{sub}</p>
          </div>
        </div>

        {renderContent()}
      </div>
    </div>
  );
}
