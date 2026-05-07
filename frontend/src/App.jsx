import { useState } from 'react'
import { UploadCloud, Map as MapIcon, Crosshair, ArrowLeft, Leaf, Layers } from 'lucide-react'
import UploadTab from './components/UploadTab'
import MapTab from './components/MapTab'
import InstanceTab from './components/InstanceTab'

function App() {
  const [currentView, setCurrentView] = useState('home')

  const renderView = () => {
    switch(currentView) {
      case 'upload': return <UploadTab />;
      case 'map': return <MapTab />;
      case 'instance': return <InstanceTab />;
      default: return null;
    }
  }

  if (currentView === 'home') {
    return (
      <div style={{ position: 'relative', minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div className="landing-bg"></div>
        
        <div style={{ textAlign: 'center', zIndex: 1, marginBottom: '2rem' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(34, 197, 94, 0.2)', padding: '1rem', borderRadius: '50%', marginBottom: '1.5rem', border: '1px solid var(--agri-light)' }}>
            <Leaf size={48} color="var(--agri-light)" />
          </div>
          <h1 style={{ fontSize: '4rem', fontWeight: 800, background: 'linear-gradient(to right, #4ade80, #10b981)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-1px', marginBottom: '1rem' }}>
            AgriVision Pro
          </h1>
          <p style={{ fontSize: '1.25rem', color: '#e5e7eb', maxWidth: '600px', margin: '0 auto', lineHeight: '1.6' }}>
            Advanced ML-powered crop classification for Pakistan. Leverage Earth Engine data to analyze agriculture with unprecedented accuracy.
          </p>
        </div>

        <div className="landing-grid" style={{ zIndex: 1 }}>
          <div className="feature-card" onClick={() => setCurrentView('upload')}>
            <div className="feature-icon-wrapper">
              <UploadCloud size={36} color="var(--agri-light)" />
            </div>
            <h2>TIFF Upload</h2>
            <p>Upload a multi-band GeoTIFF patch and run batch processing to get a detailed classification map and crop distribution stats.</p>
          </div>

          <div className="feature-card" onClick={() => setCurrentView('map')}>
            <div className="feature-icon-wrapper">
              <MapIcon size={36} color="var(--agri-light)" />
            </div>
            <h2>Interactive Map</h2>
            <p>Draw boundaries directly on high-res satellite imagery. Automatically fetches Earth Engine data and predicts crops dynamically.</p>
          </div>

          <div className="feature-card" onClick={() => setCurrentView('instance')}>
            <div className="feature-icon-wrapper">
              <Crosshair size={36} color="var(--agri-light)" />
            </div>
            <h2>Point Analysis</h2>
            <p>Pinpoint a single coordinate. Manually adjust spectral indices and band values to instantly simulate specific crop signatures.</p>
          </div>
        </div>
      </div>
    )
  }

  // Application View
  return (
    <div className="app-container">
      <header className="header glass-panel">
        <div className="header-title">
          <Leaf size={32} color="var(--agri-light)" />
          <h1>AgriVision Pro</h1>
        </div>
        <button className="back-btn" onClick={() => setCurrentView('home')}>
          <ArrowLeft size={18} />
          Back to Home
        </button>
      </header>

      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="content-area">
          {renderView()}
        </div>
      </div>
    </div>
  )
}

export default App
