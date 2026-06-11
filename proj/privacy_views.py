from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from .risk_engine import RiskAssessmentEngine
from .privacy_engine import PrivacyEngine
from .privacy_policies import PolicyLibrary, TransformationRules
import json


# =========================
# MAIN: RISK + PRIVATIZE
# =========================
@api_view(["POST"])
def assess_and_privatize(request):
    """
    ✅ SECURITY FIXED: Only returns privatized data, never original data
    
    This endpoint:
    1. Loads data from database or accepts records
    2. Assesses privacy risk
    3. Applies differential privacy transformations
    4. Returns ONLY privatized data (original data never exposed)
    """
    policy_name = request.data.get("policy", "standard")

    records = request.data.get("records")
    table_name = request.data.get("table_name")
    ALLOWED_SCHEMAS = {'public', 'railway', 'app_data'}
    schema = request.data.get("schema", "public")
    if schema not in ALLOWED_SCHEMAS:
        return Response({"error": f"Invalid schema. Allowed: {list(ALLOWED_SCHEMAS)}"}, status=400)
    
    save_to_db = request.data.get("save_to_db", False)

    # Load DB table if requested
    if table_name:
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', schema) or not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            return Response({"error": "Invalid table or schema name"}, status=400)
            
        try:
            with connection.cursor() as cursor:
                quoted_schema = connection.ops.quote_name(schema)
                quoted_table_name = connection.ops.quote_name(table_name)
                cursor.execute(f'SELECT * FROM {quoted_schema}.{quoted_table_name} LIMIT 500;')
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                records = [
                    {col: val for col, val in zip(columns, row)}
                    for row in rows
                ]

            if not records:
                return Response({"error": "Table exists but has no data"}, status=404)

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Table fetch failed: {str(e)}")
            return Response({"error": "Table fetch failed"}, status=500)

    if not records:
        return Response({"error": "records or table_name required"}, status=400)

    # ==========================
    # STEP 1 — RISK BEFORE
    # ==========================
    risk_engine = RiskAssessmentEngine()
    original_risk = risk_engine.analyze_dataset(records)

    # ==========================
    # STEP 2 — APPLY PRIVACY
    # ==========================
    privacy_engine = PrivacyEngine()

    from .column_classifier import ColumnClassifier

    classifier = ColumnClassifier()
    column_classifications = classifier.classify_columns(records)

    anonymized_records, privacy_metadata = privacy_engine.apply_privacy(
        records,
        column_classifications=column_classifications,
        risk_score=original_risk["risk_score"],
        policy_name=policy_name
    )

    # ⚠️ SECURITY NOTE: After this point, 'records' variable containing original data
    # is no longer used. The privacy_engine has already cleared it from memory.
    # Only 'anonymized_records' (privatized data) is used from here forward.

    # ==========================
    # STEP 3 — RISK AFTER
    # ==========================
    new_risk = risk_engine.analyze_dataset(anonymized_records)

    # ==========================
    # STEP 4 — RISK REDUCTION %
    # ==========================
    original_score = original_risk["risk_score"]
    new_score = new_risk["risk_score"]

    reduction = round(
        ((original_score - new_score) / original_score) * 100, 2
    ) if original_score > 0 else 0

    # ==========================
    # STEP 5 — SAVE TO DB (OPTIONAL)
    # ==========================
    db_saved = False

    if save_to_db and table_name:
        try:
            with connection.cursor() as cursor:
                # Create anonymized table if not exists
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS anonymized_records (
                        id SERIAL PRIMARY KEY,
                        source_table TEXT,
                        data JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # Insert anonymized rows
                for row in anonymized_records:
                    cursor.execute("""
                        INSERT INTO anonymized_records (source_table, data)
                        VALUES (%s, %s)
                    """, [table_name, json.dumps(row)])

            db_saved = True

        except Exception as e:
            return Response({"db_save_error": str(e)}, status=500)

    # ==========================
    # ✅ SECURE RESPONSE - ONLY PRIVATIZED DATA
    # ==========================
    return Response({
        "policy_used": policy_name,
        
        "risk_score": original_score,
        "risk_level": original_risk["risk_level"],
        
        "new_risk_score": new_score,
        "new_risk_level": new_risk["risk_level"],
        
        "risk_reduction_percent": reduction,
        
        "db_saved": db_saved,
        
        # ✅ ONLY PRIVATIZED DATA (all records, not sample)
        "privatized_data": anonymized_records,
        "record_count": len(anonymized_records),
        
        "privacy_metadata": privacy_metadata
    })
    # ❌ REMOVED: "original_sample" - NEVER expose original data
    # ❌ REMOVED: "original_risk_score" - redundant with "risk_score"


# =========================
# PRIVATIZE ONLY
# =========================
@api_view(["POST"])
def privatize_only(request):
    """
    Apply privacy transformations without risk assessment
    
    ✅ SECURITY: Only returns privatized data
    """
    records = request.data.get("records", [])
    policy_name = request.data.get("policy", "standard")

    if not records:
        return Response({"error": "records required"}, status=400)

    engine = PrivacyEngine()
    result = engine.privatize_only(records, policy_name)

    return Response(result, status=200)


# =========================
# COLUMN CLASSIFICATION
# =========================
@api_view(["POST"])
def classify_columns(request):
    """
    Classify columns by sensitivity type
    
    ✅ SECURITY: Only analyzes schema, doesn't expose data
    """
    records = request.data.get("records", [])

    if not records:
        return Response({"error": "records required"}, status=400)

    engine = PrivacyEngine()
    result = engine.classify_columns(records)

    return Response(result, status=200)


# =========================
# LIST POLICIES
# =========================
@api_view(["GET"])
def list_policies(request):
    """List available privacy policies"""
    policies = PolicyLibrary.list_available_policies()
    return Response({"policies": policies}, status=200)


# =========================
# VALIDATE POLICY
# =========================
@api_view(["POST"])
def validate_policy(request):
    """Validate a privacy policy configuration"""
    policy_name = request.data.get("policy", "standard")
    risk_score = request.data.get("risk_score", 50)

    policy = PolicyLibrary.get_policy(policy_name)
    compliant, issues = TransformationRules.validate_policy_compliance(policy, risk_score)

    return Response({
        "policy": policy_name,
        "compliant": compliant,
        "issues": issues
    })


# =========================
# COMPARE POLICIES
# =========================
@api_view(["POST"])
def compare_policies(request):
    """Compare multiple privacy policies"""
    policies = request.data.get("policies", ["standard", "strict"])

    results = []
    for name in policies:
        policy = PolicyLibrary.get_policy(name)
        results.append({
            "name": name,
            "epsilon": policy.epsilon,
            "k_anonymity": policy.k_anonymity,
            "utility_weight": policy.utility_weight
        })

    return Response({"comparison": results})


# =========================
# BRIDGE: HACKER -> GUARDIAN
# =========================
@api_view(["POST"])
def trigger_guardian_from_hacker(request):
    """
    Bridge endpoint: Hacker AI calls this when a vulnerability is found.
    Triggers Guardian AI to anonymize the affected data.
    """
    vulnerability = request.data.get("vulnerability", {})
    records = request.data.get("records", [])

    if not records:
        return Response({
            "status": "notification_received",
            "vulnerability": vulnerability,
            "message": "No records provided - Guardian notified, awaiting dataset.",
            "action_required": True
        }, status=200)

    from .column_classifier import ColumnClassifier
    classifier = ColumnClassifier()
    column_classifications = classifier.classify_columns(records)

    engine = PrivacyEngine()
    patched_records, metadata = engine.apply_privacy(
        records,
        column_classifications,
        risk_score=85,  # High risk - hacker found something
        policy_name="maximum"
    )

    return Response({
        "status": "guardian_applied",
        "triggered_by": vulnerability.get("attack", "unknown"),
        "severity": vulnerability.get("severity", "unknown"),
        "columns_patched": list(metadata.get("transformations", {}).keys()),
        "budget_remaining": metadata.get(
            "privacy_config", {}).get("epsilon_remaining", "unknown"),
        "escalations": metadata.get("columns_escalated_to_review", []),
        "record_count": len(patched_records)
    })