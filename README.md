# Crop Classification Pakistan

This project provides an advanced ML-based crop classification system using PyTorch, Google Earth Engine, FastAPI, and React.

## Architecture

- **Backend (`/backend`)**: A FastAPI application that serves the PyTorch classification model, handles GeoTIFF parsing, and fetches satellite imagery indices from Google Earth Engine.
- **Frontend (`/frontend`)**: A modern, interactive web interface built with React, Vite, and Leaflet.

## Prerequisites

- Python 3.9+
- Node.js 18+
- Google Earth Engine Service Account credentials (`gee-service-key.json` in the root folder)
- PyTorch models and scalers (`final_crop_model.pth`, `scaler.pkl`, `feature_columns.pkl`, `label_encoder.pkl` in the root folder)

## Running the Application

### 1. Start the Backend

Open a terminal in the root directory and install requirements:

```bash
cd backend
pip install -r requirements.txt
```

Run the FastAPI server:

```bash
uvicorn main:app --reload --port 8000
```

### 2. Start the Frontend

Open a second terminal in the `frontend` directory:

```bash
cd frontend
npm install
npm run dev
```

Visit the URL provided by Vite (usually `http://localhost:5173`) in your browser to interact with the new interface!

## Features
- **Upload TIFF**: Upload a multi-band GeoTIFF patch to get a full crop classification map.
- **Interactive Map**: Draw polygons directly on a real-world map and fetch instantaneous crop data without manually uploading GeoJSON files.
- **Instance Prediction**: Enter coordinates and spectral index variables to classify a single point.
