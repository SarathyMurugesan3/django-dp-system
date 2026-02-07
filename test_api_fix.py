import urllib.request
import json
import urllib.error

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, method="GET", data=None):
    print(f"Testing {name} ({url})...")
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header('Content-Type', 'application/json')
        
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req.data = json_data
            
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            print(f"Status Code: {status_code}")
            if status_code == 200:
                print("SUCCESS")
                # print(json.loads(response.read().decode('utf-8')))
            else:
                print("FAILED")
    except urllib.error.HTTPError as e:
        print(f"FAILED: {e.code} {e.reason}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"ERROR: {e}")
    print("-" * 30)

if __name__ == "__main__":
    # Test Admin Endpoints
    test_endpoint("All Budgets", f"{BASE_URL}/api/privacy/admin/budgets/")
    test_endpoint("System Stats", f"{BASE_URL}/api/privacy/admin/stats/")
    
    # Test DP Query (Direct)
    test_endpoint("DP Query (Direct)", f"{BASE_URL}/api/privacy/dp-query/", "POST", {
        "user_id": "test_local_1",
        "query_type": "count",
        "data": [1, 2, 3, 4, 5],
        "lower_bound": 0,
        "upper_bound": 10
    })


    # Test DP Query (DB Mode) - Note: This might fail if DB is empty/locked, but checking for 500 vs 400
    test_endpoint("DP Query (DB)", f"{BASE_URL}/api/privacy/dp-query/", "POST", {
        "user_id": "test_local_2",
        "table_name": "demographics",
        "field_name": "age",
        "query_type": "mean"
    })
