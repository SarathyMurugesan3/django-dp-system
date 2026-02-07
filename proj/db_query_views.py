"""
Database Query Endpoint with Query Fingerprinting

Allows users to query database tables with DP protection and
detects repeated queries to prevent privacy leakage.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from .privacy_engine import PrivacyEngine, QueryType
from .db_budget_manager import DatabaseBudgetWrapper
from .query_fingerprinting import QueryFingerprint, FingerprintMatcher
from .query_fingerprint_models import QueryFingerprintModel
from django.utils import timezone
import numpy as np


# Use wrapper for PrivacyEngine compatibility
budget_manager_wrapper = DatabaseBudgetWrapper()


@api_view(["POST"])
def execute_db_query(request):
    """
    Execute differential privacy query on database table
    
    New API Format:
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
    """
    user_id = request.data.get("user_id", "default")
    table_name = request.data.get("table_name")
    field_name = request.data.get("field_name")
    query_type_str = request.data.get("query_type", "mean")
    filters = request.data.get("filters", {})
    
    response_data, status_code = process_db_query(user_id, table_name, field_name, query_type_str, filters)
    return Response(response_data, status=status_code)


def process_db_query(user_id, table_name, field_name, query_type_str, filters):
    """
    Core logic for executing DB queries (reusable by other views)
    """
    # Validation
    if not table_name:
        return {"error": "table_name required"}, 400
    if not field_name:
        return {"error": "field_name required"}, 400
    
    try:
        query_type = QueryType(query_type_str.lower())
    except ValueError:
        return {
            "error": "Invalid query type",
            "valid_types": ["count", "mean", "sum", "variance", "std"]
        }, 400
    
    # Step 1: Create query fingerprint
    current_fingerprint = QueryFingerprint(
        table_name=table_name,
        field_name=field_name,
        query_type=query_type_str,
        filters=filters
    )
    
    # Step 2: Check for similar queries in history (including team members)
    # Get user's team_id
    from .privacy_budget_models import PrivacyBudgetLedger as LedgerModel
    try:
        user_ledger = LedgerModel.objects.get(user_id=user_id)
        team_id = user_ledger.team_id
    except LedgerModel.DoesNotExist:
        team_id = None
    
    # Build query to check user's history AND team members' history
    if team_id:
        # Get all team members
        team_members = LedgerModel.objects.filter(team_id=team_id).values_list('user_id', flat=True)
        
        # Check queries from ALL team members (cross-user detection)
        history = QueryFingerprintModel.objects.filter(
            user_id__in=team_members  # ← Check entire team!
        ).order_by('-timestamp')[:200].values(
            'user_id', 'table_name', 'field_name', 'query_type', 
            'filters_json', 'timestamp'
        )
    else:
        # No team - only check user's own history
        history = QueryFingerprintModel.objects.filter(
            user_id=user_id
        ).order_by('-timestamp')[:100].values(
            'user_id', 'table_name', 'field_name', 'query_type', 
            'filters_json', 'timestamp'
        )
    
    history_list = [
        {
            'user_id': h['user_id'],  # Track which user made the query
            'table_name': h['table_name'],
            'field_name': h['field_name'],
            'query_type': h['query_type'],
            'filters': h['filters_json'],
            'timestamp': h['timestamp']
        }
        for h in history
    ]
    
    budget_multiplier, similar_queries = FingerprintMatcher.find_similar_queries(
        current_fingerprint,
        history_list,
        time_window_hours=24
    )
    
    # Step 3: Fetch data from database
    try:
        data, data_min, data_max = fetch_data_from_db(table_name, field_name, filters)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Database query error: {error_details}")  # Log to console
        return {
            "error": "Database query failed",
            "message": str(e),
            "details": error_details
        }, 500
    
    # For COUNT queries, we don't need numeric data - just count the rows
    if query_type == QueryType.COUNT:
        # Count doesn't need numeric conversion
        if not data and data_min == 0 and data_max == 0:
            # No data at all - fetch row count directly
            from django.db import connection
            try:
                where_clauses = []
                params = []
                
                for field, condition in filters.items():
                    if isinstance(condition, dict):
                        operator = condition.get('operator', '=')
                        value = condition.get('value')
                        where_clauses.append(f'"{field}" {operator} %s')
                        params.append(value)
                    else:
                        where_clauses.append(f'"{field}" = %s')
                        params.append(condition)
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                sql = f'SELECT COUNT(*) FROM "{table_name}" WHERE {where_sql}'
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    actual_count = cursor.fetchone()[0]
                
                # Use actual count for DP count query
                data = [1] * actual_count  # Dummy data for count
                data_min, data_max = 0, actual_count
            except Exception as e:
                return {
                    "error": "Count query failed",
                    "message": str(e)
                }, 500
    
    # For non-COUNT queries, we need numeric data
    if query_type != QueryType.COUNT and (not data or len(data) == 0):
        return {
            "error": "No numeric data found",
            "message": f"Field '{field_name}' appears to be categorical or empty. For demographics table, try 'recordid' for numeric queries.",
            "table": table_name,
            "field": field_name,
            "filters": filters,
            "suggestion": "Use 'recordid' as field_name for numeric queries, or use query_type='count' for categorical fields"
        }, 400
    
    # Step 4: Auto-detect bounds from data
    if query_type == QueryType.COUNT:
        lower_bound = 0
        upper_bound = data_max * 1.1
    else:
        lower_bound = float(data_min) - (data_max - data_min) * 0.1
        upper_bound = float(data_max) + (data_max - data_min) * 0.1
    
    # Step 5: Execute DP query with budget multiplier
    engine = PrivacyEngine(budget_manager=budget_manager_wrapper)
    
    # Get base epsilon cost
    from .privacy_engine import QUERY_EPSILON_COST
    base_epsilon_cost = QUERY_EPSILON_COST[query_type]
    effective_epsilon_cost = base_epsilon_cost * budget_multiplier
    
    # Temporarily modify the cost in the engine
    # (We'll deduct the effective cost manually)
    result, metadata = engine.execute_dp_query(
        data=data,
        query_type=query_type,
        user_id=user_id,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        field_name=field_name
    )
    
    if result is None:
        return metadata, 429
    
    # Step 6: Adjust budget if multiplier > 1.0
    if budget_multiplier > 1.0:
        # Deduct additional epsilon
        ledger = budget_manager_wrapper.get_or_create_ledger(user_id)
        additional_cost = base_epsilon_cost * (budget_multiplier - 1.0)
        ledger.deduct(
            query_type=f"{query_type_str}_penalty",
            epsilon_cost=additional_cost,
            mechanism="QuerySimilarityPenalty"
        )
    
    # Step 7: Store query fingerprint
    QueryFingerprintModel.objects.create(
        user_id=user_id,
        table_name=table_name,
        field_name=field_name,
        query_type=query_type_str,
        fingerprint_hash=current_fingerprint.fingerprint_hash,
        filters_json=current_fingerprint.filters,
        epsilon_cost=base_epsilon_cost,
        budget_multiplier=budget_multiplier,
        effective_cost=effective_epsilon_cost,
        result_value=result,
        timestamp=timezone.now()
    )
    
    # Step 8: Add fingerprinting metadata to response
    metadata['budget_multiplier'] = budget_multiplier
    metadata['base_epsilon_cost'] = base_epsilon_cost
    metadata['effective_epsilon_cost'] = round(effective_epsilon_cost, 6)
    metadata['similar_queries_detected'] = len(similar_queries)
    metadata['data_points'] = len(data)
    metadata['data_range'] = [round(data_min, 2), round(data_max, 2)]
    metadata['team_id'] = team_id
    
    # Detect cross-user queries
    cross_user_detected = any(sq.get('user_id') != user_id for sq in similar_queries if 'user_id' in sq)
    metadata['cross_user_detection'] = cross_user_detected
    
    # Add warning if similar queries detected
    if budget_multiplier > 1.0:
        if cross_user_detected:
            # Teammate made similar query
            if budget_multiplier >= 5.0:
                metadata['warning'] = f"🚨 CRITICAL: Your teammate made a nearly identical query! Budget cost increased {budget_multiplier}x. Coordinated queries can leak private information."
            elif budget_multiplier >= 3.0:
                metadata['warning'] = f"⚠️ Your teammate made a very similar query. Budget cost increased {budget_multiplier}x to prevent coordinated privacy leakage."
            else:
                metadata['warning'] = f"⚠️ Similar query detected from your team. Budget cost increased {budget_multiplier}x."
        else:
            # User's own similar query
            if budget_multiplier >= 5.0:
                metadata['warning'] = f"🚨 CRITICAL: Nearly identical query detected! Budget cost increased {budget_multiplier}x. Repeated queries with slight variations can leak private information."
            elif budget_multiplier >= 3.0:
                metadata['warning'] = f"⚠️ Very similar query detected. Budget cost increased {budget_multiplier}x to prevent privacy leakage."
            else:
                metadata['warning'] = f"⚠️ Similar query detected. Budget cost increased {budget_multiplier}x."
    
    return {
        "result": result,
        "metadata": metadata,
        "similar_queries": similar_queries if len(similar_queries) > 0 else None
    }, 200


def get_postgres_type(value):
    """Determine PostgreSQL type for casting"""
    if isinstance(value, (int, float)):
        return 'numeric'
    elif isinstance(value, bool):
        return 'boolean'
    else:
        return 'text'


def fetch_data_from_db(table_name: str, field_name: str, filters: dict) -> tuple:
    """
    Fetch data from database table with filters
    Supports both regular columns AND JSON columns (dataset_records.data)
    
    Returns:
        (data_array, min_value, max_value)
    """
    # Field name mapping for demographics table
    FIELD_MAPPING = {
        'demographics': {
            'age': 'agegroup',  # Map 'age' to actual column 'agegroup'
            'record': 'recordid',
            'area': 'areatype'
        }
    }
    
    # Apply field mapping if table has mappings
    if table_name.lower() in FIELD_MAPPING:
        original_field = field_name
        field_name = FIELD_MAPPING[table_name.lower()].get(field_name.lower(), field_name)
    
    # Build WHERE clause from filters
    where_clauses = []
    params = []
    
    for field, condition in filters.items():
        if isinstance(condition, dict):
            operator = condition.get('operator', '=')
            value = condition.get('value')
            
            # Sanitize operator
            allowed_operators = ['=', '>', '<', '>=', '<=', '!=', 'LIKE', 'IN']
            if operator.upper() not in allowed_operators:
                operator = '='
            
            # Check if this is a JSON field access (dataset_records table)
            if table_name.lower() == 'dataset_records' and field != 'dataset_name':
                # JSON field access: data->>'FieldName'
                where_clauses.append(f"(data->>%s)::{get_postgres_type(value)} {operator} %s")
                params.append(field)
                params.append(value)
            else:
                # Regular column
                where_clauses.append(f'"{field}" {operator} %s')
                params.append(value)
        else:
            # Simple equality
            if table_name.lower() == 'dataset_records':
                where_clauses.append(f"data->>%s = %s")
                params.append(field)
                params.append(str(condition))
            else:
                where_clauses.append(f'"{field}" = %s')
                params.append(condition)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Build SELECT clause based on table type
    if table_name.lower() == 'dataset_records':
        # Extract from JSON column
        select_clause = f"(data->>'{field_name}')::numeric"
    else:
        # Regular column
        select_clause = f'"{field_name}"'
    
    # Build SQL query
    sql = f'''
        SELECT {select_clause}
        FROM "{table_name}"
        WHERE {where_sql}
        AND {select_clause} IS NOT NULL
        LIMIT 10000
    '''
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    except Exception as e:
        # If JSON extraction fails, try as regular column
        if 'does not exist' in str(e).lower() or 'cannot cast' in str(e).lower():
            sql = f'''
                SELECT "{field_name}"
                FROM "{table_name}"
                WHERE {where_sql}
                AND "{field_name}" IS NOT NULL
                LIMIT 10000
            '''
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        else:
            raise
    
    if not rows:
        return [], 0, 0
    
    # Extract data and calculate bounds
    # Try to convert to float, skip non-numeric values
    data = []
    for row in rows:
        if row[0] is not None:
            try:
                data.append(float(row[0]))
            except (ValueError, TypeError):
                # Skip non-numeric values (e.g., "26-35" from agegroup)
                pass
    
    if not data:
        # No numeric data found - field is likely categorical
        return [], 0, 0
    
    data_array = np.array(data)
    
    return data, float(data_array.min()), float(data_array.max())


@api_view(["GET"])
def get_query_history(request, user_id):
    """
    Get query history for a user
    
    Shows all queries with fingerprints and budget multipliers
    """
    history = QueryFingerprintModel.objects.filter(
        user_id=user_id
    ).order_by('-timestamp')[:50]
    
    history_data = [
        {
            'timestamp': q.timestamp.isoformat(),
            'table': q.table_name,
            'field': q.field_name,
            'query_type': q.query_type,
            'filters': q.filters_json,
            'epsilon_cost': q.epsilon_cost,
            'budget_multiplier': q.budget_multiplier,
            'effective_cost': q.effective_cost,
            'result': q.result_value
        }
        for q in history
    ]
    
    return Response({
        'user_id': user_id,
        'total_queries': len(history_data),
        'history': history_data
    })
