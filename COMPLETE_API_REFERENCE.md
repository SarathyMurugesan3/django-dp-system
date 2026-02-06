# Complete API Reference - All Endpoints with Raw JSON

**Base URL**: `http://localhost:8000`

---

## 🔒 Privacy & DP Endpoints

### 1. Execute DP Query (Database)
**POST** `/api/privacy/dp-query/`

**Request:**
```json
{
  "user_id": "analyst_001",
  "table_name": "dataset_records",
  "field_name": "Age",
  "query_type": "mean",
  "filters": {
    "Gender": "Female"
  }
}
```

**Response:**
```json
{
  "result": 42.567,
  "metadata": {
    "query_type": "mean",
    "epsilon_cost": 0.05,
    "epsilon_remaining": 9.95,
    "budget_multiplier": 1.0,
    "similar_queries_detected": 0,
    "data_points": 150
  }
}
```

---

### 2. Execute Database Query
**POST** `/api/privacy/db-query/`

**Request:**
```json
{
  "user_id": "analyst_001",
  "table_name": "dataset_records",
  "field_name": "MonthlyIncome",
  "query_type": "sum",
  "filters": {
    "State": "Karnataka",
    "recordid": {"operator": ">=", "value": 50}
  }
}
```

**Response:**
```json
{
  "result": 1234567.89,
  "metadata": {
    "query_type": "sum",
    "epsilon_cost": 0.1,
    "budget_multiplier": 1.0,
    "data_points": 200,
    "data_range": [10000, 200000]
  }
}
```

---

### 3. Get Privatized Table Data
**POST** `/api/privacy/privatized-table/`

**Request:**
```json
{
  "user_id": "analyst_001",
  "table_name": "dataset_records",
  "filters": {
    "State": "Karnataka"
  },
  "limit": 10
}
```

**Response:**
```json
{
  "privatized_data": [
    {
      "Age": 37,
      "State": "Maharashtra",
      "Gender": "Female",
      "District": "District 1",
      "MonthlyIncome": 74523,
      "LandOwnedAcres": 3.82,
      "HouseholdSize": 5,
      "Disability": "No",
      "MaritalStatus": "Married",
      "ChronicIllness": "Yes"
    }
  ],
  "record_count": 10,
  "epsilon_used": 1.0,
  "epsilon_remaining": 8.95
}
```

---

### 4. Assess and Privatize
**POST** `/api/privacy/assess-and-privatize/`

**Request:**
```json
{
  "table_name": "dataset_records",
  "policy": "standard"
}
```

**Response:**
```json
{
  "policy_used": "standard",
  "risk_score": 85,
  "risk_level": "High Risk",
  "new_risk_score": 25,
  "new_risk_level": "Low Risk",
  "risk_reduction_percent": 70.59,
  "privatized_data": [...],
  "record_count": 100
}
```

---

### 5. List Privacy Policies
**GET** `/api/privacy/policies/`

**Response:**
```json
{
  "policies": {
    "minimal": {
      "epsilon": 5.0,
      "k_anonymity": 3,
      "utility_weight": 0.9
    },
    "standard": {
      "epsilon": 2.0,
      "k_anonymity": 5,
      "utility_weight": 0.5
    },
    "strict": {
      "epsilon": 1.0,
      "k_anonymity": 10,
      "utility_weight": 0.3
    }
  }
}
```

---

### 6. Validate Policy
**POST** `/api/privacy/policies/validate/`

**Request:**
```json
{
  "policy": "standard",
  "risk_score": 50
}
```

**Response:**
```json
{
  "policy": "standard",
  "compliant": true,
  "issues": []
}
```

---

### 7. Compare Policies
**POST** `/api/privacy/policies/compare/`

**Request:**
```json
{
  "policies": ["standard", "strict"]
}
```

**Response:**
```json
{
  "comparison": [
    {
      "name": "standard",
      "epsilon": 2.0,
      "k_anonymity": 5,
      "utility_weight": 0.5
    },
    {
      "name": "strict",
      "epsilon": 1.0,
      "k_anonymity": 10,
      "utility_weight": 0.3
    }
  ]
}
```

---

## 💰 Budget Management

### 8. Get Budget Status
**GET** `/api/privacy/budget-status/{user_id}/`

**Example:** `/api/privacy/budget-status/analyst_001/`

**Response:**
```json
{
  "user_id": "analyst_001",
  "epsilon_remaining": 8.45,
  "epsilon_total": 10.0,
  "budget_percentage": 84.5,
  "degradation_factor": 1.0,
  "total_queries": 23
}
```

---

### 9. Get Audit Log
**GET** `/api/privacy/audit-log/{user_id}/`

**Example:** `/api/privacy/audit-log/analyst_001/`

**Response:**
```json
{
  "user_id": "analyst_001",
  "total_transactions": 23,
  "audit_log": [
    {
      "timestamp": "2026-02-06T09:30:00Z",
      "query_type": "mean",
      "epsilon_cost": 0.05,
      "epsilon_remaining": 8.45,
      "mechanism": "LaplaceBoundedDomain"
    }
  ]
}
```

