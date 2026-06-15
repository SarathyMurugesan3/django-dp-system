"""Gunicorn configuration file for Django DP System"""
import os

# Bind to the PORT environment variable (Render sets this automatically)
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Worker configuration
workers = int(os.environ.get('WEB_CONCURRENCY', '1'))
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'django-dp-system'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (not needed on Render, they handle it)
keyfile = None
certfile = None
