"""
Database Query Endpoint

Allows users to query database tables with DP protection.
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection
from .privacy_engine import PrivacyEngine, QueryType
from .db_budget_manager import DatabaseBudgetWrapper
from django.utils import timezone
import numpy as np


# Use wrapper for PrivacyEngine compatibility
budget_manager_wrapper = DatabaseBudgetWrapper()


@api_view(["POST"])
def execute_db_query(request):
    """
    Execute differential privacy query on database table
    """
    import traceback
    try:
        user_id = request.data.get("user_id", "default")
        table_name = request.data.get("table_name")
        field_name = request.data.get("field_name")
        query_type_str = request.data.get("query_type", "mean")
        filters = request.data.get("filters", {})

        response_data, status_code = process_db_query(user_id, table_name, field_name, query_type_str, filters)
        return Response(response_data, status=status_code)
    except Exception as e:
        # Catch ALL uncaught errors and return as JSON so we can debug
        return Response({
            "error": "Unexpected server error",
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }, status=500)


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
    
    # Get user's team_id for metadata
    from .privacy_budget_models import PrivacyBudgetLedger as LedgerModel
    try:
        user_ledger = LedgerModel.objects.get(user_id=user_id)
        team_id = user_ledger.team_id
    except LedgerModel.DoesNotExist:
        team_id = None
        
    budget_multiplier = 1.0
    
    # Fetch data from database
    try:
        data, data_min, data_max = fetch_data_from_db(table_name, field_name, filters)
    except ValueError as e:
        # User input error (e.g., unknown filter column) — return 400
        return {
            "error": "Invalid filter",
            "message": str(e)
        }, 400
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
                        where_clauses.append(f'`{field}` {operator} %s')
                        params.append(value)
                    else:
                        where_clauses.append(f'`{field}` = %s')
                        params.append(condition)
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                sql = f'SELECT COUNT(*) FROM `{table_name}` WHERE {where_sql}'
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
    
    # Auto-detect bounds from data
    if query_type == QueryType.COUNT:
        lower_bound = 0
        upper_bound = data_max * 1.1
    else:
        lower_bound = float(data_min) - (data_max - data_min) * 0.1
        upper_bound = float(data_max) + (data_max - data_min) * 0.1
    
    # Execute DP query with budget multiplier
    engine = PrivacyEngine(budget_manager=budget_manager_wrapper)
    
    # Get base epsilon
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
    
    # Add metadata to response
    metadata['budget_multiplier'] = budget_multiplier
    metadata['base_epsilon_cost'] = base_epsilon_cost
    metadata['effective_epsilon_cost'] = round(effective_epsilon_cost, 6)
    metadata['data_points'] = len(data)
    metadata['data_range'] = [round(data_min, 2), round(data_max, 2)]
    metadata['team_id'] = team_id
    
    return {
        "result": result,
        "metadata": metadata,
    }, 200



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
    
    # Validate filter columns against actual table schema (skip for JSON tables)
    if filters and table_name.lower() != 'dataset_records':
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                actual_columns = {row[0].lower() for row in cursor.fetchall()}
            unknown_fields = [
                f for f in filters.keys()
                if f.lower() not in actual_columns
            ]
            if unknown_fields:
                raise ValueError(
                    f"Unknown filter column(s) {unknown_fields} in table '{table_name}'. "
                    f"Available columns: {sorted(actual_columns)}"
                )
        except ValueError:
            raise  # Re-raise our own validation error
        except Exception:
            pass  # If SHOW COLUMNS itself fails, let the main query fail naturally

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
                # JSON field access for MySQL: JSON_UNQUOTE(JSON_EXTRACT(data, '$.FieldName'))
                where_clauses.append(f"CAST(JSON_UNQUOTE(JSON_EXTRACT(data, %s)) AS CHAR) {operator} %s")
                params.append(f'$.{field}')
                params.append(str(value))
            else:
                # Regular column — use backticks for MySQL
                where_clauses.append(f'`{field}` {operator} %s')
                params.append(value)
        else:
            # Simple equality
            if table_name.lower() == 'dataset_records':
                where_clauses.append(f"JSON_UNQUOTE(JSON_EXTRACT(data, %s)) = %s")
                params.append(f'$.{field}')
                params.append(str(condition))
            else:
                where_clauses.append(f'`{field}` = %s')
                params.append(condition)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Build SELECT clause based on table type
    if table_name.lower() == 'dataset_records':
        # Extract from JSON column — MySQL syntax
        select_clause = f"CAST(JSON_UNQUOTE(JSON_EXTRACT(data, '$.{field_name}')) AS DECIMAL(20,6))"
        null_check = f"JSON_EXTRACT(data, '$.{field_name}') IS NOT NULL"
    else:
        # Regular column — use backticks for MySQL
        select_clause = f'`{field_name}`'
        null_check = f'`{field_name}` IS NOT NULL'
    
    # Build SQL query — backtick table name for MySQL
    sql = f'''
        SELECT {select_clause}
        FROM `{table_name}`
        WHERE {where_sql}
        AND {null_check}
        LIMIT 10000
    '''
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    except Exception as e:
        # If JSON extraction fails on the SELECT field, try as regular column.
        # Only fall back when the error is about the SELECT field, not a WHERE filter.
        err_str = str(e).lower()
        if ('does not exist' in err_str or 'cannot cast' in err_str) and 'unknown column' not in err_str:
            sql = f'''
                SELECT `{field_name}`
                FROM `{table_name}`
                WHERE {where_sql}
                AND `{field_name}` IS NOT NULL
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
    from .privacy_budget_models import PrivacyBudgetLedger
    try:
        ledger = PrivacyBudgetLedger.objects.get(user_id=user_id)
        history = ledger.transactions.all().order_by('-timestamp')[:50]
        history_data = [
            {
                'timestamp': q.timestamp.isoformat(),
                'query_type': q.query_type,
                'epsilon_cost': q.epsilon_cost,
                'mechanism': q.mechanism_used,
            }
            for q in history
        ]
    except PrivacyBudgetLedger.DoesNotExist:
        history_data = []
        
    return Response({
        'user_id': user_id,
        'total_queries': len(history_data),
        'history': history_data
    })


@api_view(["GET"])
def list_tables(request):
    """
    List available database tables for querying
    """
    all_tables = connection.introspection.table_names()
    
    # Filter out system tables and Django internal tables
    filtered_tables = [
        t for t in all_tables 
        if not t.startswith('django_') 
        and not t.startswith('auth_') 
        and not t.startswith('privacy_')  # Hide internal privacy system tables
        and t not in ['sqlite_sequence']
    ]
    
    # Add descriptions/metadata if available (optional)
    tables_meta = []
    for t in filtered_tables:
        tables_meta.append({
            "table_name": t,
            "display_name": t.replace('_', ' ').title(),
            "type": "structured"
        })
        
    return Response({
        "tables": tables_meta,
        "count": len(tables_meta)
    })