---

### 10. Reset Budget
**POST** `/api/privacy/reset-budget/{user_id}/`

**Example:** `/api/privacy/reset-budget/analyst_001/`

**Request:**
```json
{
  "epsilon": 15.0
}
```

**Response:**
```json
{
  "message": "Budget reset successful",
  "user_id": "analyst_001",
  "new_epsilon": 15.0
}
```

---

### 11. Get Query History
**GET** `/api/privacy/query-history/{user_id}/`

**Example:** `/api/privacy/query-history/analyst_001/`

**Response:**
```json
{
  "user_id": "analyst_001",
  "total_queries": 15,
  "history": [
    {
      "timestamp": "2026-02-06T09:30:00Z",
      "table": "dataset_records",
      "field": "Age",
      "query_type": "mean",
      "filters": {"Gender": "Female"},
      "epsilon_cost": 0.05
    }
  ]
}
```

---

### 12. Calculate Query Cost
**POST** `/api/privacy/calculate-cost/`

**Request:**
```json
{
  "query_type": "mean",
  "dataset_size": 1000,
  "bounds": [0, 100]
}
```

**Response:**
```json
{
  "query_type": "mean",
  "epsilon_cost": 0.05,
  "cost_explanation": "MEAN queries have medium cost (ε=0.05)",
  "queries_possible_with_standard_budget": 200
}
```

---

## 👥 Team Management

### 13. Create Team
**POST** `/api/privacy/teams/create/`

**Request:**
```json
{
  "team_name": "Data Science Team",
  "creator_user_id": "analyst_001",
  "shared_budget": 50.0
}
```

**Response:**
```json
{
  "team_id": "team_abc123",
  "team_name": "Data Science Team",
  "creator": "analyst_001",
  "shared_budget": 50.0
}
```

---

### 14. Join Team
**POST** `/api/privacy/teams/join/`

**Request:**
```json
{
  "user_id": "analyst_002",
  "team_id": "team_abc123"
}
```

**Response:**
```json
{
  "message": "Successfully joined team",
  "team_id": "team_abc123",
  "user_id": "analyst_002"
}
```

---

### 15. Get Team Members
**GET** `/api/privacy/teams/{team_id}/members/`

**Example:** `/api/privacy/teams/team_abc123/members/`

**Response:**
```json
{
  "team_id": "team_abc123",
  "members": [
    {"user_id": "analyst_001", "role": "creator"},
    {"user_id": "analyst_002", "role": "member"}
  ]
}
```

---

### 16. Leave Team
**POST** `/api/privacy/teams/leave/`

**Request:**
```json
{
  "user_id": "analyst_002",
  "team_id": "team_abc123"
}
```

**Response:**
```json
{
  "message": "Successfully left team",
  "team_id": "team_abc123"
}
```

---

## 🔧 Admin Endpoints

### 17. Get All Budgets
**GET** `/api/privacy/admin/all-budgets/`

**Response:**
```json
{
  "budgets": [
    {
      "user_id": "analyst_001",
      "epsilon_remaining": 8.45,
      "epsilon_total": 10.0
    },
    {
      "user_id": "analyst_002",
      "epsilon_remaining": 9.8,
      "epsilon_total": 10.0
    }
  ]
}
```

---

### 18. Set Custom Budget
**POST** `/api/privacy/admin/set-budget/{user_id}/`

**Example:** `/api/privacy/admin/set-budget/analyst_001/`

**Request:**
```json
{
  "max_epsilon": 20.0,
  "refill_rate": 0.2,
  "refill_interval_hours": 24
}
```

**Response:**
```json
{
  "message": "Budget updated",
  "user_id": "analyst_001",
  "new_budget": 20.0
}
```

---

### 19. Get System Stats
**GET** `/api/privacy/admin/system-stats/`

**Response:**
```json
{
  "total_users": 50,
  "total_queries": 1234,
  "total_epsilon_consumed": 456.78,
  "average_queries_per_user": 24.68
}
```

---

### 20. Export Audit Log
**POST** `/api/privacy/admin/export-audit-log/`

**Request:**
```json
{
  "start_date": "2026-02-01",
  "end_date": "2026-02-06",
  "format": "csv"
}
```

**Response:**
```json
{
  "export_url": "/downloads/audit_log_2026-02-01_2026-02-06.csv",
  "record_count": 5678
}
```

---

### 21. Reset All Budgets
**POST** `/api/privacy/admin/reset-all-budgets/`

**Request:**
```json
{
  "new_epsilon": 10.0
}
```

**Response:**
```json
{
  "message": "All budgets reset",
  "users_affected": 50,
  "new_epsilon": 10.0
}
```

---

## 📊 Risk Assessment Endpoints

### 22. Assess Table Risk
**POST** `/api/assess-table/`

**Request:**
```json
{
  "table_name": "dataset_records"
}
```

