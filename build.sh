#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Build React Frontend
echo "Building React frontend..."
cd frontend
npm install
npm run build
cd ..

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate
