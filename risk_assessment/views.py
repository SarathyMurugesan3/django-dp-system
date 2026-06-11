from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
import sys
import os
from risk_assessment.models import DatasetRecord
from proj.risk_engine import RiskAssessmentEngine


# ============================
# DATASET STORED RECORD RISK
# ============================
@api_view(["POST"])
def assess_dataset_risk(request):
    dataset_name = request.data.get("dataset_name")

    if not dataset_name:
        return Response({"error": "dataset_name required"}, status=400)

    records = [
        obj.data for obj in DatasetRecord.objects.filter(dataset_name=dataset_name)
    ]

    if not records:
        return Response({"error": "No records found"}, status=404)

    engine = RiskAssessmentEngine()
    risk_result = engine.analyze_dataset(records)

    return Response({
        "dataset": dataset_name,
        "record_count": len(records),
        "risk_result": risk_result
    })


# ============================
# TABLE RISK ASSESSMENT
# ============================
@api_view(['POST'])
def assess_table_risk(request):
    table_name = request.data.get('table_name')
    schema = request.data.get('schema', 'public')

    if not table_name:
        return Response({"error": "table_name is required"}, status=400)

    try:
        records = fetch_table_data(table_name, schema)

        if not records:
            return Response(
                {"error": "No data found or table does not exist"},
                status=404
            )

        engine = RiskAssessmentEngine()
        result = engine.analyze_dataset(records)

        result['metadata'] = {
            'table_name': table_name,
            'schema': schema,
            'total_records': len(records),
            'analyzed_records': min(len(records), 15)
        }

        return Response(result, status=200)

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"assess_table_risk failed: {str(e)}")
        return Response({"error": "Risk assessment failed"}, status=500)


# ============================
# LIST DATABASE TABLES
# ============================
@api_view(['GET'])
def list_tables(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN (
                    'information_schema',
                    'mysql',
                    'performance_schema',
                    'sys'
                )
                AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name;
            """)

            tables = [{"schema": row[0], "table_name": row[1]} for row in cursor.fetchall()]

        return Response({"tables": tables, "count": len(tables)}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ============================
# QUERY RISK ASSESSMENT
# ============================
@api_view(['POST'])
def assess_query_risk(request):
    query = request.data.get('query', '').strip()

    if not query:
        return Response({"error": "query required"}, status=400)

    query_upper = query.upper()

    if not query_upper.startswith('SELECT'):
        return Response({"error": "Only SELECT queries allowed"}, status=400)

    blocked = ['DROP','DELETE','TRUNCATE','ALTER','INSERT',
               'UPDATE','EXEC','EXECUTE','UNION','SLEEP',
               'BENCHMARK','OUTFILE','LOAD_FILE']
    for word in blocked:
        if word in query_upper:
            return Response({"error": f"Disallowed keyword: {word}"}, status=400)

    if 'LIMIT' not in query_upper:
        query = query.rstrip(';') + ' LIMIT 100'
        
    # Prevent multiple statements
    if query.count(';') > 1 or (query.count(';') == 1 and not query.rstrip().endswith(';')):
        return Response({"error": "Multiple statements not allowed"}, status=400)
    
    # Strip trailing semicolon before execution
    query = query.rstrip(';')

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            records = [
                {col: (val if val is not None else "")
                 for col, val in zip(columns, row)}
                for row in rows
            ]
        if not records:
            return Response({"error": "No results"}, status=404)

        engine = RiskAssessmentEngine()
        result = engine.analyze_dataset(records)
        return Response({"record_count": len(records), "risk_result": result})

    except Exception:
        return Response({"error": "Query execution failed"}, status=500)


# ============================
# SAFE TABLE FETCHER
# ============================
def fetch_table_data(table_name, schema='public'):
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', schema):
        return []
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return []

    with connection.cursor() as cursor:

        # Validate table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
            );
        """, [schema, table_name])

        exists = cursor.fetchone()[0]

        if not exists:
            return []

        quoted_table = connection.ops.quote_name(table_name)
        cursor.execute(f'SELECT * FROM {quoted_table} LIMIT 500;')

        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

        records = []

        for row in rows:
            clean_row = {}
            for col, val in zip(columns, row):
                clean_row[col] = val if val is not None else ""
            records.append(clean_row)

        return records
