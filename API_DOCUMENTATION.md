# Django DP System - API Documentation

**Base URL (Production):** `https://django-dp-system.onrender.com`

## Table of Contents
1. [Differential Privacy Query Endpoints](#differential-privacy-query-endpoints)
2. [Budget Management Endpoints](#budget-management-endpoints)
3. [Admin Endpoints](#admin-endpoints)
4. [Team Management Endpoints](#team-management-endpoints)

---

## Differential Privacy Query Endpoints

### 1. Execute DP Query
**Endpoint:** `POST /api/privacy/dp-query/`

**Description:** Execute differential privacy queries on database tables. All queries must specify a table and field from the database.

**Request Format:**
```json
{
  "user_id": "analyst_001",
  "table_name": "demographics",
  "field_name": "age",
  "query_type": "mean",
  "filters": {
    "age": {"operator": ">", "value": 18},
    "state": {"operator": "=", "value": "Maharashtra"}
  }
}
```

**Required Fields:**
- `user_id` (string): Unique identifier for the analyst
- `table_name` (string): Database table to query
- `field_name` (string): Field/column to analyze
- `query_type` (string): Type of aggregation

**Optional Fields:**
- `filters` (object): Conditions to filter data

**Query Types:** `count`, `mean`, `sum`, `variance`, `std`

**Success Response (200):**
```json
{
  "result": 35.234,
  "metadata": {
    "query_type": "mean",
    "epsilon_cost": 0.05,
    "epsilon_remaining": 9.95,
    "budget_percentage": 99.5,
    "degradation_factor": 1.0,
    "effective_epsilon": 0.05,
    "noise_scale": 20.0,
    "mechanism": "LaplaceBoundedDomain",
    "timestamp": "2026-02-08T08:30:00",
    "privacy_guarantee": "(0.05, 1e-05)-DP",
    "budget_status": "HIGH",
    "warning": null,
    "queries_remaining_estimate": {
      "COUNT": 995,
      "MEAN": 199,
      "SUM": 99
    }
  }
}
```

**Error Response (429 - Budget Exhausted):**
```json
{
  "error": "BUDGET_EXHAUSTED",
  "epsilon_remaining": 0.001,
  "epsilon_required": 0.05,
  "message": "Insufficient privacy budget. Wait for refill or request admin reset."
}
```

**Error Response (400 - Missing Required Fields):**
```json
{
  "error": "table_name required"
}
```

**Error Response (400 - Invalid Query Type):**
```json
{
  "error": "Invalid query type",
  "valid_types": ["count", "mean", "sum", "variance", "std"]
}
```

---

### 2. Execute Database Query (Direct)
**Endpoint:** `POST /api/privacy/db-query/`

**Description:** Execute DP query directly on database tables with query fingerprinting and similarity detection.

**Request:**
```json
{
  "user_id": "analyst_001",
  "table_name": "demographics",
  "field_name": "recordid",
  "query_type": "count",
  "filters": {
    "age": {"operator": ">", "value": 18}
  }
}
```

**Success Response (200):**
```json
{
  "result": 1523.45,
  "metadata": {
    "query_type": "count",
    "epsilon_cost": 0.01,
    "budget_multiplier": 1.0,
    "base_epsilon_cost": 0.01,
    "effective_epsilon_cost": 0.01,
    "similar_queries_detected": 0,
    "data_points": 1500,
    "data_range": [1, 2000],
    "team_id": "team_alpha",
    "cross_user_detection": false,
    "warning": null
  },
  "similar_queries": null
}
```

**Response with Budget Penalty:**
```json
{
  "result": 1523.45,
  "metadata": {
    "budget_multiplier": 3.0,
    "effective_epsilon_cost": 0.03,
    "similar_queries_detected": 2,
    "cross_user_detection": true,
    "warning": "⚠️ Your teammate made a very similar query. Budget cost increased 3.0x to prevent coordinated privacy leakage."
  },
  "similar_queries": [
    {
      "user_id": "analyst_002",
      "table_name": "demographics",
      "field_name": "recordid",
      "query_type": "count",
      "timestamp": "2026-02-08T08:25:00"
    }
  ]
}
```

---

### 3. List Tables
**Endpoint:** `GET /api/privacy/tables/`

**Description:** Get list of available database tables for querying.

**Success Response (200):**
```json
{
  "tables": [
    {
      "table_name": "demographics",
      "display_name": "Demographics",
      "type": "structured"
    },
    {
      "table_name": "health_records",
      "display_name": "Health Records",
      "type": "structured"
    }
  ],
  "count": 2
}
```

---

## Budget Management Endpoints

### 3. Get Budget Status
**Endpoint:** `GET /api/privacy/budget-status/{user_id}/`

**Description:** Get current privacy budget status for a user.

**Example:** `GET /api/privacy/budget-status/analyst_001/`

**Success Response (200):**
```json
{
  "user_id": "analyst_001",
  "epsilon_remaining": 9.45,
  "epsilon_total": 10.0,
  "budget_percentage": 94.5,
  "degradation_factor": 1.0,
  "total_queries": 11,
  "last_refill": "2026-02-08T00:00:00"
}
```

---

### 4. Get Audit Log
**Endpoint:** `GET /api/privacy/audit-log/{user_id}/`

**Description:** Get complete audit trail for a user (GDPR/DPDP compliant).

**Example:** `GET /api/privacy/audit-log/analyst_001/`

**Success Response (200):**
```json
{
  "user_id": "analyst_001",
  "audit_log": [
    {
      "timestamp": "2026-02-08T08:30:00",
      "query_type": "mean",
      "epsilon_cost": 0.05,
      "epsilon_remaining": 9.45,
      "mechanism": "LaplaceBoundedDomain",
      "query_id": "a1b2c3d4e5f6",
      "mathematical_output": {
        "sensitivity": 1.0,
        "noise_scale": 20.0,
        "noise_distribution": "Laplace(μ=0, b=20.00)",
        "privacy_formula": "(ε, δ)-DP where ε=0.05, δ=1e-05",
        "true_result_bounds": "[0, 120]",
        "degradation_applied": "1.0x",
        "effective_epsilon": 0.05
      }
    }
  ],
  "total_transactions": 11
}
```

---

### 5. Reset Budget (Admin)
**Endpoint:** `POST /api/privacy/reset-budget/{user_id}/`

**Description:** Reset a user's privacy budget (admin only).

**Request:**
```json
{
  "epsilon": 15.0
}
```

**Success Response (200):**
```json
{
  "message": "Budget reset successful",
  "user_id": "analyst_001",
  "new_epsilon": 15.0
}
```

---

## Admin Endpoints

### 6. Get All Budgets
**Endpoint:** `GET /api/privacy/admin/budgets/`  
**Alias:** `GET /api/privacy/admin/all-budgets/`

**Description:** View all user budgets (admin dashboard).

**Success Response (200):**
```json
{
  "total_users": 15,
  "budgets": [
    {
      "user_id": "analyst_001",
      "epsilon_remaining": 2.5,
      "epsilon_total": 10.0,
      "budget_percentage": 25.0,
      "status": "MEDIUM",
      "total_queries": 45,
      "last_query": "2026-02-08T08:30:00",
      "last_refill": "2026-02-08T00:00:00"
    },
    {
      "user_id": "analyst_002",
      "epsilon_remaining": 0.5,
      "epsilon_total": 10.0,
      "budget_percentage": 5.0,
      "status": "CRITICAL",
      "total_queries": 120,
      "last_query": "2026-02-08T08:25:00",
      "last_refill": "2026-02-08T00:00:00"
    }
  ]
}
```

**Budget Status Values:** `HIGH` (>50%), `MEDIUM` (25-50%), `LOW` (10-25%), `CRITICAL` (<10%)

---

### 7. Get System Statistics
**Endpoint:** `GET /api/privacy/admin/stats/`  
**Alias:** `GET /api/privacy/admin/system-stats/`

**Description:** Get overall system statistics for admin dashboard.

**Success Response (200):**
```json
{
  "system_overview": {
    "total_users": 15,
    "total_queries": 523,
    "average_budget_used_percent": 45.23
  },
  "query_breakdown": {
    "count": 250,
    "mean": 150,
    "sum": 80,
    "variance": 30,
    "std": 13
  },
  "user_status_distribution": {
    "HIGH": 5,
    "MEDIUM": 6,
    "LOW": 3,
    "CRITICAL": 1
  }
}
```

---

### 8. Export Audit Log
**Endpoint:** `POST /api/privacy/admin/export-audit-log/`

**Description:** Export audit logs for compliance (GDPR/DPDP Act).

**Request (All Users, JSON):**
```json
{
  "format": "json"
}
```

**Request (Single User, CSV):**
```json
{
  "user_id": "analyst_001",
  "format": "csv"
}
```

**Success Response (200 - JSON):**
```json
{
  "format": "json",
  "data": [
    {
      "user_id": "analyst_001",
      "timestamp": "2026-02-08T08:30:00",
      "query_type": "mean",
      "epsilon_cost": 0.05,
      "epsilon_remaining": 9.45,
      "mechanism": "LaplaceBoundedDomain",
      "query_id": "a1b2c3d4e5f6"
    }
  ],
  "total_records": 523,
  "exported_at": "2026-02-08T09:00:00"
}
```

**Success Response (200 - CSV):**
```json
{
  "format": "csv",
  "data": "user_id,timestamp,query_type,epsilon_cost,epsilon_remaining,mechanism,query_id\nanalyst_001,2026-02-08T08:30:00,mean,0.05,9.45,LaplaceBoundedDomain,a1b2c3d4e5f6\n...",
  "total_records": 523,
  "exported_at": "2026-02-08T09:00:00"
}
```

---

### 9. Reset All Budgets
**Endpoint:** `POST /api/privacy/admin/reset-all-budgets/`

**Description:** Reset all user budgets (use with caution!).

**Request:**
```json
{
  "confirm": true,
  "epsilon": 10.0
}
```

**Success Response (200):**
```json
{
  "message": "Reset 15 user budgets",
  "new_epsilon": 10.0,
  "timestamp": "2026-02-08T09:00:00"
}
```

**Error Response (400):**
```json
{
  "error": "Confirmation required. Set 'confirm': true"
}
```

---

### 10. Set Custom Budget
**Endpoint:** `POST /api/privacy/admin/set-budget/{user_id}/`

**Description:** Set custom epsilon budget for a specific user.

**Request:**
```json
{
  "epsilon": 20.0
}
```

**Success Response (200):**
```json
{
  "message": "Budget updated successfully",
  "user_id": "analyst_001",
  "new_epsilon": 20.0,
  "epsilon_remaining": 20.0
}
```

---

## Team Management Endpoints

### 11. Create Team
**Endpoint:** `POST /api/privacy/teams/create/`

**Description:** Create a new team for coordinated query detection.

**Request:**
```json
{
  "team_id": "team_alpha",
  "team_name": "Alpha Research Team",
  "created_by": "admin_001"
}
```

**Success Response (201):**
```json
{
  "message": "Team created successfully",
  "team_id": "team_alpha",
  "team_name": "Alpha Research Team"
}
```

---

### 12. Add Team Member
**Endpoint:** `POST /api/privacy/teams/{team_id}/add-member/`

**Description:** Add a user to a team.

**Request:**
```json
{
  "user_id": "analyst_001",
  "role": "member"
}
```

**Success Response (200):**
```json
{
  "message": "User added to team successfully",
  "team_id": "team_alpha",
  "user_id": "analyst_001",
  "role": "member"
}
```

---

### 13. Get Team Members
**Endpoint:** `GET /api/privacy/teams/{team_id}/members/`

**Description:** Get all members of a team.

**Example:** `GET /api/privacy/teams/team_alpha/members/`

**Success Response (200):**
```json
{
  "team_id": "team_alpha",
  "team_name": "Alpha Research Team",
  "members": [
    {
      "user_id": "analyst_001",
      "role": "admin",
      "joined_at": "2026-02-01T10:00:00"
    },
    {
      "user_id": "analyst_002",
      "role": "member",
      "joined_at": "2026-02-02T14:30:00"
    }
  ],
  "total_members": 2
}
```

---

## Common Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid query type",
  "valid_types": ["count", "mean", "sum", "variance", "std"]
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 429 Too Many Requests (Budget Exhausted)
```json
{
  "error": "BUDGET_EXHAUSTED",
  "epsilon_remaining": 0.001,
  "epsilon_required": 0.05,
  "message": "Insufficient privacy budget. Wait for refill or request admin reset."
}
```

### 500 Internal Server Error
```json
{
  "error": "QUERY_EXECUTION_FAILED",
  "message": "Database query failed: connection timeout"
}
```

---

## Authentication & CORS

**Authentication:** Currently not implemented (add token-based auth as needed)

**CORS:** Configured to allow requests from frontend origins. Update `CORS_ALLOWED_ORIGINS` in Django settings for production.

---

## Rate Limiting

- No explicit rate limiting implemented
- Privacy budget acts as natural rate limiter
- Budget refills automatically based on sliding window (default: 0.1ε per hour)

---

## Notes for Frontend Developer

1. **Base URL:** Always use `https://django-dp-system.onrender.com` for production
2. **Content-Type:** All requests should use `Content-Type: application/json`
3. **Error Handling:** Check for both HTTP status codes and `error` field in response
4. **Budget Warnings:** Display `metadata.warning` to users when present
5. **Query Similarity:** Show `similar_queries` data when budget multiplier > 1.0
6. **Team Detection:** Display `cross_user_detection` alerts for coordinated queries
7. **Budget Status Colors:** 
   - HIGH (green): >50%
   - MEDIUM (yellow): 25-50%
   - LOW (orange): 10-25%
   - CRITICAL (red): <10%
