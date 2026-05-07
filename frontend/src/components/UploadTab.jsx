import React, { useState, useRef } from 'react';
import { Upload, FileImage, Loader2 } from 'lucide-react';
import axios from 'axios';

const UploadTab = () => {
  const [file, setFile] = useState(null);
  const [province, setProvince] = useState('Punjab');
  const [season, setSeason] = useState('Rabi');
  const [date, setDate] = useState('10/01/2023');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handlePredict = async () => {
    if (!file) {
      setError("Please select a file first.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    }
    formData.append('province', province);
    formData.append('season', season);
    formData.append('date', date);

    try {
      const response = await axios.post('http://localhost:8000/predict/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred during prediction.");
    } finally {
      setLoading(false);
    }
  };



  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <div>
        <h2 style={{ marginBottom: '0.5rem' }}>Upload GeoTIFF</h2>
        <p style={{ color: 'var(--text-muted)' }}>Upload a .tiff file containing spectral bands for crop classification.</p>
      </div>

      <div className="grid-3">
        <div className="form-group">
          <label>Province</label>
          <input className="input-field" value={province} onChange={e => setProvince(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Season</label>
          <input className="input-field" value={season} onChange={e => setSeason(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Date (DD/MM/YYYY)</label>
          <input className="input-field" value={date} onChange={e => setDate(e.target.value)} />
        </div>
      </div>

      <div 
        className="upload-zone" 
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          accept=".tiff,.tif"
          onChange={handleFileChange}
        />
        {file ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <FileImage size={48} color="var(--agri-bright)" />
            <span style={{ fontWeight: 600 }}>{file.name}</span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <Upload size={48} color="var(--text-muted)" />
            <span>Click to browse or drag and drop a .tiff file here</span>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <button className="btn-primary" onClick={handlePredict} disabled={loading || !file}>
          {loading ? <Loader2 className="animate-spin" /> : <Upload size={20} />}
          {loading ? 'Processing...' : 'Predict Uploaded File'}
        </button>
      </div>

      {error && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderRadius: '8px' }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: '2rem', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '300px' }}>
            <h3 style={{ marginBottom: '1rem' }}>Prediction Map</h3>
            <img 
              src={`data:image/png;base64,${result.image}`} 
              alt="Prediction" 
              style={{ width: '100%', borderRadius: '12px', border: '1px solid var(--border-color)' }}
            />
          </div>
          <div style={{ flex: 1, minWidth: '300px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ marginBottom: '1rem' }}>Statistics</h3>
            {result.stats.map((stat, i) => (
              <div key={i} className="stat-card">
                <div className="stat-details">
                  <div className="stat-name">{stat.crop}</div>
                  <div className="stat-value">{stat.count} pixels ({stat.percentage.toFixed(2)}%)</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadTab;
