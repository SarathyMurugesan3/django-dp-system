import React, { useState } from 'react';
import { FileSpreadsheet, FileText, Settings, Download, Zap, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';

export default function FastConverter() {
  const [txtFile, setTxtFile] = useState(null);
  const [layoutFile, setLayoutFile] = useState(null);
  
  // Layout columns loaded
  const [columns, setColumns] = useState([]);
  const [colWidths, setColWidths] = useState([]);
  
  // Anonymization Options
  const [identifierCols, setIdentifierCols] = useState({});
  const [dpCols, setDpCols] = useState({});
  const [epsilon, setEpsilon] = useState(1.0);
  
  // Progress states
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processedRows, setProcessedRows] = useState(0);
  const [processingTime, setProcessingTime] = useState(0);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [outputFileName, setOutputFileName] = useState('');
  
  const [error, setError] = useState('');

  // Parse the layout CSV file
  const handleLayoutChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLayoutFile(file);
    setError('');

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target.result;
        const lines = text.split(/\r?\n/);
        if (lines.length < 2) throw new Error("Layout CSV is empty.");

        // Detect headers
        const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
        const nameIdx = headers.findIndex(h => h.includes('name') || h.includes('field'));
        const lengthIdx = headers.findIndex(h => h.includes('length') || h.includes('width'));

        if (nameIdx === -1 || lengthIdx === -1) {
          throw new Error("Layout must contain columns named 'Name' and 'Length'.");
        }

        const names = [];
        const widths = [];

        for (let i = 1; i < lines.length; i++) {
          if (!lines[i].trim()) continue;
          const cols = lines[i].split(',');
          const name = cols[nameIdx]?.trim();
          const len = parseInt(cols[lengthIdx]?.trim(), 10);
          if (name && !isNaN(len)) {
            names.push(name);
            widths.push(len);
          }
        }

        setColumns(names);
        setColWidths(widths);
        
        // Reset check selections
        const initialIdents = {};
        const initialDp = {};
        names.forEach(name => {
          const nl = name.toLowerCase();
          if (nl.includes('id') || nl.includes('name') || nl.includes('ssn') || nl.includes('email')) {
            initialIdents[name] = true;
          }
          if (nl.includes('age') || nl.includes('income') || nl.includes('salary') || nl.includes('cost')) {
            initialDp[name] = true;
          }
        });
        setIdentifierCols(initialIdents);
        setDpCols(initialDp);

      } catch (err) {
        setError("Error parsing layout file: " + err.message);
      }
    };
    reader.readAsText(file);
  };

  const handleToggleIdentifier = (col) => {
    setIdentifierCols(prev => ({ ...prev, [col]: !prev[col] }));
  };

  const handleToggleDp = (col) => {
    setDpCols(prev => ({ ...prev, [col]: !prev[col] }));
  };

  // Generate Laplace Noise
  const getLaplaceNoise = (scale) => {
    const u = Math.random() - 0.5;
    return -scale * Math.sign(u) * Math.log(1 - 2 * Math.abs(u));
  };

  // Process the large Fixed Width Text file locally in chunks
  const processFwfFile = async () => {
    if (!txtFile || colWidths.length === 0) return;
    
    setProcessing(true);
    setProgress(0);
    setProcessedRows(0);
    setDownloadUrl(null);
    setError('');
    
    const startTime = performance.now();
    const chunkSize = 16 * 1024 * 1024; // 16MB chunk processing
    let offset = 0;
    const fileSize = txtFile.size;
    
    let csvHeader = columns.join(',') + '\n';
    let csvChunks = [csvHeader];
    
    let partialLine = '';
    let rowCount = 0;
    
    // Noise scaling factor (Sensitivity = 1 / epsilon)
    const scale = 1.0 / parseFloat(epsilon);

    try {
      while (offset < fileSize) {
        const slice = txtFile.slice(offset, offset + chunkSize);
        
        // Read chunk as text
        const chunkText = await new Promise((resolve, reject) => {
          const r = new FileReader();
          r.onload = (e) => resolve(e.target.result);
          r.onerror = (e) => reject(e);
          r.readAsText(slice);
        });

        offset += chunkSize;
        
        // Join with previous leftover line fragment
        const currentText = partialLine + chunkText;
        const lines = currentText.split(/\r?\n/);
        
        // The last line is potentially incomplete, keep it for next chunk
        partialLine = lines.pop() || '';
        
        let chunkCsv = '';
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (!line.trim()) continue;
          
          let colIdx = 0;
          let lineOffset = 0;
          const rowValues = [];
          
          for (let j = 0; j < colWidths.length; j++) {
            const width = colWidths[j];
            const colName = columns[j];
            
            // Extract field value
            let val = line.substring(lineOffset, lineOffset + width).trim();
            lineOffset += width;
            
            // Apply Anonymization rules
            if (identifierCols[colName]) {
              // Hash identifier using a fast client-side string hash
              let hash = 0;
              for (let k = 0; k < val.length; k++) {
                hash = (hash << 5) - hash + val.charCodeAt(k);
                hash |= 0;
              }
              val = `hash_${Math.abs(hash).toString(16)}`;
            } else if (dpCols[colName]) {
              // Parse number and add differential noise
              const numVal = parseFloat(val);
              if (!isNaN(numVal)) {
                const noisyVal = numVal + getLaplaceNoise(scale);
                val = noisyVal.toFixed(2);
              }
            }
            
            // Clean value for CSV insertion
            if (val.includes(',') || val.includes('"') || val.includes('\n')) {
              val = `"${val.replace(/"/g, '""')}"`;
            }
            rowValues.push(val);
          }
          
          chunkCsv += rowValues.join(',') + '\n';
          rowCount++;
        }
        
        csvChunks.push(chunkCsv);
        
        // Update progress bar
        const currentProgress = Math.min(Math.round((offset / fileSize) * 100), 99);
        setProgress(currentProgress);
        setProcessedRows(rowCount);
      }
      
      // Process final leftover line
      if (partialLine.trim()) {
        const rowValues = [];
        let lineOffset = 0;
        for (let j = 0; j < colWidths.length; j++) {
          const width = colWidths[j];
          const colName = columns[j];
          let val = partialLine.substring(lineOffset, lineOffset + width).trim();
          lineOffset += width;
          
          if (identifierCols[colName]) {
            let hash = 0;
            for (let k = 0; k < val.length; k++) {
              hash = (hash << 5) - hash + val.charCodeAt(k);
              hash |= 0;
            }
            val = `hash_${Math.abs(hash).toString(16)}`;
          } else if (dpCols[colName]) {
            const numVal = parseFloat(val);
            if (!isNaN(numVal)) {
              val = (numVal + getLaplaceNoise(scale)).toFixed(2);
            }
          }
          rowValues.push(val);
        }
        csvChunks.push(rowValues.join(',') + '\n');
        rowCount++;
      }

      // Compile file blob
      const fileBlob = new Blob(csvChunks, { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(fileBlob);
      
      setDownloadUrl(url);
      const name = txtFile.name.replace(/\.[^/.]+$/, "") + "_anonymized.csv";
      setOutputFileName(name);
      setProgress(100);
      setProcessedRows(rowCount);
      setProcessingTime(((performance.now() - startTime) / 1000).toFixed(2));

    } catch (err) {
      setError("Processing error: " + err.message);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      <div className="card">
        <h3 className="card-title" style={{ color: 'var(--accent-cyan)' }}><Zap className="nav-icon" /> Client-Side Turbo FWF Converter</h3>
        <p className="card-subtitle">Convert fixed-width text files of up to 1GB directly in your browser. Processed locally in seconds with zero database footprint.</p>

        <div className="form-row" style={{ marginBottom: '24px' }}>
          <div className="form-group">
            <label className="form-label">1. Select Layout Configuration File (.csv)</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input 
                type="file" 
                accept=".csv"
                className="form-input" 
                onChange={handleLayoutChange}
              />
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginTop: '6px' }}>
              Layout CSV must contain name/field and length/width columns (matching convert_fwf.py spec).
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">2. Select Fixed-Width Text File (.txt)</label>
            <input 
              type="file" 
              accept=".txt"
              className="form-input" 
              disabled={columns.length === 0}
              onChange={(e) => setTxtFile(e.target.files[0])}
            />
          </div>
        </div>

        {error && (
          <div style={{ padding: '16px', backgroundColor: 'var(--status-danger-glow)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: 'var(--radius-md)', color: 'var(--status-danger)', marginBottom: '24px' }}>
            <AlertTriangle className="nav-icon" style={{ float: 'left', marginRight: '8px' }} />
            {error}
          </div>
        )}

        {/* Column Configuration List */}
        {columns.length > 0 && (
          <div className="card" style={{ backgroundColor: 'var(--bg-tertiary)', padding: '24px', border: '1px solid var(--border-color)', marginBottom: '24px' }}>
            <h4 style={{ fontSize: '15px', marginBottom: '14px', display: 'flex', items: 'center', gap: '8px' }}>
              <Settings style={{ width: '16px' }} /> Configure Transmission & Anonymization Rules
            </h4>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', maxHeight: '200px', overflowY: 'auto', paddingRight: '10px' }}>
              {columns.map((col, idx) => (
                <div key={col} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: '600', fontSize: '13px' }}>{col}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Width: {colWidths[idx]} characters</span>
                  </div>

                  <div style={{ display: 'flex', gap: '10px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={!!identifierCols[col]} 
                        onChange={() => handleToggleIdentifier(col)}
                      /> Hash ID
                    </label>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={!!dpCols[col]} 
                        onChange={() => handleToggleDp(col)}
                      /> Add DP
                    </label>
                  </div>
                </div>
              ))}
            </div>

            {/* DP Epsilon Slider */}
            {Object.values(dpCols).some(v => v) && (
              <div className="form-group" style={{ marginTop: '20px', marginBottom: 0 }}>
                <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Epsilon Protection Value (ε)</span>
                  <span style={{ color: 'var(--accent-purple)', fontWeight: 'bold' }}>{epsilon} ε</span>
                </label>
                <input 
                  type="range" 
                  min="0.1" 
                  max="5.0" 
                  step="0.1" 
                  className="form-input" 
                  value={epsilon}
                  onChange={(e) => setEpsilon(e.target.value)}
                />
              </div>
            )}
          </div>
        )}

        {/* Process button */}
        {txtFile && colWidths.length > 0 && (
          <button 
            className="btn btn-primary" 
            style={{ width: '100%' }}
            onClick={processFwfFile}
            disabled={processing}
          >
            <Zap className="nav-icon" style={{ fill: '#fff' }} /> {processing ? 'Turbo Processing...' : 'Run FWF-to-CSV Conversion'}
          </button>
        )}
      </div>

      {/* Progress & Output Dashboard */}
      {(processing || progress > 0) && (
        <div className="card">
          <h3 className="card-title">Processing Console</h3>
          <p className="card-subtitle">Streaming execution status</p>
          
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
              <span className="text-secondary">Chunk Processing Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="custom-progress-bar">
              <div className="custom-progress-fill" style={{ width: `${progress}%` }}></div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div style={{ padding: '16px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <span className="text-secondary" style={{ fontSize: '11px', display: 'block', marginBottom: '4px' }}>Processed Rows</span>
              <span style={{ fontSize: '20px', fontWeight: 'bold' }}>{processedRows.toLocaleString()} rows</span>
            </div>

            <div style={{ padding: '16px', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
              <span className="text-secondary" style={{ fontSize: '11px', display: 'block', marginBottom: '4px' }}>Processing Time</span>
              <span style={{ fontSize: '20px', fontWeight: 'bold' }}>{processingTime ? `${processingTime} seconds` : 'Computing...'}</span>
            </div>
          </div>

          {downloadUrl && (
            <div style={{ marginTop: '24px', padding: '20px', backgroundColor: 'var(--status-safe-glow)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <CheckCircle style={{ color: 'var(--status-safe)' }} />
                <div>
                  <strong style={{ color: 'var(--status-safe)' }}>Conversion Complete!</strong>
                  <span style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)' }}>File size: {(txtFile.size / (1024 * 1024)).toFixed(2)} MB processed locally.</span>
                </div>
              </div>

              <a href={downloadUrl} download={outputFileName} className="btn btn-primary" style={{ padding: '10px 18px', background: 'var(--status-safe)', boxShadow: 'none' }}>
                <Download style={{ width: '16px', height: '16px' }} /> Download CSV
              </a>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
