# --- Stage 1: Build the React Frontend ---
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Final Image with Python Backend ---
FROM python:3.11-slim

# Install system dependencies for rasterio/GDAL
RUN apt-get update && apt-get install -y \
    build-essential \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set environment variables for HF Spaces
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Install Python dependencies
# We use the CPU version of torch to save space and avoid errors on HF free tier
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.7.0+cpu \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Hugging Face Spaces expects the app on port 7860
EXPOSE 7860

# Start the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
