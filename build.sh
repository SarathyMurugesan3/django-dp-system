#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Skip migrations during build - run manually after deployment
# cd proj
# python manage.py migrate
