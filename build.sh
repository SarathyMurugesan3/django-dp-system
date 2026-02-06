#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

cd proj
python manage.py migrate
