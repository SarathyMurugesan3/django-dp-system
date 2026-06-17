from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from .risk_engine import RiskAssessmentEngine
from .privacy_engine import PrivacyEngine
from .privacy_policies import PolicyLibrary, TransformationRules
import json
import os
import io
import csv
import re


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
    
    save_to_db_val = request.data.get("save_to_db", False)
    save_to_db = str(save_to_db_val).lower() == 'true'

    # Load DB table if requested
    if table_name:
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', schema) or not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            return Response({"error": "Invalid table or schema name"}, status=400)
            
        try:
            with connection.cursor() as cursor:
                quoted_table_name = connection.ops.quote_name(table_name)
                cursor.execute(f'SELECT * FROM {quoted_table_name} LIMIT 500;')
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
            return Response({"error": f"Table fetch failed: {str(e)}"}, status=400)

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
    # Determine DP parameters actually used so the post-privacy risk
    # assessment can apply a correct, analytically-motivated discount
    # instead of re-scoring the noisy integers at face value.
    privacy_config_used = privacy_metadata.get("privacy_config", {})
    epsilon_used = privacy_config_used.get("epsilon_total")

    # Count how many columns received DP noise vs non-DP anonymization
    transformations = privacy_metadata.get("transformations", {})
    dp_col_count = sum(
        1 for info in transformations.values()
        if info.get("privacy_guarantee") == "DIFFERENTIAL_PRIVACY"
    )
    anon_col_count = sum(
        1 for info in transformations.values()
        if info.get("privacy_guarantee") == "NON_DP_ANONYMIZATION"
    )

    new_risk = risk_engine.analyze_anonymized_dataset(
        anonymized_records,
        privacy_metadata
    )

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
                # Create anonymized table if not exists (MySQL-compatible)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS anonymized_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        source_table TEXT,
                        data JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        "primary_risk_drivers": original_risk.get("primary_risk_drivers", []),
        
        "new_risk_score": new_score,
        "new_risk_level": new_risk["risk_level"],
        "new_risk_drivers": new_risk.get("primary_risk_drivers", []),
        
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

