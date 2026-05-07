#!/usr/bin/env bash
# Exit on error
set -o errexit

# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Build the frontend
cd frontend
npm install
npm run build
cd ..
