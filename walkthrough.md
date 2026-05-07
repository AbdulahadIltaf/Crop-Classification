# Professional UI/UX Overhaul

I have successfully refactored the application from a prototype Gradio script into a decoupled, professional-level React and FastAPI application.

## Key Upgrades

### 1. Modern Tech Stack
- **Backend (FastAPI)**: We replaced Gradio with FastAPI (`backend/main.py`), creating a structured REST API that exposes three robust endpoints: `/predict/upload`, `/predict/map`, and `/predict/instance`.
- **Frontend (React + Vite)**: We built a sleek, single-page React application (`frontend/`) to act as the presentation layer.

### 2. Premium Aesthetics
- **Dark Mode & Glassmorphism**: We added custom CSS (`index.css`) with modern frosted-glass effects, a deep dark theme (`#0f172a`), and vibrant accent colors.
- **Typography & Layout**: Imported `Inter` font for a cleaner, modern look, combined with a highly responsive grid layout for the dashboard.
- **Animations**: Added hover effects, smooth transitions, and loading spinners powered by `lucide-react`.

### 3. Streamlined Map Workflow
- **Interactive Drawing Tool**: Integrated `react-leaflet` and `leaflet-draw` into the Map tab. You can now draw a polygon directly on the screen.
- **No More Upload Overhead**: The drawn geometry is automatically captured and sent directly to the FastAPI backend! There is no longer a need to draw, export as GeoJSON, and upload. 
- **Satellite Map**: Replaced the default OpenStreetMap layer with a high-resolution Esri World Imagery layer, giving the tool an authentic Earth observation aesthetic.

## How to Run

1. Open a terminal in `/backend`, run `pip install -r requirements.txt`, and start it with `uvicorn main:app --reload --port 8000`.
2. Open another terminal in `/frontend`, run `npm install`, and start it with `npm run dev`.

The app is now running with a significantly enhanced user experience, matching top-tier web applications!
