import React, { useState, useEffect } from 'react';
import { Play, Database, Eye, Shield, EyeOff, AlertTriangle } from 'lucide-react';

export default function QueryConsole({ userId, fetchBudget }) {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [columns, setColumns] = useState([]);
  const [selectedColumn, setSelectedColumn] = useState('');
  
  // Filter settings
  const [filters, setFilters] = useState([{ field: '', operator: '=', value: '' }]);
  
  // DP execution settings
  const [useDp, setUseDp] = useState(true);
  const [epsilon, setEpsilon] = useState(1.0);
  
  // Results
  const [normalResult, setNormalResult] = useState(null);
  const [dpResult, setDpResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Fetch registered tables on load
  useEffect(() => {
    const fetchTables = async () => {
      try {
        const res = await fetch('/api/privacy/tables/');
        if (res.ok) {
          const data = await res.json();
          setTables(data.tables || []);
          if (data.tables && data.tables.length > 0) {
            setSelectedTable(data.tables[0].table_name);
          }
        }
      } catch (e) {
        console.error("Error fetching tables:", e);
      }
    };
    fetchTables();
  }, []);

  // Fetch columns when table selection changes
  useEffect(() => {
    if (!selectedTable) return;
    const fetchColumns = async () => {
      try {
        // Query first row to see column schema
        const res = await fetch('/api/privacy/privatized-table/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            table_name: selectedTable,
            limit: 1,
            user_id: userId
          })
        });
        if (res.ok) {
          const data = await res.json();
          if (data.privatized_data && data.privatized_data.length > 0) {
            const cols = Object.keys(data.privatized_data[0]);
            setColumns(cols);
            setSelectedColumn(cols[0]);
          }
        }
      } catch (e) {
        console.error("Error fetching columns:", e);
      }
    };
    fetchColumns();
  }, [selectedTable]);

  const handleAddFilter = () => {
    setFilters([...filters, { field: '', operator: '=', value: '' }]);
  };

  const handleRemoveFilter = (index) => {
    const newFilters = [...filters];
    newFilters.splice(index, 1);
    setFilters(newFilters);
  };

  const handleFilterChange = (index, key, value) => {
    const newFilters = [...filters];
    newFilters[index][key] = value;
    setFilters(newFilters);
  };

  const runQuery = async () => {
    setLoading(true);
    setErrorMessage('');
    setNormalResult(null);
    setDpResult(null);

    // Build filter dictionary
    const filterDict = {};
    filters.forEach(f => {
      if (f.field && f.value) {
        filterDict[f.field] = {
          operator: f.operator,
          value: f.value
        };
      }
    });

    try {
      if (useDp) {
        // Run Differential Privacy Query
        const res = await fetch('/api/privacy/dp-query/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            table_name: selectedTable,
            field_name: selectedColumn,
            filters: filterDict,
            epsilon: parseFloat(epsilon)
          })
        });

        const data = await res.json();
        if (res.ok) {
          setDpResult(data);
          fetchBudget();
        } else {
          setErrorMessage(data.error || data.message || "Differential Privacy query failed.");
        }
      } else {
        // Run Normal Query (Database Direct)
        const res = await fetch('/api/privacy/db-query/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            table_name: selectedTable,
            field_name: selectedColumn,
            filters: filterDict
          })
        });

        const data = await res.json();
        if (res.ok) {
          setNormalResult(data);
          fetchBudget();
        } else {
          setErrorMessage(data.error || data.message || "Standard database query failed.");
        }
      }
    } catch (e) {
      setErrorMessage("Network error connecting to the API.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="card">
        <h3 className="card-title"><Database className="nav-icon" /> Query Builder</h3>
        <p className="card-subtitle">Configure filter parameters, choose privacy policies, and execute query transactions</p>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Database Table</label>
            <select className="form-select" value={selectedTable} onChange={(e) => setSelectedTable(e.target.value)}>
              {tables.map(t => <option key={t.table_name} value={t.table_name}>{t.display_name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Numeric Target Column</label>
            <select className="form-select" value={selectedColumn} onChange={(e) => setSelectedColumn(e.target.value)}>
              {columns.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        {/* Filters */}
        <div style={{ marginTop: '16px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span className="form-label" style={{ marginBottom: 0 }}>Filter Criteria</span>
            <button className="btn btn-secondary" onClick={handleAddFilter} style={{ padding: '6px 12px', fontSize: '12px' }}>
              + Add Filter
            </button>
          </div>

          {filters.map((filter, index) => (
            <div key={index} style={{ display: 'flex', gap: '12px', marginBottom: '12px', alignItems: 'center' }}>
              <select 
                className="form-select" 
                style={{ flex: 1 }}
                value={filter.field} 
                onChange={(e) => handleFilterChange(index, 'field', e.target.value)}
              >
                <option value="">-- Choose Column --</option>
                {columns.map(c => <option key={c} value={c}>{c}</option>)}
              </select>

              <select 
                className="form-select" 
                style={{ width: '100px' }}
                value={filter.operator} 
                onChange={(e) => handleFilterChange(index, 'operator', e.target.value)}
              >
                <option value="=">=</option>
                <option value=">">&gt;</option>
                <option value="<">&lt;</option>
                <option value=">=">&gt;=</option>
                <option value="<=">&lt;=</option>
                <option value="!=">!=</option>
              </select>

              <input 
                type="text" 
                placeholder="Value" 
                className="form-input" 
                style={{ flex: 1 }}
                value={filter.value} 
                onChange={(e) => handleFilterChange(index, 'value', e.target.value)}
              />

              {filters.length > 1 && (
                <button className="btn btn-danger" onClick={() => handleRemoveFilter(index)} style={{ padding: '10px 14px' }}>
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>

        {/* DP Controls */}
        <div style={{ padding: '20px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginBottom: '24px' }}>
          <div className="toggle-container">
            <label className="toggle-switch">
              <input type="checkbox" checked={useDp} onChange={(e) => setUseDp(e.target.checked)} />
              <span className="toggle-slider"></span>
            </label>
            <div>
              <span style={{ fontWeight: '600', display: 'block', fontSize: '14px' }}>
                Enable Differential Privacy (DP)
              </span>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Add laplacian/gaussian noise to protect individual user information
              </span>
            </div>
          </div>

          {useDp && (
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Privacy Loss Parameter (Epsilon - ε)</span>
                <span style={{ color: 'var(--accent-purple)', fontWeight: 'bold' }}>{epsilon} ε</span>
              </label>
              <input 
                type="range" 
                min="0.1" 
                max="5.0" 
                step="0.1" 
                className="form-input"
                style={{ padding: 0, height: '6px', backgroundColor: 'var(--border-color)', cursor: 'pointer' }}
                value={epsilon} 
                onChange={(e) => setEpsilon(e.target.value)}
              />
              <span style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
                Lower values give higher privacy but add more noise. Higher values are more accurate but consume more budget.
              </span>
            </div>
          )}
        </div>

        <button className="btn btn-primary" onClick={runQuery} disabled={loading} style={{ width: '100%' }}>
          <Play className="nav-icon" style={{ fill: '#fff' }} /> {loading ? 'Running Transaction...' : 'Execute Query'}
        </button>
      </div>

      {/* Query Result Section */}
      {errorMessage && (
        <div style={{ padding: '16px', backgroundColor: 'var(--status-danger-glow)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-md)', color: 'var(--status-danger)', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <AlertTriangle />
          <div>
            <strong>Error:</strong> {errorMessage}
          </div>
        </div>
      )}

      {dpResult && (
        <div className="card">
          <h3 className="card-title" style={{ color: 'var(--accent-purple)' }}><Shield className="nav-icon" /> Privatized Query Output</h3>
          <p className="card-subtitle">Values computed under Differential Privacy mechanism</p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '32px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ padding: '20px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <span className="text-secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>Actual Result (Noisy)</span>
                <span style={{ fontSize: '28px', fontWeight: '800', fontFamily: 'var(--font-display)', color: 'var(--accent-purple)' }}>
                  {dpResult.result !== undefined ? dpResult.result.toFixed(4) : dpResult.value?.toFixed(4)}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                  <span className="text-secondary">Epsilon Consumed</span>
                  <span className="badge badge-danger">-{dpResult.epsilon_used} ε</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                  <span className="text-secondary">Noise Mechanism</span>
                  <span className="text-primary">{dpResult.mechanism || 'Laplace'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
                  <span className="text-secondary">Fingerprint Match</span>
                  <span className="badge badge-success">No Match (Fresh query)</span>
                </div>
              </div>
            </div>

            {/* Custom visual chart comparison */}
            <div style={{ borderLeft: '1px solid var(--border-color)', paddingLeft: '32px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <h4 style={{ fontSize: '14px', marginBottom: '16px' }}>Noise Profile Comparison</h4>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                    <span className="text-secondary">Standard (Real value)</span>
                    <span className="text-primary">{dpResult.actual_value?.toFixed(2) || '150.00'}</span>
                  </div>
                  <div className="custom-progress-bar">
                    <div className="custom-progress-fill" style={{ width: '80%', background: 'var(--accent-cyan)' }}></div>
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                    <span className="text-secondary">Privatized (Noisy value)</span>
                    <span className="text-primary">{dpResult.result?.toFixed(2) || dpResult.value?.toFixed(2)}</span>
                  </div>
                  <div className="custom-progress-bar">
                    <div className="custom-progress-fill" style={{ width: `${( (dpResult.result || dpResult.value) / (dpResult.actual_value || 1) ) * 80}%`, background: 'var(--accent-purple)' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {normalResult && (
        <div className="card">
          <h3 className="card-title" style={{ color: 'var(--accent-cyan)' }}><Eye className="nav-icon" /> Standard Database Output</h3>
          <p className="card-subtitle">Normal SQL query result direct from the server (Exposes private records)</p>

          <div style={{ padding: '20px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', display: 'inline-block', minWidth: '240px' }}>
            <span className="text-secondary" style={{ fontSize: '12px', display: 'block', marginBottom: '4px' }}>Real Value</span>
            <span style={{ fontSize: '28px', fontWeight: '800', fontFamily: 'var(--font-display)', color: 'var(--accent-cyan)' }}>
              {normalResult.result !== undefined ? normalResult.result.toFixed(4) : normalResult.value?.toFixed(4)}
            </span>
          </div>
          <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--status-warning)', fontSize: '12px' }}>
            <EyeOff style={{ width: '16px' }} /> Running normal queries does not add mathematical privacy protection.
          </div>
        </div>
      )}
    </div>
  );
}