# =========================
# PROOF: ORIGINAL VS ANONYMIZED
# =========================
@api_view(["POST"])
def anonymization_proof(request):
    """
    Returns a side-by-side comparison of the original dataset vs the anonymized dataset
    to prove that the privacy transformations are working correctly.
    """
    policy_name = request.data.get("policy", "standard")
    table_name = request.data.get("table_name")
    limit_val = request.data.get("limit", 5)
    try:
        limit = int(limit_val)
    except (TypeError, ValueError):
        limit = 5
        
    if not table_name:
        return Response({"error": "table_name is required"}, status=400)
        
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return Response({"error": "Invalid table or schema name"}, status=400)

    try:
        with connection.cursor() as cursor:
            quoted_table_name = connection.ops.quote_name(table_name)
            cursor.execute(f'SELECT * FROM {quoted_table_name} LIMIT {limit};')
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            records = [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Table fetch failed: {str(e)}")
        return Response({"error": f"Table fetch failed: {str(e)}"}, status=500)

    if not records:
        return Response({"error": "No records found in table"}, status=404)

    # Make a deep copy to keep original untouched
    import copy
    original_records = copy.deepcopy(records)

    # Classify Columns
    from .column_classifier import ColumnClassifier
    classifier = ColumnClassifier()
    column_classifications = classifier.classify_columns(records)

    # Pre-Privacy Risk
    risk_engine = RiskAssessmentEngine()
    initial_risk = risk_engine.analyze_dataset(records)

    # Apply Privacy
    engine = PrivacyEngine()
    anonymized_records, privacy_metadata = engine.apply_privacy(
        records,
        column_classifications,
        risk_score=initial_risk["risk_score"],
        policy_name=policy_name
    )

    # Pair them up
    proof = []
    for orig, anon in zip(original_records, anonymized_records):
        proof.append({
            "original": orig,
            "anonymized": anon
        })

    return Response({
        "table_name": table_name,
        "policy_applied": policy_name,
        "proof": proof,
        "risk_reduction": {
            "original_risk_score": initial_risk["risk_score"],
            "original_risk_level": initial_risk["risk_level"]
        },
        "metadata": privacy_metadata
    })


# =========================
# FILE UPLOAD & PROCESSING
# =========================
def sanitize_column(name):
    name = name.strip()
    name = re.sub(r'\W+', '_', name)  # replace spaces & symbols with underscore
    return name.lower()

def get_safe_columns(headers):
    seen = {'id'}  # Reserve 'id' for the auto-increment primary key in DB
    col_map = {}
    for col in headers:
        sanitized = sanitize_column(col)
        if not sanitized:
            sanitized = "empty_column"
        base = sanitized
        counter = 1
        while sanitized in seen:
            sanitized = f"{base}_{counter}"
            counter += 1
        seen.add(sanitized)
        col_map[col] = sanitized
    return col_map

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_and_anonymize_file(request):
    """
    POST /api/privacy/upload-file/
    
    Accepts:
      - file: Uploaded CSV or TXT file
      - plfs_type: Optional 'HH' or 'PER'. If FWF text, determines layout.
      - table_name: Optional custom table name in DB (defaults to dataset_<filename>)
      - policy: Optional privacy policy (default 'standard')
    """
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"error": "No file uploaded"}, status=400)
        
    plfs_type = request.data.get("plfs_type", "").upper()
    policy_name = request.data.get("policy", "standard")
    custom_table_name = request.data.get("table_name", "").strip()
    
    filename = uploaded_file.name
    filename_lower = filename.lower()
    
    # Determine table name
    if custom_table_name:
        # Sanitize custom table name
        sanitized_table = re.sub(r'\W+', '_', custom_table_name).lower()
        table_name = f"dataset_{sanitized_table}"
    else:
        # Generate from filename
        base_name = os.path.splitext(filename)[0]
        sanitized_name = re.sub(r'\W+', '_', base_name).lower()
        table_name = f"dataset_{sanitized_name}"
        
    # Read the file content
    try:
        content_bytes = uploaded_file.read()
    except Exception as e:
        return Response({"error": f"Failed to read file: {str(e)}"}, status=400)
        
    records = []
    headers = []
    
    # Check if CSV or text (FWF)
    if filename_lower.endswith(".csv"):
        # Parse CSV
        try:
            decoded_content = content_bytes.decode("utf-8", errors="replace")
        except Exception:
            decoded_content = content_bytes.decode("latin-1", errors="replace")
            
        csv_file = io.StringIO(decoded_content)
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames
        if not headers:
            return Response({"error": "Empty CSV or no headers found"}, status=400)
            
        for row in reader:
            clean_row = {str(k).strip(): (str(v).strip() if v is not None else "") for k, v in row.items()}
            records.append(clean_row)
    else:
        # Parse Fixed-Width Text File (PLFS)
        try:
            decoded_content = content_bytes.decode("latin-1", errors="replace")
        except Exception:
            decoded_content = content_bytes.decode("utf-8", errors="replace")
            
        lines = decoded_content.splitlines()
        if not lines:
            return Response({"error": "Empty text file"}, status=400)
            
        # Determine PLFS layout (HH or PER)
        from risk_assessment.management.commands.plfs_convert import HOUSEHOLD_LAYOUT, PERSON_LAYOUT
        
        layout = None
        if plfs_type == "HH":
            layout = HOUSEHOLD_LAYOUT
        elif plfs_type == "PER":
            layout = PERSON_LAYOUT
        else:
            # Auto-detect by checking line length of first non-empty line
            first_line = ""
            for line in lines:
                if line.strip():
                    first_line = line
                    break
            
            if len(first_line) >= 200:
                layout = PERSON_LAYOUT
                plfs_type = "PER"
            else:
                layout = HOUSEHOLD_LAYOUT
                plfs_type = "HH"
                
        headers = [col[0] for col in layout]
        slices = [(col[1] - 1, col[2]) for col in layout]
        
        for line in lines:
            raw = line.rstrip("\r\n")
            if not raw:
                continue
            row = {}
            for (start, end), header in zip(slices, headers):
                if start >= len(raw):
                    row[header] = ""
                else:
                    row[header] = raw[start:end].strip()
            records.append(row)
            
    if not records:
        return Response({"error": "No records parsed from the file"}, status=400)
        
    # Save parsed records to DB as structured table
    db_saved = False
    db_error = None
    try:
        col_map = get_safe_columns(headers)
        sql_columns = ", ".join([f"`{col_map[col]}` TEXT" for col in headers])
        
        with connection.cursor() as cursor:
            # Drop if exists and create new table
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{table_name}` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    {sql_columns}
                )
            """)
            
            # Batch insert
            cols_sql = ", ".join([f"`{col_map[c]}`" for c in headers])
            placeholders = ", ".join(["%s"] * len(headers))
            insert_sql = f"INSERT INTO `{table_name}` ({cols_sql}) VALUES ({placeholders})"
            
            BATCH_SIZE = 500
            batch = []
            for row in records:
                batch.append(tuple(row.get(c, "") for c in headers))
                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(insert_sql, batch)
                    batch = []
            if batch:
                cursor.executemany(insert_sql, batch)
        db_saved = True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to save uploaded file to database: {str(e)}")
        db_error = str(e)
        
    # Run Privacy Engine
    try:
        # Analyze risk before
        risk_engine = RiskAssessmentEngine()
        original_risk = risk_engine.analyze_dataset(records)
        
        # Apply privacy
        from .column_classifier import ColumnClassifier
        classifier = ColumnClassifier()
        column_classifications = classifier.classify_columns(records)
        
        privacy_engine = PrivacyEngine()
        anonymized_records, privacy_metadata = privacy_engine.apply_privacy(
            records,
            column_classifications=column_classifications,
            risk_score=original_risk["risk_score"],
            policy_name=policy_name
        )
        
        # Analyze risk after
        new_risk = risk_engine.analyze_anonymized_dataset(
            anonymized_records,
            privacy_metadata
        )
        
        reduction = round(
            ((original_risk["risk_score"] - new_risk["risk_score"]) / original_risk["risk_score"]) * 100, 2
        ) if original_risk["risk_score"] > 0 else 0
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Privacy engine failed on uploaded data: {str(e)}")
        return Response({
            "message": "File parsed successfully, but privacy engine analysis failed.",
            "table_name": table_name if db_saved else None,
            "db_saved": db_saved,
            "db_error": db_error,
            "record_count": len(records),
            "error_details": str(e)
        }, status=200)
        
    message = "File uploaded, parsed, and anonymized successfully."
    if db_saved:
        message += " Saved to database."
    else:
        message += f" (Database save skipped: {db_error})"
        
    return Response({
        "message": message,
        "table_name": table_name if db_saved else None,
        "db_saved": db_saved,
        "db_error": db_error,
        "record_count": len(records),
        "policy_used": policy_name,
        "plfs_detected_type": plfs_type if not filename_lower.endswith(".csv") else None,
        
        "risk_score": original_risk["risk_score"],
        "risk_level": original_risk["risk_level"],
        "primary_risk_drivers": original_risk.get("primary_risk_drivers", []),
        
        "new_risk_score": new_risk["risk_score"],
        "new_risk_level": new_risk["risk_level"],
        "new_risk_drivers": new_risk.get("primary_risk_drivers", []),
        
        "risk_reduction_percent": reduction,
        
        # Directly display data to user
        "original_data_preview": records[:50],  # Return preview to avoid massive payload size for huge files
        "privatized_data": anonymized_records,   # Return full anonymized data
        
        "privacy_metadata": privacy_metadata
    }, status=200)