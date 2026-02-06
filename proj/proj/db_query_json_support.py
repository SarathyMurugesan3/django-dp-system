"""
Database Query Endpoint with Query Fingerprinting - UPDATED for JSON support

Allows users to query database tables with DP protection and
detects repeated queries to prevent privacy leakage.

SUPPORTS:
- Regular columns (demographics table)
- JSON columns (dataset_records.data)
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


def get_postgres_type(value):
    """Determine PostgreSQL type for casting"""
    if isinstance(value, (int, float)):
        return 'numeric'
    elif isinstance(value, bool):
        return 'boolean'
    else:
        return 'text'


def fetch_data_from_db_json(table_name: str, field_name: str, filters: dict) -> tuple:
    """
    Fetch data from database table with filters
    Supports both regular columns and JSON columns
    
    Returns:
        (data_array, min_value, max_value)
    """
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
            
            # Check if this is a JSON field access
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
    data = [float(row[0]) for row in rows if row[0] is not None]
    
    if not data:
        return [], 0, 0
    
    data_array = np.array(data)
    
    return data, float(data_array.min()), float(data_array.max())