**Response:**
```json
{
  "table_name": "dataset_records",
  "risk_score": 85,
  "risk_level": "High Risk",
  "identifiers": ["RecordID"],
  "quasi_identifiers": ["Age", "Gender", "State", "District"],
  "sensitive_attributes": ["MonthlyIncome", "Disability"]
}
```

---

### 23. List Tables
**GET** `/api/list-tables/`

**Response:**
```json
{
  "tables": [
    "dataset_records",
    "demographics",
    "survey_data"
  ]
}
```

---

### 24. Assess Query Risk
**POST** `/api/assess-query/`

**Request:**
```json
{
  "query": "SELECT Age, Gender FROM dataset_records WHERE State='Karnataka'"
}
```

**Response:**
```json
{
  "risk_score": 65,
  "risk_level": "Moderate Risk",
  "recommendations": [
    "Apply k-anonymity with k=5",
    "Generalize Age to ranges"
  ]
}
```

---

### 25. Assess Dataset Risk
**POST** `/api/assess-dataset/`

**Request:**
```json
{
  "records": [
    {"name": "John", "age": 35, "city": "Bangalore"},
    {"name": "Jane", "age": 28, "city": "Mumbai"}
  ]
}
```

**Response:**
```json
{
  "risk_score": 75,
  "risk_level": "High Risk",
  "unique_combinations": 2,
  "recommendations": [
    "Remove direct identifiers (name)",
    "Apply differential privacy to age"
  ]
}
```

---

## 🔍 Query Types & Operators

### Supported Query Types
- `count` - Count records (ε = 0.01)
- `mean` - Average value (ε = 0.05)
- `sum` - Sum of values (ε = 0.1)
- `variance` - Variance (ε = 0.1)
- `std` - Standard deviation (ε = 0.1)

### Filter Operators
```json
{
  "field_name": {"operator": ">=", "value": 100}
}
```

**Available Operators:**
- `=` - Equality (default)
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal
- `!=` - Not equal
- `LIKE` - Pattern matching

---

## 🛡️ Privacy Transformations

### Applied Automatically to Privatized Data

| Field | Transformation | Example |
|-------|----------------|---------|
| Age | ±2 or ±3 noise | 35 → 37 |
| State | Randomized response (75% truthful) | "Karnataka" → "Maharashtra" |
| Gender | Randomized response (75% truthful) | "Male" → "Female" |
| AreaType | Randomized response (75% truthful) | "Urban" → "Rural" |
| District | Anonymized | "Bangalore" → "District 1" |
| Disability | Randomized response (75% truthful) | "Yes" → "No" |
| MaritalStatus | Randomized response (75% truthful) | "Married" → "Unmarried" |
| ChronicIllness | Randomized response (75% truthful) | "Yes" → "No" |
| MonthlyIncome | DP noise | 50000 → 51234 |
| LandOwnedAcres | DP noise | 3.5 → 3.67 |
| HouseholdSize | DP noise | 5 → 6 |

---

## 🔐 Security Features

### Deterministic Noise (HMAC-Based)
```
seed = HMAC(secret_key, query_id || time_window)
noise = Laplace(PRNG(seed))
```

**Properties:**
- ✅ Same query = same result within time window
- ✅ Different time windows = different noise
- ✅ Cryptographically secure
- ✅ No averaging attacks possible

### Time Window Rotation
- **Daily** (default): Seed changes every 24 hours
- **Weekly**: Seed changes every 7 days
- **Monthly**: Seed changes every 30 days

Configure via: `DP_SEED_ROTATION_HOURS` in settings

---

## ⚠️ Broken Endpoints (Do Not Use)

These endpoints exist but will fail:

- ❌ **POST** `/api/privacy/privatize/` - Method `privatize_only()` doesn't exist
- ❌ **POST** `/api/privacy/classify/` - Method `classify_columns()` doesn't exist

---

## 📝 Testing Examples

### Python
```python
import requests

BASE_URL = "http://localhost:8000/api/privacy/"

# Test DP query
response = requests.post(f"{BASE_URL}dp-query/", json={
    "user_id": "analyst_001",
    "table_name": "dataset_records",
    "field_name": "Age",
    "query_type": "mean",
    "filters": {"Gender": "Female"}
})
print(response.json())

# Test privatized table
response = requests.post(f"{BASE_URL}privatized-table/", json={
    "user_id": "analyst_001",
    "table_name": "dataset_records",
    "filters": {},
    "limit": 10
})
print(response.json())

# Check budget
response = requests.get(f"{BASE_URL}budget-status/analyst_001/")
print(response.json())
```

### PowerShell
```powershell
# DP Query
$body = @{
    user_id = "analyst_001"
    table_name = "dataset_records"
    field_name = "Age"
    query_type = "mean"
    filters = @{Gender = "Female"}
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/privacy/dp-query/" -Method Post -Body $body -ContentType "application/json"

# Budget Status
Invoke-RestMethod -Uri "http://localhost:8000/api/privacy/budget-status/analyst_001/" -Method Get
```
