"""
Database Query with Privatized Data Return

New endpoint that returns privatized table data instead of just aggregates
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from .privacy_engine import PrivacyEngine
from .db_budget_manager import DatabasePrivacyBudgetManager, DatabaseBudgetWrapper
import numpy as np


@api_view(['POST'])
def get_privatized_table(request):
    """
    Fetch and return privatized table data
    
    POST /api/privacy/privatized-table/
    {
        "user_id": "analyst_001",
        "table_name": "demographics",
        "filters": {
            "gender": "Male"
        },
        "limit": 100
    }
    
    Returns privatized records with DP applied
    """
    user_id = request.data.get("user_id", "default")
    table_name = request.data.get("table_name")
    filters = request.data.get("filters", {})
    limit = request.data.get("limit", 100)
    
    if not table_name:
        return Response({"error": "table_name required"}, status=400)
    
    # Build WHERE clause
    where_clauses = []
    params = []
    
    # Check if this is dataset_records table (JSON data)
    is_json_table = table_name.lower() == 'dataset_records'
    is_postgres = connection.vendor == 'postgresql'
    quoted_table = connection.ops.quote_name(table_name)
    
    if is_json_table:
        # For dataset_records, filter on JSON fields
        for field, condition in filters.items():
            if isinstance(condition, dict):
                operator = condition.get('operator', '=')
                value = condition.get('value')
                # Use JSON path for filtering
                if is_postgres:
                    where_clauses.append(f"data->>'{field}' {operator} %s")
                else:
                    where_clauses.append(f"JSON_UNQUOTE(JSON_EXTRACT(data, '$.{field}')) {operator} %s")
                params.append(str(value))
            else:
                if is_postgres:
                    where_clauses.append(f"data->>'{field}' = %s")
                else:
                    where_clauses.append(f"JSON_UNQUOTE(JSON_EXTRACT(data, '$.{field}')) = %s")
                params.append(str(condition))
    else:
        # For regular tables, filter on columns
        for field, condition in filters.items():
            quoted_field = connection.ops.quote_name(field)
            if isinstance(condition, dict):
                operator = condition.get('operator', '=')
                value = condition.get('value')
                where_clauses.append(f'{quoted_field} {operator} %s')
                params.append(value)
            else:
                where_clauses.append(f'{quoted_field} = %s')
                params.append(condition)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Fetch data
    sql = f'SELECT * FROM {quoted_table} WHERE {where_sql} LIMIT %s'
    params.append(limit)
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
    except Exception as e:
        return Response({
            "error": "Database query failed",
            "message": str(e)
        }, status=500)
    
    if not rows:
        return Response({
            "error": "No data found",
            "table": table_name,
            "filters": filters
        }, status=404)
    
    # Convert to list of dicts
    if is_json_table:
        # For dataset_records, extract JSON data
        import json
        records = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            # Parse JSON data column
            if 'data' in row_dict and row_dict['data']:
                try:
                    json_data = json.loads(row_dict['data']) if isinstance(row_dict['data'], str) else row_dict['data']
                    # Merge JSON data with row metadata
                    record = {
                        'id': row_dict.get('id'),
                        'dataset_name': row_dict.get('dataset_name'),
                        'row_index': row_dict.get('row_index'),
                        **json_data  # Unpack JSON fields
                    }
                    records.append(record)
                except:
                    records.append(row_dict)
            else:
                records.append(row_dict)
    else:
        # For regular tables, use as-is
        records = [dict(zip(columns, row)) for row in rows]
    
    # Auto-classify columns
    column_classifications = {}
    for col in (records[0].keys() if records else []):
        col_lower = col.lower()
        if any(kw in col_lower for kw in ['id', 'recordid']):
            column_classifications[col] = {'type': 'identifier', 'sensitivity': 'high'}
        elif any(kw in col_lower for kw in ['gender', 'state', 'district']):
            column_classifications[col] = {'type': 'categorical', 'sensitivity': 'medium'}
        elif any(kw in col_lower for kw in ['age', 'income', 'household']):
            column_classifications[col] = {'type': 'quasi_identifier', 'sensitivity': 'high'}
        else:
            column_classifications[col] = {'type': 'categorical', 'sensitivity': 'low'}
    
    # Apply privacy
    budget_manager = DatabasePrivacyBudgetManager()
    budget_wrapper = DatabaseBudgetWrapper()  # No arguments needed
    engine = PrivacyEngine(budget_manager=budget_wrapper)
    
    # Check budget
    try:
        from .privacy_budget_models import PrivacyBudgetLedger
        ledger = PrivacyBudgetLedger.objects.get(user_id=user_id)
        if ledger.epsilon_remaining < 1.0:
            return Response({
                "error": "Insufficient privacy budget",
                "epsilon_remaining": ledger.epsilon_remaining
            }, status=429)
    except PrivacyBudgetLedger.DoesNotExist:
        # Create new ledger
        PrivacyBudgetLedger.objects.create(
            user_id=user_id,
            max_epsilon=10.0,
            epsilon_remaining=10.0
        )
    
    # Compute actual risk score from real data before applying privacy
    from .risk_engine import RiskAssessmentEngine
    risk_engine = RiskAssessmentEngine()
    risk_result = risk_engine.analyze_dataset(records)
    actual_risk_score = risk_result["risk_score"]

    # Apply privacy transformations using real risk score
    privatized_records, metadata = engine.apply_privacy(
        records=records,
        column_classifications=column_classifications,
        risk_score=actual_risk_score,
        user_id=user_id
    )
    
    # Deduct budget (1.0 epsilon for table access)
    from .privacy_budget_models import PrivacyBudgetLedger, PrivacyBudgetTransaction
    ledger = PrivacyBudgetLedger.objects.get(user_id=user_id)
    ledger.epsilon_remaining -= 1.0
    ledger.save()
    
    # Log transaction
    import uuid
    PrivacyBudgetTransaction.objects.create(
        ledger=ledger,
        query_id=str(uuid.uuid4())[:32],
        query_type="privatized_table_access",
        epsilon_cost=1.0,
        epsilon_remaining=ledger.epsilon_remaining,
        mechanism_used="PrivacyEngine.apply_privacy",
        sensitivity=0.0,
        noise_scale=0.0,
        degradation_factor=1.0,
        bounds_lower=0.0,
        bounds_upper=0.0
    )
    
    return Response({
        "privatized_data": privatized_records,
        "record_count": len(privatized_records),
        "table": table_name,
        "filters": filters,
        "risk_score": actual_risk_score,
        "risk_level": risk_result["risk_level"],
        "risk_drivers": risk_result["primary_risk_drivers"],
        "epsilon_used": 1.0,
        "epsilon_remaining": ledger.epsilon_remaining,
        "privacy_metadata": {
            "transformations": metadata.get('transformations_applied', {}),
            "mechanisms": list(set([t['mechanism'] for t in metadata.get('transformations_applied', {}).values()]))
        }
    })
