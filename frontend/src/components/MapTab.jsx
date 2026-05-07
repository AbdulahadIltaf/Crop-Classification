import React, { useState, useRef, useEffect } from 'react';
import { MapContainer, TileLayer, Circle, Popup, Polygon, useMap } from 'react-leaflet';
import '@geoman-io/leaflet-geoman-free';
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css';
import { MapPin, Loader2 } from 'lucide-react';
import axios from 'axios';

// Required to fix missing icon issue in Leaflet with webpack/vite
import L from 'leaflet';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Component to handle Geoman drawing controls
const GeomanControls = ({ onPolygonCreated }) => {
  const map = useMap();
  
  useEffect(() => {
    map.pm.addControls({
      position: 'topright',
      drawCircle: false,
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawRectangle: true,
      drawPolygon: true,
      editMode: true,
      dragMode: true,
      cutPolygon: false,
      removalMode: true,
      drawText: false
    });

    map.on('pm:create', (e) => {
      // Clear other layers so only 1 polygon exists
      map.eachLayer((layer) => {
        if (layer.pm && layer !== e.layer && layer._path) {
          layer.remove();
        }
      });
      
      const geojson = e.layer.toGeoJSON();
      onPolygonCreated(geojson.geometry);
      
      // Listen to edit events
      e.layer.on('pm:edit', (editEvent) => {
        onPolygonCreated(editEvent.target.toGeoJSON().geometry);
      });
    });

    map.on('pm:remove', (e) => {
      onPolygonCreated(null);
    });

    return () => {
      map.pm.removeControls();
      map.off('pm:create');
      map.off('pm:remove');
    };
  }, [map, onPolygonCreated]);

  return null;
};

const MapTab = () => {
  const [province, setProvince] = useState('Punjab');
  const [season, setSeason] = useState('Rabi');
  const [date, setDate] = useState('10/01/2023');
  const [spacing, setSpacing] = useState(30);
  
  const [drawnPolygon, setDrawnPolygon] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const calculateEstimatedPoints = () => {
    if (!drawnPolygon) return 0;
    
    const coords = drawnPolygon.coordinates[0];
    let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90;
    coords.forEach(coord => {
      minLon = Math.min(minLon, coord[0]);
      maxLon = Math.max(maxLon, coord[0]);
      minLat = Math.min(minLat, coord[1]);
      maxLat = Math.max(maxLat, coord[1]);
    });
    
    const spacingDeg = parseFloat(spacing) / 111320.0;
    const latStep = spacingDeg / 2;
    const lonStep = spacingDeg / 2;
    
    const latCount = Math.max(1, Math.floor((maxLat - minLat) / latStep));
    const lonCount = Math.max(1, Math.floor((maxLon - minLon) / lonStep));
    
    let estimated = Math.floor(latCount * lonCount * 0.7); // Roughly 70% of bounding box
    if (estimated > 100) estimated = 100; // Backend limits to 100
    
    return estimated > 0 ? estimated : 1;
  };

  const estimatedPoints = calculateEstimatedPoints();

  const handlePredict = async () => {
    if (!drawnPolygon) {
      setError("Please draw a polygon on the map first.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/predict/map`, {
        province,
        season,
        date,
        spacing_m: parseFloat(spacing),
        geometry: drawnPolygon
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
        <h2 style={{ marginBottom: '0.5rem' }}>Interactive Map Prediction</h2>
        <p style={{ color: 'var(--text-muted)' }}>Draw a polygon directly on the map to classify crops within the area using Earth Engine.</p>
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
      
      <div className="form-group" style={{ width: '33%' }}>
        <label>Grid Spacing (meters) - Min 10, Max 1000</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <input 
            type="number" 
            className="input-field" 
            value={spacing} 
            onChange={e => setSpacing(e.target.value)} 
            min="10" 
            max="1000"
            style={{ width: '100px' }}
          />
          {drawnPolygon && (
            <span style={{ color: estimatedPoints === 100 ? 'var(--danger)' : 'var(--accent)', fontWeight: '500', fontSize: '0.875rem' }}>
              ~{estimatedPoints} points will be generated {estimatedPoints === 100 ? '(Max Limit Reached)' : ''}
            </span>
          )}
        </div>
      </div>

      <div style={{ height: '500px', width: '100%', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
        <MapContainer center={[30.809, 73.45]} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Tiles &copy; Esri &mdash; Source: Esri"
          />
          <GeomanControls onPolygonCreated={setDrawnPolygon} />

          {/* Render predictions if available */}
          {result && result.points && result.points.map((pt, i) => (
            <Circle 
              key={i}
              center={[pt.latitude, pt.longitude]} 
              radius={spacing / 2}
              pathOptions={{ fillColor: pt.color, color: 'black', weight: 1, fillOpacity: 0.7 }}
            >
              <Popup>
                <div>
                  <strong>Crop: {pt.crop}</strong><br/>
                  NDVI: {pt.NDVI.toFixed(3)}<br/>
                  NDWI: {pt.NDWI.toFixed(3)}
                </div>
              </Popup>
            </Circle>
          ))}
          {drawnPolygon && result && (
            <Polygon positions={drawnPolygon.coordinates[0].map(coord => [coord[1], coord[0]])} pathOptions={{color: 'white', fill: false, weight: 2}} />
          )}
        </MapContainer>
      </div>

      <button className="btn-primary" onClick={handlePredict} disabled={loading || !drawnPolygon}>
        {loading ? <Loader2 className="animate-spin" /> : <MapPin size={20} />}
        {loading ? 'Processing Earth Engine Data...' : 'Predict Crops in Polygon'}
      </button>

      {error && (
        <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderRadius: '8px' }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ marginBottom: '1rem' }}>Crop Distribution</h3>
            {result.stats.map((stat, i) => (
              <div key={i} className="stat-card">
                <div className="stat-color" style={{ backgroundColor: stat.color }}></div>
                <div className="stat-details">
                  <div className="stat-name">{stat.crop}</div>
                  <div className="stat-value">{stat.count} points ({stat.percentage.toFixed(2)}%)</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ marginBottom: '1rem' }}>Average Indices</h3>
            {Object.entries(result.averages).map(([key, value], i) => (
              <div key={i} className="stat-card">
                <div className="stat-details">
                  <div className="stat-name">{key}</div>
                  <div className="stat-value">{value.toFixed(4)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MapTab;
