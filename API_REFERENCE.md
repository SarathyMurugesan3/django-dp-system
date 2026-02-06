# Working API Reference - Verified Endpoints Only

**Base URL**: `http://localhost:8000/api/privacy/`

> ⚠️ **Note**: This reference contains ONLY verified working endpoints. Some endpoints in the codebase are broken due to missing methods.

---

## ✅ WORKING ENDPOINTS

### 1. Assess and Privatize Data
**POST** `/api/privacy/assess-and-privatize/`

Assess privacy risks and apply transformations to a dataset.

```json
{
  "records": [
    {"name": "John Doe", "age": 35, "email": "john@example.com"}
  ],
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
  "record_count": 1,
  "privacy_metadata": {...}
}
```

---

### 2. List Privacy Policies
**GET** `/api/privacy/policies/`

Get available privacy policies.

No request body needed.

**Response:**
```json
{
  "policies": {
    "minimal": {"epsilon": 3.0, "k_anonymity": 3},
    "standard": {"epsilon": 1.0, "k_anonymity": 5},
    "strict": {"epsilon": 0.5, "k_anonymity": 10}
  }
}
```

---

### 3. Validate Policy
**POST** `/api/privacy/policies/validate/`

Validate a privacy policy configuration.

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

### 4. Compare Policies
**POST** `/api/privacy/policies/compare/`

Compare multiple privacy policies.

```json
{
  "policies": ["standard", "strict"]
}
```

**Response:**
```json
{
  "comparison": [
    {"name": "standard", "epsilon": 1.0, "k_anonymity": 5},
    {"name": "strict", "epsilon": 0.5, "k_anonymity": 10}
  ]
}
```

---

### 5. Execute DP Query (In-Memory)
**POST** `/api/privacy/dp-query/`

Execute a differential privacy query on in-memory data.

**COUNT Query:**
```json
{
  "user_id": "analyst_001",
  "query_type": "count",
  "data": [25, 30, 35, 40, 45, 50],
  "lower_bound": 0,
  "upper_bound": 100,
  "field_name": "age"
}
```

**MEAN Query:**
```json
{
  "user_id": "analyst_001",
  "query_type": "mean",
  "data": [25, 30, 35, 40, 45, 50],
  "lower_bound": 0,
  "upper_bound": 100,
  "field_name": "age"
}
```

**SUM Query:**
```json
{
  "user_id": "analyst_001",
  "query_type": "sum",
  "data": [1000, 2000, 3000, 4000, 5000],
  "lower_bound": 0,
  "upper_bound": 10000,
  "field_name": "salary"
}
```

**Response:**
```json
{
  "result": 37.234,
  "metadata": {
    "query_type": "mean",
    "epsilon_cost": 0.05,
    "epsilon_remaining": 9.95,
    "budget_percentage": 99.5,
    "degradation_factor": 1.0,
    "effective_epsilon": 0.05,
    "noise_scale": 20.0,
    "mechanism": "LaplaceBoundedDomain",
    "privacy_guarantee": "(0.05, 1e-05)-DP",
    "budget_status": "HIGH"
  }
}
```

---

### 6. Execute Database Query
**POST** `/api/privacy/db-query/`

Query database tables with DP protection and similarity detection.

**Simple Query:**
```json
{
  "user_id": "analyst_001",
  "table_name": "demographics",
  "field_name": "age",
  "query_type": "mean",
  "filters": {
    "gender": "Female"
  }
}
```

**Query with Numeric Filters:**
```json
{
  "user_id": "analyst_001",
  "table_name": "dataset_records",
  "field_name": "Age",
  "query_type": "mean",
  "filters": {
    "State": "Karnataka",
    "Gender": "Male",
    "recordid": {"operator": ">", "value": 100}
  }
}
```

**COUNT Query:**
```json
{
  "user_id": "analyst_001",
  "table_name": "dataset_records",
  "field_name": "RecordID",
  "query_type": "count",
  "filters": {
    "Gender": "Female",
    "State": "Telangana"
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
    "budget_multiplier": 1.0,
    "similar_queries_detected": 0,
    "data_points": 150,
    "data_range": [18.0, 75.0]
  }
}
```

