import os
import json
import tempfile
import concurrent.futures
from dotenv import load_dotenv

# Load .env from the project root (one level above backend/)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
import ee
from datetime import datetime, timedelta
import rasterio
from rasterio.transform import xy
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from PIL import Image
from shapely.geometry import shape, Point

app = FastAPI(title="Crop Classification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration paths (assuming run from backend directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Earth Engine initialisation from .env ────────────────────────────────────
def _build_gee_key_file() -> str:
    """Write the service-account private key from env vars to a temp JSON file
    and return its path.  The caller is responsible for deleting it when done."""
    sa_info = {
        "type": "service_account",
        "project_id": os.environ["GEE_PROJECT_ID"],
        "private_key_id": os.environ["GEE_PRIVATE_KEY_ID"],
        "private_key": os.environ["GEE_PRIVATE_KEY"].replace("\\n", "\n"),
        "client_email": os.environ["GEE_CLIENT_EMAIL"],
        "client_id": os.environ["GEE_CLIENT_ID"],
        "auth_uri": os.environ.get("GEE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": os.environ.get("GEE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": os.environ.get("GEE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url": os.environ["GEE_CLIENT_X509_CERT_URL"],
        "universe_domain": "googleapis.com",
    }
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(sa_info, tmp)
    tmp.flush()
    tmp.close()
    return tmp.name

try:
    _key_file = _build_gee_key_file()
    SERVICE_ACCOUNT = os.environ["GEE_SERVICE_ACCOUNT"]
    credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, _key_file)
    ee.Initialize(credentials)
    os.remove(_key_file)  # clean up temp key file immediately after init
    print("✅ Earth Engine initialized from .env credentials.")
except Exception as e:
    print(f"❌ Earth Engine initialization failed: {e}")

# Define crop season dictionary
crop_season_dict = {
    "Punjab": {
        "Rabi": [
            "wheat", "barley", "gram (chickpea)", "lentil", "mustard", "rapeseed mustard",
            "linseed", "peas", "garlic", "onion", "coriander", "fennel", "potato",
            "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ],
        "Kharif": [
            "cotton", "rice", "sugarcane", "maize", "sesame", "millet", "sorghum", "sunflower",
            "groundnuts", "okra", "tomato", "chillies", "banana", "mango",
            "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ]
    },
    "Sindh": {
        "Rabi": [
            "wheat", "barley", "peas", "gram (chickpea)", "mustard", "onion", "garlic", "spinach",
            "coriander", "potato", "fennel", "turnip",
            "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ],
        "Kharif": [
            "cotton", "rice", "sugarcane", "maize", "sesame", "millet", "okra", "tomato",
            "chillies", "banana", "mango", "sunflower", "guava",
            "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ]
    },
    "Balochistan": {
        "Rabi": [
            "wheat", "barley", "gram (chickpea)", "lentil", "peas", "mustard", "potato",
            "onion", "coriander", "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ],
        "Kharif": [
            "maize", "rice", "millet", "sorghum", "peach", "apple", "grapes", "tomato",
            "chillies", "pomegranate", "groundnuts", "sunflower",
            "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ]
    },
    "Khyber Pakhtunkhwa": {
        "Rabi": [
            "wheat", "barley", "gram (chickpea)", "lentil", "peas", "mustard", "onion",
            "garlic", "turnip", "potato", "coriander",
            "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ],
        "Kharif": [
            "maize", "rice", "sugarcane", "tomato", "chillies", "peach", "plum", "apricot",
            "apple", "mango", "sunflower", "okra", "sesame",
            "fallow (agriculture)", "water", "barren", "shrubs", "forest"
        ]
    }
}

# Define model
class CropClassifier(nn.Module):
    def __init__(self, input_size, num_classes):
        super(CropClassifier, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 512),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(),
            nn.Dropout(0.4),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.LeakyReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.LeakyReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, num_classes)
        )
    def forward(self, x):
        return self.network(x)

# Load saved objects
try:
    scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))
    label_to_idx = joblib.load(os.path.join(BASE_DIR, "label_encoder.pkl"))
    feature_columns = joblib.load(os.path.join(BASE_DIR, "feature_columns.pkl"))
    idx_to_label = {v: k for k, v in label_to_idx.items()}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CropClassifier(len(feature_columns), len(label_to_idx)).to(device)
    model.load_state_dict(torch.load(os.path.join(BASE_DIR, "final_crop_model.pth"), map_location=device))
    model.eval()
except Exception as e:
    print(f"Error loading models: {e}")

uncertainty_threshold = 0.2
uncertain_class_idx = len(label_to_idx)
idx_to_label[uncertain_class_idx] = "Uncertain"

def get_color_palette(n):
    if n <= 20:
        palette = list(matplotlib.colors.TABLEAU_COLORS.values()) + list(matplotlib.colors.CSS4_COLORS.values())
        return palette[:n]
    else:
        return [matplotlib.colors.rgb2hex(matplotlib.cm.hsv(i/n)) for i in range(n)]

def assign_crop_colors(unique_crops):
    palette = get_color_palette(len(unique_crops))
    return {crop: palette[i] for i, crop in enumerate(unique_crops)}

def get_valid_user_classes(province, season):
    try:
        user_classes = crop_season_dict.get(province, {}).get(season, [])
        return [cls for cls in user_classes if cls in label_to_idx]
    except:
        return []

# --- Pydantic Models ---
class MapPredictionRequest(BaseModel):
    province: str
    season: str
    date: str
    spacing_m: float
    geometry: Dict[str, Any]

class InstancePredictionRequest(BaseModel):
    province: str
    season: str
    latitude: float
    longitude: float
    date: str
    ndvi: float
    ndwi: float
    ndbi: float
    red: float
    green: float
    blue: float
    nir: float
    swir: float


@app.post("/predict/upload")
async def predict_upload(
    province: str = Form(...),
    season: str = Form(...),
    date: str = Form(...),
    file: Optional[UploadFile] = File(None),
    sample: Optional[str] = Form(None)
):
    if not file and not sample:
        raise HTTPException(status_code=400, detail="Must provide either a file or a sample name.")

    if sample:
        sample_map = {"Sample 1": "sample1.tif", "Sample 2": "sample2.tif"}
        if sample not in sample_map:
            raise HTTPException(status_code=400, detail="Invalid sample selection.")
        tmp_path = os.path.join(BASE_DIR, "samples", sample_map[sample])
    else:
        if not file.filename.endswith(('.tiff', '.tif')):
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .tiff or .tif file.")

        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tif") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

    try:
        with rasterio.open(tmp_path) as src:
            patch = src.read()
            transform = src.transform
            rows, cols = patch.shape[1], patch.shape[2]
            row_indices, col_indices = np.meshgrid(np.arange(rows), np.arange(cols), indexing='ij')
            lon, lat = xy(transform, row_indices, col_indices)
            lon_mask = np.array(lon).reshape(rows, cols)
            lat_mask = np.array(lat).reshape(rows, cols)
    except Exception as e:
        if not sample:
            os.remove(tmp_path)
        raise HTTPException(status_code=400, detail=f"Error reading GeoTIFF file: {str(e)}")
    
    if not sample:
        os.remove(tmp_path)

    if len(patch.shape) != 3 or patch.shape[0] < 7:
        raise HTTPException(status_code=400, detail="Invalid GeoTIFF file format. Expected at least 7 bands.")

    patch = np.transpose(patch, (1, 2, 0))
    H, W, _ = patch.shape

    r, g, b = patch[..., 0], patch[..., 1], patch[..., 2]
    rgb = np.stack([r, g, b], axis=-1).astype(np.float32)
    rgb_norm = (rgb - rgb.min()) / (rgb.max() - rgb.min() + 1e-6)

    pixels = []
    for i in range(H):
        for j in range(W):
            pix = patch[i, j].astype(np.float32)
            red, green, blue, nir, swr1 = pix[0], pix[1], pix[2], pix[4], pix[5]
            pixels.append({
                "Province": province,
                "Season": season,
                "Latitude": lat_mask[i, j],
                "Longitude": lon_mask[i, j],
                "NDVI": (nir - red) / (nir + red + 1e-6),
                "NDWI": (green - nir) / (green + nir + 1e-6),
                "NDBI": (swr1 - nir) / (swr1 + nir + 1e-6),
                "Red": red,
                "Green": green,
                "Blue": blue,
                "NIR": nir,
                "SWIR": swr1,
                "Date": date
            })

    df = pd.DataFrame(pixels)
    try:
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    except:
        raise HTTPException(status_code=400, detail="Invalid date format. Please use DD/MM/YYYY.")
    
    df["HalfMonth"] = df["Date"].dt.day.apply(lambda x: 0 if x <= 15 else 1)
    df["Month"] = df["Date"].dt.month
    df.drop(columns=["Date"], inplace=True)

    df = pd.get_dummies(df, columns=['Province', 'Season'], dummy_na=True)
    missing_cols = set(feature_columns) - set(df.columns)
    for col in missing_cols:
        df[col] = 0
    df = df[feature_columns]
    df = df.replace([np.inf, -np.inf], np.finfo(np.float32).eps)

    try:
        X_scaled = scaler.transform(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scaling features: {str(e)}")

    X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(device)
    with torch.no_grad():
        outputs = model(X_tensor)
        valid_user_classes = get_valid_user_classes(province, season)
        user_class_indices = [label_to_idx[cls] for cls in valid_user_classes if cls in label_to_idx]
        if user_class_indices:
            mask = torch.ones_like(outputs) * -1e10
            for idx in user_class_indices:
                mask[:, idx] = 0
            outputs = outputs + mask
        probs = torch.softmax(outputs, dim=1)
        max_probs, preds = torch.max(probs, dim=1)
        uncertain_mask = max_probs < uncertainty_threshold
        preds[uncertain_mask] = uncertain_class_idx
    preds = preds.cpu().numpy().reshape(H, W)

    unique_classes = np.unique(preds)
    color_map = assign_crop_colors([idx_to_label[cls] for cls in unique_classes])
    mask_img = np.zeros((H, W, 3))
    for cls, color in color_map.items():
        mask_img[preds == label_to_idx.get(cls, uncertain_class_idx)] = matplotlib.colors.to_rgb(color)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    ax1.imshow(rgb_norm)
    ax1.set_title("Original RGB Patch")
    ax1.axis("off")
    ax2.imshow(mask_img)
    ax2.set_title("Predicted Crop Classification")
    ax2.axis("off")
    legend_elements = [Patch(facecolor=color_map[idx_to_label[cls]], edgecolor='black', label=idx_to_label[cls]) for cls in unique_classes]
    fig.legend(handles=legend_elements, loc='center right', bbox_to_anchor=(1.15, 0.5), title="Predicted Crops")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    stats = []
    for cls in unique_classes:
        class_name = idx_to_label[cls]
        pixel_count = int(np.sum(preds == cls))
        percentage = float((pixel_count / (H * W)) * 100)
        stats.append({"crop": class_name, "count": pixel_count, "percentage": percentage})

    return {"image": img_base64, "stats": stats}


def generate_grid_points(polygon, spacing_deg):
    min_lon, min_lat, max_lon, max_lat = polygon.bounds
    grid_points = []
    point_id = 1
    lat_step = spacing_deg / 2
    lon_step = spacing_deg / 2
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            pt = Point(lon, lat)
            if polygon.contains(pt):
                is_spaced = True
                for existing_pt in grid_points:
                    dist = ((existing_pt["latitude"] - lat) ** 2 + (existing_pt["longitude"] - lon) ** 2) ** 0.5
                    if dist < spacing_deg:
                        is_spaced = False
                        break
                if is_spaced:
                    grid_points.append({
                        "point_id": point_id,
                        "latitude": round(lat, 6),
                        "longitude": round(lon, 6)
                    })
                    point_id += 1
            lon += lon_step
        lat += lat_step
    return grid_points

def get_indices(lat, lon, date_str):
    try:
        point = ee.Geometry.Point([lon, lat])
        date = datetime.strptime(date_str, "%d/%m/%Y")
        start = ee.Date(date.strftime('%Y-%m-%d'))
        end = ee.Date((date + timedelta(days=30)).strftime('%Y-%m-%d'))

        collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                      .filterBounds(point)
                      .filterDate(start, end)
                      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))

        image = collection.median().clip(point)
        band_names = image.bandNames().getInfo()
        if not band_names:
            return None

        B2 = image.select('B2')
        B3 = image.select('B3')
        B4 = image.select('B4')
        B8 = image.select('B8')
        B11 = image.select('B11')

        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        ndwi = image.normalizedDifference(['B3', 'B8']).rename('NDWI')
        evi = image.expression(
            '2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
            {'NIR': B8, 'RED': B4, 'BLUE': B2}).rename('EVI')
        gndvi = image.normalizedDifference(['B8', 'B3']).rename('GNDVI')
        savi = image.expression(
            '((NIR - RED) / (NIR + RED + 0.5)) * 1.5',
            {'NIR': B8, 'RED': B4}).rename('SAVI')

        all_bands = image.addBands([ndvi, ndwi, evi, gndvi, savi])
        values = all_bands.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=10,
            maxPixels=1e8
        ).getInfo()

        return {
            'NDVI': values.get('NDVI', 0.0),
            'NDWI': values.get('NDWI', 0.0),
            'EVI': values.get('EVI', 0.0),
            'GNDVI': values.get('GNDVI', 0.0),
            'SAVI': values.get('SAVI', 0.0),
            'Red': values.get('B4', 0.0),
            'Green': values.get('B3', 0.0),
            'Blue': values.get('B2', 0.0),
            'NIR': values.get('B8', 0.0),
            'SWIR': values.get('B11', 0.0)
        }
    except Exception as e:
        print(f"Error fetching indices for lat={lat}, lon={lon}: {str(e)}")
        return None

def predict_crop_description(point, static_features, scaler, feature_columns, province, season):
    df = pd.DataFrame([{
        **static_features,
        "Latitude": point["latitude"],
        "Longitude": point["longitude"],
        "Date": static_features["Date"]
    }])
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df["HalfMonth"] = df["Date"].dt.day.apply(lambda x: 0 if x <= 15 else 1)
    df["Month"] = df["Date"].dt.month
    df.drop(columns=["Date"], inplace=True)
    df = pd.get_dummies(df)
    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0
    df = df[feature_columns]
    df = df.replace([np.inf, -np.inf], np.finfo(np.float32).eps)
    scaled = scaler.transform(df)
    X_tensor = torch.tensor(scaled, dtype=torch.float32).to(device)
    with torch.no_grad():
        outputs = model(X_tensor)
        valid_user_classes = get_valid_user_classes(province, season)
        user_class_indices = [label_to_idx[cls] for cls in valid_user_classes if cls in label_to_idx]
        if user_class_indices:
            mask = torch.ones_like(outputs) * -1e10
            for idx in user_class_indices:
                mask[:, idx] = 0
            outputs = outputs + mask
        probs = torch.softmax(outputs, dim=1)
        max_probs, preds = torch.max(probs, dim=1)
        uncertain_mask = max_probs < uncertainty_threshold
        preds[uncertain_mask] = uncertain_class_idx
    return idx_to_label[preds.cpu().numpy()[0]]


@app.post("/predict/map")
async def predict_map(req: MapPredictionRequest):
    try:
        datetime.strptime(req.date, "%d/%m/%Y")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Please use DD/MM/YYYY.")

    try:
        polygon = shape(req.geometry)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing polygon: {str(e)}")

    spacing_deg = req.spacing_m / 111320.0
    points = generate_grid_points(polygon, spacing_deg)

    if not points:
        raise HTTPException(status_code=400, detail="No points generated within the polygon. Try decreasing the spacing.")
    
    # We should limit points to avoid timeout
    if len(points) > 100:
        points = points[:100]

    def fetch_indices(point):
        indices = get_indices(point["latitude"], point["longitude"], req.date)
        return point, indices

    valid_points = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        for point, indices in executor.map(fetch_indices, points):
            if indices:
                pt = point.copy()
                pt.update(indices)
                pt["Province"] = req.province
                pt["Season"] = req.season
                pt["Date"] = req.date
                pt["Latitude"] = pt["latitude"]
                pt["Longitude"] = pt["longitude"]
                valid_points.append(pt)

    if not valid_points:
        raise HTTPException(status_code=400, detail="No valid data found for any grid points from GEE.")

    # Batch prediction for speed
    df = pd.DataFrame(valid_points)
    df_pred = df.copy()
    df_pred["Date"] = pd.to_datetime(df_pred["Date"], dayfirst=True)
    df_pred["HalfMonth"] = df_pred["Date"].dt.day.apply(lambda x: 0 if x <= 15 else 1)
    df_pred["Month"] = df_pred["Date"].dt.month
    df_pred.drop(columns=["Date"], inplace=True)
    df_pred = pd.get_dummies(df_pred, columns=['Province', 'Season'])
    
    for col in feature_columns:
        if col not in df_pred.columns:
            df_pred[col] = 0
    df_pred = df_pred[feature_columns]
    df_pred = df_pred.replace([np.inf, -np.inf], np.finfo(np.float32).eps)
    
    scaled = scaler.transform(df_pred)
    X_tensor = torch.tensor(scaled, dtype=torch.float32).to(device)
    
    with torch.no_grad():
        outputs = model(X_tensor)
        valid_user_classes = get_valid_user_classes(req.province, req.season)
        user_class_indices = [label_to_idx[cls] for cls in valid_user_classes if cls in label_to_idx]
        if user_class_indices:
            mask = torch.ones_like(outputs) * -1e10
            for idx in user_class_indices:
                mask[:, idx] = 0
            outputs = outputs + mask
        probs = torch.softmax(outputs, dim=1)
        max_probs, preds = torch.max(probs, dim=1)
        uncertain_mask = max_probs < uncertainty_threshold
        preds[uncertain_mask] = uncertain_class_idx
        
    preds_np = preds.cpu().numpy()
    
    predicted_points = []
    for i, pt in enumerate(valid_points):
        crop = idx_to_label[preds_np[i]]
        predicted_points.append({
            "point_id": pt["point_id"],
            "latitude": pt["latitude"],
            "longitude": pt["longitude"],
            "NDVI": pt["NDVI"],
            "NDWI": pt["NDWI"],
            "EVI": pt["EVI"],
            "GNDVI": pt["GNDVI"],
            "SAVI": pt["SAVI"],
            "crop": crop
        })

    # Calculate stats
    pred_df = pd.DataFrame(predicted_points)
    unique_crops = pred_df['crop'].unique()
    crop_colors = assign_crop_colors(unique_crops)
    
    crop_stats = pred_df['crop'].value_counts()
    stats = []
    for crop, count in crop_stats.items():
        percentage = float((count / len(predicted_points)) * 100)
        stats.append({"crop": crop, "count": int(count), "percentage": percentage, "color": crop_colors.get(crop, "#808080")})

    averages = {
        "NDVI": float(pred_df["NDVI"].mean()),
        "NDWI": float(pred_df["NDWI"].mean()),
        "EVI": float(pred_df["EVI"].mean()),
        "GNDVI": float(pred_df["GNDVI"].mean()),
        "SAVI": float(pred_df["SAVI"].mean()),
    }

    # Add color to points for frontend rendering
    for pt in predicted_points:
        pt["color"] = crop_colors.get(pt.get("crop", "Other"), "#808080")

    return {
        "points": predicted_points,
        "stats": stats,
        "averages": averages,
        "colors": crop_colors
    }


@app.post("/predict/instance")
async def predict_instance(req: InstancePredictionRequest):
    static_features = {
        "Province": req.province,
        "Season": req.season,
        "NDVI": req.ndvi,
        "NDWI": req.ndwi,
        "NDBI": req.ndbi,
        "Red": req.red,
        "Green": req.green,
        "Blue": req.blue,
        "NIR": req.nir,
        "SWIR": req.swir,
        "Date": req.date
    }
    crop = predict_crop_description({"latitude": req.latitude, "longitude": req.longitude}, static_features, scaler, feature_columns, req.province, req.season)
    return {"crop": crop}

# ── Serve React frontend (production build) ───────────────────────────────────
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

print(f"🔍 Checking for frontend at: {FRONTEND_DIST}")
if os.path.isdir(FRONTEND_DIST):
    print("✅ Frontend found! Serving static files.")
    # Serve Vite's hashed asset bundles (JS / CSS / images)
    _assets = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        requested = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(requested):
            return FileResponse(requested)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    print("⚠️ Frontend NOT found. API only mode.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
