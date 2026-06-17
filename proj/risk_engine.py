"""
Data Privacy & Risk Assessment Engine
Analyzes actual data values for re-identification risk
"""
import re
from typing import List, Dict, Any, Tuple
from collections import Counter


class RiskAssessmentEngine:
    """Evaluates datasets for identity, sensitivity, and re-identification risk"""

    def __init__(self):
        self.risk_score   = 0
        self.risk_drivers = []

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: analyze RAW (original) dataset
    # ─────────────────────────────────────────────────────────────────────────
    def analyze_dataset(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not records:
            return self._generate_output(10, ["No data to analyze"])

        sampled_records = self._sample_records(records)

        record_risks = []
        all_drivers  = []

        for record in sampled_records:
            risk, drivers = self._analyze_record(record)
            record_risks.append(risk)
            all_drivers.extend(drivers)

        final_risk           = self._calculate_final_risk(record_risks)
        consolidated_drivers = self._consolidate_drivers(all_drivers)

        return self._generate_output(final_risk, consolidated_drivers)

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC: analyze ANONYMIZED dataset  ← fully dynamic, no hardcoding
    #
    # Everything is computed from:
    #   • privacy_metadata["transformations"]  — what happened per column
    #   • the actual anonymized records        — what values look like now
    #
    # Score formula
    # ─────────────────────────────────────────────────────────────────────────
    def analyze_anonymized_dataset(
        self,
        records: List[Dict[str, Any]],
        privacy_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute residual risk score and drivers PURELY from:
          1. What transformations were actually applied (from metadata)
          2. What patterns still exist in the anonymized data
          3. How many columns remain partially or fully exposed

        Nothing here is hardcoded to a specific dataset or column count.
        Every number is derived from the real metadata for this run.
        """
        if not records:
            return self._generate_output(10, ["No data to analyze"])

        transformations: Dict[str, Any] = (privacy_metadata or {}).get("transformations", {})
        privacy_config: Dict[str, Any]  = (privacy_metadata or {}).get("privacy_config", {})

        # ── If no metadata at all, fall back to raw analysis ──────────────────
        if not transformations:
            return self.analyze_dataset(records)

        total_cols = len(transformations)

        # ── Step 1: Categorise every column by what was applied ───────────────
        # These lists are built from the actual metadata — completely dynamic.
        dp_cols           = []   # numeric + DIFFERENTIAL_PRIVACY
        hashed_cols       = []   # identifier hashed/pseudonymized/redacted
        masked_cols       = []   # quasi_identifier masked/k-anonymised
        generalized_cols  = []   # temporal/geospatial generalised/bucketed
        suppressed_cols   = []   # explicit suppression
        untouched_cols    = []   # generic / no known transformation

        for col, info in transformations.items():
            mechanism         = (info.get("mechanism") or "").lower()
            privacy_guarantee = (info.get("privacy_guarantee") or "").upper()
            col_type          = (info.get("type") or "").lower()
            sensitivity       = (info.get("sensitivity") or "").lower()

            # Infer mechanism from type when not set
            if not mechanism:
                if col_type == "identifier":
                    mechanism = "hashing"
                elif col_type == "sensitive":
                    mechanism = "redaction"
                elif col_type in ("quasi_identifier",):
                    mechanism = "k_anonymity"
                elif col_type in ("temporal", "geospatial"):
                    mechanism = "generalization"
                elif col_type == "numeric":
                    mechanism = "laplace_noise"

            if "DIFFERENTIAL_PRIVACY" in privacy_guarantee or mechanism in (
                "laplace_noise", "gaussian_noise", "exponential", "dp"
            ):
                dp_cols.append(col)

            elif mechanism in ("hashing", "pseudonymization", "redaction"):
                hashed_cols.append(col)

            elif mechanism in ("masking", "k_anonymity", "suppression"):
                if mechanism == "suppression":
                    suppressed_cols.append(col)
                else:
                    masked_cols.append(col)

            elif mechanism in ("generalization", "bucketing", "rounding", "truncation"):
                generalized_cols.append(col)

            else:
                untouched_cols.append(col)

        # ── Step 2: Compute protection weight per column ──────────────────────
        # Each protection type gets a weight (0-1) representing how much risk
        # it removes. These weights are fixed constants (DP > hashing > masking
        # > generalization > suppression > untouched) and are applied to the
        # actual column counts from this specific run.
        WEIGHTS = {
            "dp":          1.00,   # strongest — formal ε-DP
            "hashed":      0.95,   # irreversible; direct ID gone
            "masked":      0.70,   # quasi-ID partially obscured
            "generalized": 0.55,   # range/bucket — some granularity left
            "suppressed":  0.40,   # value removed but field still exists
            "untouched":   0.00,   # no protection at all
        }

        weighted_protection = (
            len(dp_cols)          * WEIGHTS["dp"]
            + len(hashed_cols)    * WEIGHTS["hashed"]
            + len(masked_cols)    * WEIGHTS["masked"]
            + len(generalized_cols) * WEIGHTS["generalized"]
            + len(suppressed_cols)  * WEIGHTS["suppressed"]
            + len(untouched_cols)   * WEIGHTS["untouched"]
        )

        # Coverage = fraction of total risk removed across all columns
        coverage = (weighted_protection / total_cols) if total_cols > 0 else 0.0
        coverage = min(coverage, 1.0)

        # ── Step 3: Check what still looks risky in the anonymized data ────────
        # Run the standard record-level checks on the anonymized records.
        # Values that _is_anonymized_value() recognises (hashes, [DATE],
        # ranges, etc.) are skipped automatically inside those checks —
        # so the residual score reflects only what genuinely wasn't masked.
        sampled = self._sample_records(records)
        residual_risks   = []
        residual_drivers = []

        for record in sampled:
            risk, drivers = self._analyze_record(record)
            residual_risks.append(risk)
            residual_drivers.extend(drivers)

        residual_score = self._calculate_final_risk(residual_risks) if residual_risks else 0

        # ── Step 4: Blend coverage discount with residual signal ──────────────
        # Final score = weighted mix of:
        #   a) what the data-level scanner still sees as risky (60%)
        #   b) discount implied by the protection coverage (40%)
        #
        # This means:
        #   • If DP + hashing covered 95% of columns → big discount
        #   • But if scanner still finds real patterns (e.g. GPS still exact)
        #     → that residual signal drags the score back up
        discount_factor  = coverage * 0.40           # max 40% from coverage alone
        blended_score    = residual_score * (1.0 - discount_factor)

        # Floor: we can never claim 0 risk; minimum is 5% of residual
        floor_score  = max(5.0, residual_score * 0.05)
        final_score  = max(blended_score, floor_score)
        final_score  = int(max(0, min(100, round(final_score))))

        # ── Step 5: Build dynamic driver list ─────────────────────────────────
        # Every line is derived from the actual column counts & epsilon value
        # for this run. None of these are hardcoded strings.
        drivers = []

        if dp_cols:
            eps = privacy_config.get("epsilon_total", "?")
            drivers.append(
                f"{len(dp_cols)} numeric column(s) protected with "
                f"Differential Privacy (ε={eps})"
            )

        if hashed_cols:
            drivers.append(
                f"{len(hashed_cols)} identifier(s) hashed/pseudonymized — "
                f"direct re-identification removed"
            )

        if masked_cols:
            drivers.append(
                f"{len(masked_cols)} quasi-identifier(s) masked/k-anonymized — "
                f"partial linkage risk remains"
            )

        if generalized_cols:
            drivers.append(
                f"{len(generalized_cols)} column(s) generalized/bucketed — "
                f"exact values no longer present"
            )

        if suppressed_cols:
            drivers.append(
                f"{len(suppressed_cols)} column(s) suppressed — "
                f"values removed but field exists"
            )

        if untouched_cols:
            # Name the first 3 unprotected columns so the user knows exactly
            # which ones are still exposed — this is fully data-driven
            sample_names = ", ".join(untouched_cols[:3])
            more         = f" (+{len(untouched_cols)-3} more)" if len(untouched_cols) > 3 else ""
            drivers.append(
                f"{len(untouched_cols)} column(s) received no protection "
                f"({sample_names}{more}) — residual risk"
            )

        # Add residual data-pattern warning if scanner still found real risk
        if residual_score > 30 and residual_drivers:
            top_residual = self._consolidate_drivers(residual_drivers)
            drivers.append(
                f"Residual data patterns detected: {top_residual[0]}"
                if top_residual else
                "Residual data patterns still detectable in anonymized values"
            )

        if not drivers:
            drivers = ["Full protection applied — no significant residual risk detected"]

        return self._generate_output(final_score, drivers)

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL helpers (unchanged from original)
    # ─────────────────────────────────────────────────────────────────────────
    def _sample_records(self, records: List[Dict]) -> List[Dict]:
        n = len(records)
        if n <= 15:
            return records
        first_5       = records[:5]
        middle_start  = (n // 2) - 2
        middle_5      = records[middle_start:middle_start + 5]
        last_5        = records[-5:]
        return first_5 + middle_5 + last_5

    def _analyze_record(self, record: Dict[str, Any]) -> Tuple[float, List[str]]:
        risk_factors = []
        drivers      = []

        values           = [v for v in record.values() if v is not None and str(v).strip()]
        field_value_pairs = [(k, v) for k, v in record.items() if v is not None and str(v).strip()]

        if not values:
            return 10, ["Empty record"]

        unique_risk,      unique_drivers      = self._check_uniqueness(values)
        sensitivity_risk, sensitivity_drivers = self._check_sensitivity(field_value_pairs)
        combination_risk, combination_drivers = self._check_combination_risk(values)
        precision_risk,   precision_drivers   = self._check_precision(values)

        risk_factors.extend([unique_risk, sensitivity_risk, combination_risk, precision_risk])
        drivers.extend(unique_drivers + sensitivity_drivers + combination_drivers + precision_drivers)

        record_risk = self._combine_risk_factors(risk_factors)
        return record_risk, drivers

    def _combine_risk_factors(self, risk_factors: List[float]) -> float:
        active = [f for f in risk_factors if f and f > 0]
        if not active:
            return 0.0
        prob_none = 1.0
        for f in active:
            p          = max(0.0, min(1.0, f / 100.0))
            prob_none *= (1.0 - p)
        return min(100.0, (1.0 - prob_none) * 100.0)

    def _is_anonymized_value(self, val_str: str) -> bool:
        if re.match(r'^[a-f0-9]{32,}$', val_str, re.I):
            return True
        if val_str.endswith('...'):
            return True
        if val_str in ('[REDACTED]', '[DATE]', '[LOCATION]', '***', 'REDACTED'):
            return True
        if re.match(r'^\d+[k]?[-–]\d+[k]?$', val_str):
            return True
        return False

    def _check_uniqueness(self, values: List[Any]) -> Tuple[float, List[str]]:
        drivers = []
        hits    = []
        for val in values:
            val_str = str(val)
            if self._is_anonymized_value(val_str):
                continue
            if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', val_str, re.I):
                hits.append(80)
                drivers.append("UUID-like identifiers present")
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', val_str):
                hits.append(90)
                drivers.append("Email addresses detected (direct identifiers)")
            if re.match(r'^\+?\d{10,13}$', val_str):
                hits.append(80)
                drivers.append("Phone numbers detected")
            if len(val_str) > 20 and not re.match(r'^[a-f0-9]+$', val_str, re.I):
                hits.append(50)
                drivers.append("Long unique values detected")
            if re.match(r'^\d+\.\d{4,}$', val_str):
                hits.append(50)
                drivers.append("Highly precise numerical values")
        return self._combine_risk_factors(hits), drivers

    def _check_sensitivity(self, field_value_pairs: List[Tuple[str, Any]]) -> Tuple[float, List[str]]:
        drivers = []
        hits    = []

        sensitive_patterns = {
            r'\b(password|passwd|pwd|secret)\b':            ("Potential credential data", 100),
            r'\b(ssn|social.security)\b':                   ("Social security patterns", 100),
            r'\b(credit.card|card.number|cvv)\b':           ("Financial data patterns", 100),
            r'\b(diagnosis|medical|health|patient)\b':      ("Healthcare-related data", 90),
            r'\b(salary|income|wage|compensation)\b':       ("Financial compensation data", 80),
            r'\b(address|street|apartment)\b':              ("Location data detected", 70),
            r'\b(zip|zipcode|postal.?code|pincode)\b':      ("Postal/zip code (quasi-identifier)", 35),
            r'\b(birth|dob)\b':                             ("Birth date data", 55),
            r'\bage\b':                                     ("Age data present", 35),
        }

        name_field_pattern = r'\b(full.?name|first.?name|last.?name|surname|customer.?name|patient.?name)\b'

        for field_name, val in field_value_pairs:
            val_str_raw = str(val)
            if self._is_anonymized_value(val_str_raw):
                continue

            field_str = str(field_name).lower()
            if re.search(name_field_pattern, field_str, re.I):
                hits.append(65)
                if "Personal name field detected (quasi-identifier)" not in drivers:
                    drivers.append("Personal name field detected (quasi-identifier)")
            elif field_str.strip() == 'name':
                hits.append(50)
                if "Generic 'name' field detected" not in drivers:
                    drivers.append("Generic 'name' field detected")

            val_str       = val_str_raw.lower()
            combined_text = f"{field_str} {val_str}"

            for pattern, (driver, pattern_risk) in sensitive_patterns.items():
                if re.search(pattern, combined_text, re.I):
                    hits.append(pattern_risk)
                    if driver not in drivers:
                        drivers.append(driver)

            if re.match(r'^\d{1,3}$', str(val)) and 0 < int(str(val)) < 120:
                hits.append(25)
                if "Precise age values present" not in drivers:
                    drivers.append("Precise age values present")

        return self._combine_risk_factors(hits), drivers

    def _check_combination_risk(self, values: List[Any]) -> Tuple[int, List[str]]:
        drivers    = []
        risk       = 0
        num_values = len(values)
        if num_values >= 15:
            risk = max(risk, 50)
            drivers.append(f"High attribute count ({num_values} fields) increases re-identification risk")
        elif num_values >= 8:
            risk = max(risk, 35)
            drivers.append(f"Multiple attributes ({num_values} fields) enable linking attacks")
        elif num_values >= 4:
            risk = max(risk, 20)
            drivers.append("Combination of multiple data points")
        return risk, drivers

    def _check_precision(self, values: List[Any]) -> Tuple[float, List[str]]:
        drivers = []
        hits    = []
        for val in values:
            val_str = str(val)
            if self._is_anonymized_value(val_str):
                continue
            if re.match(r'\d{4}-\d{2}-\d{2}.\d{2}:\d{2}:\d{2}', val_str):
                hits.append(70)
                drivers.append("Precise timestamps enable temporal correlation")
            if re.match(r'^-?\d+\.\d{4,},\s*-?\d+\.\d{4,}$', val_str):
                hits.append(90)
                drivers.append("GPS coordinates (exact location data)")
            if re.match(r'^\d+\.\d{4,}$', val_str):
                hits.append(60)
                drivers.append("High-precision measurements")
        return self._combine_risk_factors(hits), drivers

    def _calculate_final_risk(self, record_risks: List[float]) -> int:
        if not record_risks:
            return 10
        max_risk = max(record_risks)
        avg_risk = sum(record_risks) / len(record_risks)
        combined = (max_risk * 0.4) + (avg_risk * 0.6)
        return int(max(0, min(100, round(combined))))

    def _consolidate_drivers(self, all_drivers: List[str]) -> List[str]:
        driver_counts  = Counter(all_drivers)
        unique_drivers = sorted(driver_counts.items(), key=lambda x: x[1], reverse=True)
        return [driver for driver, _ in unique_drivers[:5]]

    def _generate_output(self, risk_score: int, drivers: List[str]) -> Dict[str, Any]:
        if risk_score <= 20:
            level = "Very Low Risk"
        elif risk_score <= 40:
            level = "Low Risk"
        elif risk_score <= 60:
            level = "Moderate Risk"
        elif risk_score <= 80:
            level = "High Risk"
        else:
            level = "Very High Risk"

        filled = int((risk_score / 100) * 20)
        meter  = "█" * filled + "░" * (20 - filled)

        return {
            "risk_score":          risk_score,
            "risk_level":          level,
            "risk_meter":          f"[{meter}] {risk_score} / 100",
            "primary_risk_drivers": drivers if drivers else ["Insufficient data for detailed analysis"],
        }