---

### 7. Get Query History
**GET** `/api/privacy/query-history/{user_id}/`

Retrieve query history for a user.

Example: `/api/privacy/query-history/analyst_001/`

**Response:**
```json
{
  "user_id": "analyst_001",
  "total_queries": 15,
  "history": [
    {
      "timestamp": "2026-02-06T09:30:00Z",
      "table": "demographics",
      "field": "age",
      "query_type": "mean",
      "filters": {"gender": "Female"},
      "epsilon_cost": 0.05
    }
  ]
}
```

---

### 8. Get Privatized Table Data
**POST** `/api/privacy/privatized-table/`

Fetch privatized table data with privacy transformations applied.

**Basic Request:**
```json
{
  "user_id": "analyst_001",
  "table_name": "dataset_records",
  "filters": {},
  "limit": 10
}
```

**With Filters:**
```json
{
  "user_id": "analyst_001",
  "table_name": "dataset_records",
  "filters": {
    "State": "Karnataka",
    "Gender": "Male",
    "recordid": {"operator": ">=", "value": 50}
  },
  "limit": 20
}
```

**Response:**
```json
{
  "privatized_data": [
    {
      "Age": "36-45",
      "State": "Karnataka",
      "Gender": "Male",
      "District": "District 1",
      "HouseholdSize": "3-5",
      "MonthlyIncome": "50000-75000",
      "LandOwnedAcres": "2.0-3.0",
      "Disability": "No",
      "MaritalStatus": "Married"
    }
  ],
  "record_count": 10,
  "epsilon_used": 1.0,
  "epsilon_remaining": 8.89
}
```

---

### 9. Get Budget Status
**GET** `/api/privacy/budget-status/{user_id}/`

Check privacy budget for a user.

Example: `/api/privacy/budget-status/analyst_001/`

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

### 10. Get Audit Log
**GET** `/api/privacy/audit-log/{user_id}/`

Retrieve audit log for a user (GDPR/DPDP compliant).

Example: `/api/privacy/audit-log/analyst_001/`

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

### 11. Reset Budget (Admin)
**POST** `/api/privacy/reset-budget/{user_id}/`

Reset user budget (admin only).

Example: `/api/privacy/reset-budget/analyst_001/`

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

### 12. Calculate Query Cost
**POST** `/api/privacy/calculate-cost/`

Calculate privacy cost before executing a query.

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

### 13. Create Team
**POST** `/api/privacy/teams/create/`

Create a new team for collaborative analysis.

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

Join an existing team.

```json
{
  "user_id": "analyst_002",
  "team_id": "team_abc123"
}
```

---

### 15. Get Team Members
**GET** `/api/privacy/teams/{team_id}/members/`

List all members of a team.

Example: `/api/privacy/teams/team_abc123/members/`

---

### 16. Leave Team
**POST** `/api/privacy/teams/leave/`

Leave a team.

```json
{
  "user_id": "analyst_002",
  "team_id": "team_abc123"
}
```

---

### 17. Get All Budgets (Admin)
**GET** `/api/privacy/admin/all-budgets/`

View all user budgets (admin only).

---

### 18. Set Custom Budget (Admin)
**POST** `/api/privacy/admin/set-budget/{user_id}/`

Set custom budget for a user (admin only).

```json
{
  "max_epsilon": 20.0,
  "refill_rate": 0.2,
  "refill_interval_hours": 24
}
```

---

### 19. Get System Stats (Admin)
**GET** `/api/privacy/admin/system-stats/`

Get system-wide statistics (admin only).

---

### 20. Export Audit Log (Admin)
**POST** `/api/privacy/admin/export-audit-log/`

Export complete audit log (admin only).

```json
{
  "start_date": "2026-02-01",
  "end_date": "2026-02-06",
  "format": "csv"
}
```

---

### 21. Reset All Budgets (Admin)
**POST** `/api/privacy/admin/reset-all-budgets/`

Reset all user budgets (admin only).

```json
{
  "new_epsilon": 10.0
}
```

---

