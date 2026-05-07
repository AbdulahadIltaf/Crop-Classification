import React, { useState } from 'react';
import { Crosshair, Loader2 } from 'lucide-react';
import axios from 'axios';

const InstanceTab = () => {
  const [formData, setFormData] = useState({
    province: 'Punjab',
    season: 'Rabi',
    latitude: 30.809,
    longitude: 73.450,
    date: '10/01/2023',
    ndvi: 0.65,
    ndwi: -2.0,
    ndbi: 0.10,
    red: 678,
    green: 732,
    blue: 620,
    nir: 3000,
    swir: 1800
  });
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    // Parse numbers automatically
    const isNum = !['province', 'season', 'date'].includes(name);
    setFormData(prev => ({
      ...prev,
      [name]: isNum ? parseFloat(value) : value
    }));
  };

  const handlePredict = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/predict/instance`, formData);
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
        <h2 style={{ marginBottom: '0.5rem' }}>Single Point Prediction</h2>
        <p style={{ color: 'var(--text-muted)' }}>Enter specific coordinates and spectral indices manually for an instant classification.</p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        <div>
          <h3 style={{ marginBottom: '1rem', color: 'var(--accent)' }}>Location & Time</h3>
          <div className="grid-3">
            <div className="form-group">
              <label>Province</label>
              <input className="input-field" name="province" value={formData.province} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Season</label>
              <input className="input-field" name="season" value={formData.season} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Date (DD/MM/YYYY)</label>
              <input className="input-field" name="date" value={formData.date} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Latitude</label>
              <input type="number" className="input-field" name="latitude" value={formData.latitude} onChange={handleChange} step="0.001" />
            </div>
            <div className="form-group">
              <label>Longitude</label>
              <input type="number" className="input-field" name="longitude" value={formData.longitude} onChange={handleChange} step="0.001" />
            </div>
          </div>
        </div>

        <div>
          <h3 style={{ marginBottom: '1rem', color: 'var(--accent)' }}>Spectral Indices</h3>
          <div className="grid-3">
            <div className="form-group">
              <label>NDVI</label>
              <input type="number" className="input-field" name="ndvi" value={formData.ndvi} onChange={handleChange} step="0.01" />
            </div>
            <div className="form-group">
              <label>NDWI</label>
              <input type="number" className="input-field" name="ndwi" value={formData.ndwi} onChange={handleChange} step="0.01" />
            </div>
            <div className="form-group">
              <label>NDBI</label>
              <input type="number" className="input-field" name="ndbi" value={formData.ndbi} onChange={handleChange} step="0.01" />
            </div>
          </div>
        </div>

        <div>
          <h3 style={{ marginBottom: '1rem', color: 'var(--accent)' }}>Band Values</h3>
          <div className="grid-3">
            <div className="form-group">
              <label>Red</label>
              <input type="number" className="input-field" name="red" value={formData.red} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Green</label>
              <input type="number" className="input-field" name="green" value={formData.green} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>Blue</label>
              <input type="number" className="input-field" name="blue" value={formData.blue} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>NIR</label>
              <input type="number" className="input-field" name="nir" value={formData.nir} onChange={handleChange} />
            </div>
            <div className="form-group">
              <label>SWIR</label>
              <input type="number" className="input-field" name="swir" value={formData.swir} onChange={handleChange} />
            </div>
          </div>
        </div>
      </div>

      <button className="btn-primary" onClick={handlePredict} disabled={loading} style={{ alignSelf: 'flex-start' }}>
        {loading ? <Loader2 className="animate-spin" /> : <Crosshair size={20} />}
        {loading ? 'Calculating...' : 'Predict Single Point'}
      </button>

      {error && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderRadius: '8px' }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: '1rem', padding: '1.5rem', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid var(--accent)', borderRadius: '12px' }}>
          <h3 style={{ color: 'var(--accent)', marginBottom: '0.5rem' }}>Prediction Result</h3>
          <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>The predicted crop is: <span style={{ color: 'white' }}>{result.crop}</span></p>
        </div>
      )}
    </div>
  );
};

export default InstanceTab;
