import React, { useState, useEffect } from 'react';
import { Shield, EyeOff, Layers, BarChart, Database, Activity, RefreshCw } from 'lucide-react';

export default function Dashboard({ userId, budget, fetchBudget }) {
  const [stats, setStats] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchStatsAndLogs = async () => {
    setLoading(true);
    try {
      // Fetch system stats
      const statsRes = await fetch('/api/privacy/admin/stats/');
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      // Fetch audit logs for the selected user
      const logsRes = await fetch(`/api/privacy/audit-log/${userId}/`);
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        setTransactions(logsData.audit_log || []);
      }
    } catch (e) {
      console.error("Error fetching stats and logs:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatsAndLogs();
  }, [userId]);

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card purple">
          <span className="stat-title">Remaining Privacy Budget</span>
          <span className="stat-value">{budget !== null ? `${budget.toFixed(2)} ε` : '10.00 ε'}</span>
          <span className="stat-desc">Remaining capacity before reset</span>
        </div>
        <div className="stat-card cyan">
          <span className="stat-title">Registered Tables</span>
          <span className="stat-value">{stats?.total_tables || 4}</span>
          <span className="stat-desc">Active databases & datasets</span>
        </div>
        <div className="stat-card safe">
          <span className="stat-title">Secure Transactions</span>
          <span className="stat-value">{stats?.total_transactions || transactions.length}</span>
          <span className="stat-desc">Differential Privacy queries processed</span>
        </div>
        <div className="stat-card warning">
          <span className="stat-title">Mean Query Cost</span>
          <span className="stat-value">1.00 ε</span>
          <span className="stat-desc">Standard consumption rate</span>
        </div>
      </div>

      <div className="layout-split">
        <div className="card">
          <h3 className="card-title"><Activity className="nav-icon" /> System Overview</h3>
          <p className="card-subtitle">Local database server details and system metrics</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '13px' }}>
                <span className="text-secondary">Privacy Ledger Consumption</span>
                <span>{(10 - (budget || 10)).toFixed(2)} / 10.0 ε</span>
              </div>
              <div className="custom-progress-bar">
                <div 
                  className="custom-progress-fill" 
                  style={{ width: `${((10 - (budget || 10)) / 10) * 100}%` }}
                ></div>
              </div>
            </div>

            <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span className="text-secondary">Active Protection Engine</span>
                <span className="badge badge-info">Active</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span className="text-secondary">Noise Mechanisms</span>
                <span className="text-primary" style={{ fontSize: '13px', fontWeight: '500' }}>Laplace & Gaussian</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0' }}>
                <span className="text-secondary">Backend Driver</span>
                <span className="text-primary" style={{ fontSize: '13px', fontWeight: '500' }}>Supabase PostgreSQL</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <div>
              <h3 className="card-title"><Layers className="nav-icon" /> Privacy Audit Ledger</h3>
              <p className="card-subtitle" style={{ marginBottom: 0 }}>Recent Differential Privacy actions for User {userId}</p>
            </div>
            <button className="btn btn-secondary" onClick={() => { fetchStatsAndLogs(); fetchBudget(); }} style={{ padding: '8px 12px' }}>
              <RefreshCw className="nav-icon" style={{ width: '16px', height: '16px' }} />
            </button>
          </div>

          <div className="table-container" style={{ maxHeight: '280px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Query ID</th>
                  <th>Type</th>
                  <th>Epsilon Cost</th>
                  <th>Mechanism</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Loading audit log...</td>
                  </tr>
                ) : transactions.length === 0 ? (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No recent ledger transactions</td>
                  </tr>
                ) : (
                  transactions.map((tx) => (
                    <tr key={tx.id || tx.query_id}>
                      <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{tx.query_id?.substring(0, 8)}...</td>
                      <td>
                        <span className="badge badge-info">{tx.query_type}</span>
                      </td>
                      <td style={{ fontWeight: '600', color: 'var(--status-danger)' }}>-{tx.epsilon_cost} ε</td>
                      <td style={{ fontSize: '12px' }}>{tx.mechanism_used || 'Gaussian'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
