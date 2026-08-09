import time
import urllib.request
import sys

URL = "https://django-dp-system.onrender.com/"

print(f"Starting keep-alive pinger for {URL}")
print("Press Ctrl+C to stop.")

while True:
    try:
        # Send a simple GET request
        req = urllib.request.Request(
            URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) KeepAlivePinger/1.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            status = response.getcode()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ping status: {status} (Success)")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ping failed: {e}", file=sys.stderr)
        
    # Wait 30 seconds before the next request
    time.sleep(30)
