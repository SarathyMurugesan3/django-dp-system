import React, { useState } from 'react';
import { Settings, ShieldAlert, Users, Plus, Download, RefreshCcw, Trash2 } from 'lucide-react';

export default function AdminConsole({ userId, fetchBudget }) {
  // New User Form State
  const [newUserId, setNewUserId] = useState('');
  const [maxEpsilon, setMaxEpsilon] = useState(10.0);

  // New Team Form State
  const [teamName, setTeamName] = useState('');
  
  // Custom Budget Allocation State
  const [targetUserId, setTargetUserId] = useState(userId);
  const [customBudgetVal, setCustomBudgetVal] = useState(10.0);

  // Action status messages
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUserId) return;
    setLoading(true);
    setStatusMessage('');
    setErrorMessage('');

    try {
      const res = await fetch('/api/privacy/admin/create-user/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: newUserId,
          max_epsilon: parseFloat(maxEpsilon)
        })
      });

      if (res.ok) {
        setStatusMessage(`User "${newUserId}" created successfully with ${maxEpsilon} ε budget.`);
        setNewUserId('');
        fetchBudget();
      } else {
        const data = await res.json();
        setErrorMessage(data.error || "Failed to create user.");
      }
    } catch (err) {
      setErrorMessage("Network error.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!teamName) return;
    setLoading(true);
    setStatusMessage('');
    setErrorMessage('');

    try {
      const res = await fetch('/api/privacy/admin/create-team/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_name: teamName
        })
      });

      if (res.ok) {
        setStatusMessage(`Team "${teamName}" created successfully.`);
        setTeamName('');
      } else {
        const data = await res.json();
        setErrorMessage(data.error || "Failed to create team.");
      }
    } catch (err) {
      setErrorMessage("Network error.");
    } finally {
      setLoading(false);
    }
  };

  const handleSetCustomBudget = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatusMessage('');
    setErrorMessage('');

    try {
      const res = await fetch(`/api/privacy/admin/set-budget/${targetUserId}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epsilon_remaining: parseFloat(customBudgetVal)
        })
      });

      if (res.ok) {
        setStatusMessage(`Budget for user "${targetUserId}" set to ${customBudgetVal} ε.`);
        if (targetUserId === userId) {
          fetchBudget();
        }
      } else {
        const data = await res.json();
        setErrorMessage(data.error || "Failed to set budget.");
      }
    } catch (err) {
      setErrorMessage("Network error.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetAllBudgets = async () => {
    if (!window.confirm("Are you sure you want to reset ALL users' privacy budgets to maximum?")) return;
    setLoading(true);
    setStatusMessage('');
    setErrorMessage('');

    try {
      const res = await fetch('/api/privacy/admin/reset-all-budgets/', {
        method: 'POST'
      });

      if (res.ok) {
        setStatusMessage("All privacy budgets have been reset successfully.");
        fetchBudget();
      } else {
        setErrorMessage("Failed to reset budgets.");
      }
    } catch (err) {
      setErrorMessage("Network error.");
    } finally {
      setLoading(false);
    }
  };

  const handleExportAuditLogs = () => {
    window.open('/api/privacy/admin/export-audit-log/', '_blank');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {statusMessage && (
        <div style={{ padding: '16px', backgroundColor: 'var(--status-safe-glow)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: 'var(--radius-md)', color: 'var(--status-safe)' }}>
          {statusMessage}
        </div>
      )}

      {errorMessage && (
        <div style={{ padding: '16px', backgroundColor: 'var(--status-danger-glow)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-md)', color: 'var(--status-danger)' }}>
          {errorMessage}
        </div>
      )}

      <div className="layout-split">
        {/* User Creation Card */}
        <div className="card">
          <h3 className="card-title"><Users className="nav-icon" /> User Provisioning</h3>
          <p className="card-subtitle">Create new analytical user accounts and seed privacy budgets</p>

          <form onSubmit={handleCreateUser}>
            <div className="form-group">
              <label className="form-label">User Identifier ID</label>
              <input 
                type="text" 
                placeholder="e.g. analyst_john" 
                className="form-input" 
                value={newUserId}
                onChange={(e) => setNewUserId(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Max Budget Allowance (Epsilon - ε)</label>
              <input 
                type="number" 
                step="0.1" 
                className="form-input" 
                value={maxEpsilon}
                onChange={(e) => setMaxEpsilon(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              <Plus className="nav-icon" /> Provision User
            </button>
          </form>
        </div>

        {/* Budget Allocation Card */}
        <div className="card">
          <h3 className="card-title"><Settings className="nav-icon" /> Budget Override</h3>
          <p className="card-subtitle">Manually adjust remaining privacy allowances for individual users</p>

          <form onSubmit={handleSetCustomBudget}>
            <div className="form-group">
              <label className="form-label">Target User ID</label>
              <input 
                type="text" 
                className="form-input" 
                value={targetUserId}
                onChange={(e) => setTargetUserId(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Set Remaining Epsilon (ε)</label>
              <input 
                type="number" 
                step="0.1" 
                className="form-input" 
                value={customBudgetVal}
                onChange={(e) => setCustomBudgetVal(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-secondary" style={{ width: '100%' }} disabled={loading}>
              Save Override Settings
            </button>
          </form>
        </div>
      </div>

      <div className="layout-split">
        {/* Team Management */}
        <div className="card">
          <h3 className="card-title"><Users className="nav-icon" /> Team Provisioning</h3>
          <p className="card-subtitle">Group users into collaborative teams for budget sharing</p>

          <form onSubmit={handleCreateTeam}>
            <div className="form-group">
              <label className="form-label">Team Name</label>
              <input 
                type="text" 
                placeholder="e.g. data_science_team" 
                className="form-input" 
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
              <Plus className="nav-icon" /> Create Team
            </button>
          </form>
        </div>

        {/* System Administration / Maintenance */}
        <div className="card">
          <h3 className="card-title" style={{ color: 'var(--status-danger)' }}><ShieldAlert className="nav-icon" /> Danger Zone</h3>
          <p className="card-subtitle">Global administrative settings and system tools</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <button className="btn btn-secondary" onClick={handleExportAuditLogs} style={{ width: '100%', justifyContent: 'flex-start' }}>
              <Download className="nav-icon" /> Export Global Audit Log (CSV)
            </button>

            <button className="btn btn-danger" onClick={handleResetAllBudgets} style={{ width: '100%', justifyContent: 'flex-start' }} disabled={loading}>
              <RefreshCcw className="nav-icon" /> Reset All Privacy Budgets (10.0 ε)
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}
