"""
Quick test to verify the db-query endpoint is working
"""
import requests
import json

url = "http://localhost:8000/api/privacy/db-query/"

# Simple test without filters
payload = {
    "user_id": "test_user",
    "table_name": "demographics",
    "field_name": "age",
    "query_type": "mean",
    "filters": {}
}

print("Testing /db-query/ endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
