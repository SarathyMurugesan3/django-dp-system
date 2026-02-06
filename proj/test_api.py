"""
Quick Test Script for Privacy Engine with Budget System
Run this after starting the Django server
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/privacy"

print("=" * 80)
print("PRIVACY ENGINE TEST - POSTMAN EXAMPLES")
print("=" * 80)

# Test 1: Privatize Census Data
print("\n1. Testing Data Privatization...")
print("-" * 80)

data = {
    "records": [
        {
            "id": "101",
            "recordid": "1335",
            "aadhaar": "4821 7394 1056",
            "pan": "ABCDE1234F",
            "agegroup": "28",
            "gender": "Male",
            "state": "tamilnadu",
            "district": "salem",
            "monthlyincomerange": "20000",
            "householdsizerange": "4",
            "landownedrange": "0.7"
        }
    ]
}

print("\nRequest URL:")
print(f"POST {BASE_URL}/assess-and-privatize/")

print("\nRequest Body:")
print(json.dumps(data, indent=2))

try:
    response = requests.post(f"{BASE_URL}/assess-and-privatize/", json=data)
    print("\nResponse Status:", response.status_code)
    print("\nResponse Body:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\nError: {e}")
    print("\nMake sure Django server is running: python manage.py runserver")

# Test 2: Execute DP Query
print("\n\n2. Testing DP Query (Budget System)...")
print("-" * 80)

query_data = {
    "user_id": "analyst_001",
    "query_type": "mean",
    "data": [25, 30, 35, 40, 45, 50],
    "lower_bound": 0,
    "upper_bound": 100,
    "field_name": "age"
}

print("\nRequest URL:")
print(f"POST {BASE_URL}/dp-query/")

print("\nRequest Body:")
print(json.dumps(query_data, indent=2))

try:
    response = requests.post(f"{BASE_URL}/dp-query/", json=query_data)
    print("\nResponse Status:", response.status_code)
    print("\nResponse Body:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\nError: {e}")

# Test 3: Check Budget Status
print("\n\n3. Checking Budget Status...")
print("-" * 80)

print("\nRequest URL:")
print(f"GET {BASE_URL}/budget-status/analyst_001/")

try:
    response = requests.get(f"{BASE_URL}/budget-status/analyst_001/")
    print("\nResponse Status:", response.status_code)
    print("\nResponse Body:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\nError: {e}")

# Test 4: Get Audit Log
print("\n\n4. Getting Audit Log...")
print("-" * 80)

print("\nRequest URL:")
print(f"GET {BASE_URL}/audit-log/analyst_001/")

try:
    response = requests.get(f"{BASE_URL}/audit-log/analyst_001/")
    print("\nResponse Status:", response.status_code)
    print("\nResponse Body:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"\nError: {e}")

print("\n" + "=" * 80)
print("TESTS COMPLETED!")
print("=" * 80)
print("\nFor Postman testing, see: POSTMAN_GUIDE.md")
print("\nAvailable Endpoints:")
print("  POST   /api/privacy/assess-and-privatize/")
print("  POST   /api/privacy/dp-query/")
print("  GET    /api/privacy/budget-status/<user_id>/")
print("  GET    /api/privacy/audit-log/<user_id>/")
print("  POST   /api/privacy/reset-budget/<user_id>/")