## ❌ BROKEN ENDPOINTS (Do Not Use)

These endpoints exist in the code but will fail:

- **POST** `/api/privacy/privatize/` - ❌ `PrivacyEngine.privatize_only()` does not exist
- **POST** `/api/privacy/classify/` - ❌ `PrivacyEngine.classify_columns()` does not exist

---

## Filter Operators

Use these operators in filter objects:

- `=` - Equality (default)
- `>` - Greater than (auto-casts to numeric)
- `<` - Less than (auto-casts to numeric)
- `>=` - Greater than or equal (auto-casts to numeric)
- `<=` - Less than or equal (auto-casts to numeric)
- `!=` - Not equal
- `LIKE` - Pattern matching

**Example:**
```json
{
  "recordid": {"operator": ">=", "value": 100}
}
```

---

## Query Types & Epsilon Costs

| Query Type | Epsilon Cost | Description |
|------------|--------------|-------------|
| `count` | 0.01 | Count records |
| `mean` | 0.05 | Average value |
| `sum` | 0.1 | Sum of values |
| `variance` | 0.1 | Variance |
| `std` | 0.1 | Standard deviation |

---

## Privacy Transformations Applied

When using `/api/privacy/privatized-table/`:

| Field | Transformation | Example |
|-------|----------------|---------|
| Age | Range buckets | "36-45", "46-55" |
| HouseholdSize | Range buckets | "3-5", "6-8" |
| LandOwnedAcres | Range buckets | "2.0-3.0", "5.0-10.0" |
| MonthlyIncome | Range buckets | "50000-75000" |
| District | Anonymized | "District 1", "District 2" |
| Disability | Randomized response | May be flipped (75% truthful) |
| ChronicIllness | Randomized response | May be flipped (75% truthful) |
| MaritalStatus | Randomized response | May be changed (75% truthful) |
| State | Unchanged | Actual state names kept |
| RecordID | Hashed | 16-character hash |

---

## Testing Examples

### Test 1: Get Privatized Table
```bash
curl -X POST http://localhost:8000/api/privacy/privatized-table/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "analyst_001",
    "table_name": "dataset_records",
    "filters": {},
    "limit": 10
  }'
```

### Test 2: Execute Database Query
```bash
curl -X POST http://localhost:8000/api/privacy/db-query/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "analyst_001",
    "table_name": "dataset_records",
    "field_name": "Age",
    "query_type": "mean",
    "filters": {"Gender": "Female"}
  }'
```

### Test 3: Get Budget Status
```bash
curl -X GET http://localhost:8000/api/privacy/budget-status/analyst_001/
```

### Test 4: Execute DP Query
```bash
curl -X POST http://localhost:8000/api/privacy/dp-query/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "analyst_001",
    "query_type": "mean",
    "data": [25, 30, 35, 40, 45, 50],
    "lower_bound": 0,
    "upper_bound": 100,
    "field_name": "age"
  }'
```

---

## Python Testing Example

```python
import requests

BASE_URL = "http://localhost:8000/api/privacy/"

# Test 1: Get privatized table data
response = requests.post(f"{BASE_URL}privatized-table/", json={
    "user_id": "analyst_001",
    "table_name": "dataset_records",
    "filters": {"State": "Karnataka"},
    "limit": 10
})
print("Privatized Data:", response.json())

# Test 2: Execute database query
response = requests.post(f"{BASE_URL}db-query/", json={
    "user_id": "analyst_001",
    "table_name": "dataset_records",
    "field_name": "Age",
    "query_type": "mean",
    "filters": {"Gender": "Female"}
})
print("Query Result:", response.json())

# Test 3: Get budget status
response = requests.get(f"{BASE_URL}budget-status/analyst_001/")
print("Budget Status:", response.json())

# Test 4: Execute DP query
response = requests.post(f"{BASE_URL}dp-query/", json={
    "user_id": "analyst_001",
    "query_type": "count",
    "data": [1, 2, 3, 4, 5],
    "lower_bound": 0,
    "upper_bound": 10,
    "field_name": "value"
})
print("DP Query Result:", response.json())
```
