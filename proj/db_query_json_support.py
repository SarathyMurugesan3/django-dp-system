"""
Database Query Endpoint with Query Fingerprinting - UPDATED for JSON support

Allows users to query database tables with DP protection and
detects repeated queries to prevent privacy leakage.

SUPPORTS:
- Regular columns (any dataset table)
- JSON columns (dataset_records.data)
"""

from django.db import connection
import numpy as np


def fetch_data_from_db_json(table_name: str, field_name: str, filters: dict) -> tuple:
    """
    Fetch data from database table with filters.
    Supports both regular columns and JSON columns (dataset_records).

    Returns:
        (data_list, min_value, max_value)
    """
    # Build WHERE clause from filters
    where_clauses = []
    params = []

    for field, condition in filters.items():
        if isinstance(condition, dict):
            operator = condition.get('operator', '=')
            value = condition.get('value')

            # Sanitize operator — only allow safe operators
            allowed_operators = ['=', '>', '<', '>=', '<=', '!=', 'LIKE', 'IN']
            if operator.upper() not in allowed_operators:
                operator = '='

            if table_name.lower() == 'dataset_records' and field != 'dataset_name':
                # MySQL JSON field access
                where_clauses.append(
                    f"CAST(JSON_UNQUOTE(JSON_EXTRACT(data, %s)) AS CHAR) {operator} %s"
                )
                params.append(f'$.{field}')
                params.append(str(value))
            else:
                # Regular column — use backticks for MySQL identifiers
                where_clauses.append(f'`{field}` {operator} %s')
                params.append(value)
        else:
            # Simple equality (non-dict condition)
            if table_name.lower() == 'dataset_records':
                where_clauses.append("JSON_UNQUOTE(JSON_EXTRACT(data, %s)) = %s")
                params.append(f'$.{field}')
                params.append(str(condition))
            else:
                where_clauses.append(f'`{field}` = %s')
                params.append(condition)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Build SELECT clause
    if table_name.lower() == 'dataset_records':
        # MySQL JSON numeric extraction
        select_clause = f"CAST(JSON_UNQUOTE(JSON_EXTRACT(data, '$.{field_name}')) AS DECIMAL(20,6))"
        null_check = f"JSON_EXTRACT(data, '$.{field_name}') IS NOT NULL"
    else:
        # Regular column — backticks for MySQL
        select_clause = f'`{field_name}`'
        null_check = f'`{field_name}` IS NOT NULL'

    # Final SQL — backtick table name for MySQL
    sql = f"""
        SELECT {select_clause}
        FROM `{table_name}`
        WHERE {where_sql}
        AND {null_check}
        LIMIT 10000
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    except Exception as e:
        err_str = str(e).lower()
        # Fallback to plain column if JSON extraction failed
        if 'does not exist' in err_str or 'cannot cast' in err_str or 'unknown column' in err_str:
            sql = f"""
                SELECT `{field_name}`
                FROM `{table_name}`
                WHERE {where_sql}
                AND `{field_name}` IS NOT NULL
                LIMIT 10000
            """
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        else:
            raise

    if not rows:
        return [], 0, 0

    # Convert to float, skip non-numeric rows
    data = []
    for row in rows:
        if row[0] is not None:
            try:
                data.append(float(row[0]))
            except (ValueError, TypeError):
                pass

    if not data:
        return [], 0, 0

    data_array = np.array(data)
    return data, float(data_array.min()), float(data_array.max())
