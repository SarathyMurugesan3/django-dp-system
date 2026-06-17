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
        self.risk_score = 0
        self.risk_drivers = []
        
    def analyze_dataset(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze dataset and return risk assessment
        
        Args:
            records: List of dictionaries representing database records
            
        Returns:
            Dictionary with risk score, level, and drivers
        """
        if not records:
            return self._generate_output(10, ["No data to analyze"])
        
        # Sample records according to strategy
        sampled_records = self._sample_records(records)
        
        # Analyze each record
        record_risks = []
        all_drivers = []
        
        for record in sampled_records:
            risk, drivers = self._analyze_record(record)
            record_risks.append(risk)
            all_drivers.extend(drivers)
        
        # Calculate overall risk
        final_risk = self._calculate_final_risk(record_risks)
        
        # Consolidate risk drivers
        consolidated_drivers = self._consolidate_drivers(all_drivers)
        
        return self._generate_output(final_risk, consolidated_drivers)
    
    def _sample_records(self, records: List[Dict]) -> List[Dict]:
        """Sample first 5, middle 5, and last 5 records"""
        n = len(records)
        
        if n <= 15:
            return records
        
        first_5 = records[:5]
        middle_start = (n // 2) - 2
        middle_5 = records[middle_start:middle_start + 5]
        last_5 = records[-5:]
        
        return first_5 + middle_5 + last_5
    
    def _analyze_record(self, record: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        Analyze a single record for identifiability and sensitivity

        Returns:
            Tuple of (risk_score, list_of_drivers)

        NOTE ON SCORING MODEL:
        Earlier versions took max() across the four risk-factor checks, which
        meant a single severe hit (e.g. one email at 90) saturated the record
        score identically whether that was the *only* problem or one of many
        simultaneous severe problems (SSN + credit card + GPS + email, etc).
        That caused unrelated "high risk" datasets to all collapse to the same
        rounded score (commonly 90 or 100).

        Fixed model: each check still reports its own peak severity (so a
        single email is still flagged at its correct severity), but the
        record-level score now combines severity with breadth — i.e. how
        many *independent* risk categories fired — using a soft saturating
        sum instead of a hard max. This keeps "1 weak signal" and "many
        severe signals" distinguishable while still capping at 100.
        """
        risk_factors = []
        drivers = []

        values = [v for v in record.values() if v is not None and str(v).strip()]
        # Field/value pairs (for checks that need the column name, e.g.
        # detecting a column literally named "ssn" or "salary" — the value
        # itself, like "123-45-6789" or 95000, doesn't contain that word).
        field_value_pairs = [
            (k, v) for k, v in record.items() if v is not None and str(v).strip()
        ]

        if not values:
            return 10, ["Empty record"]

        # 1. Check for uniqueness indicators
        unique_risk, unique_drivers = self._check_uniqueness(values)
        risk_factors.append(unique_risk)
        drivers.extend(unique_drivers)

        # 2. Check for sensitive data patterns (by column name AND value)
        sensitivity_risk, sensitivity_drivers = self._check_sensitivity(field_value_pairs)
        risk_factors.append(sensitivity_risk)
        drivers.extend(sensitivity_drivers)

        # 3. Check combination risk
        combination_risk, combination_drivers = self._check_combination_risk(values)
        risk_factors.append(combination_risk)
        drivers.extend(combination_drivers)

        # 4. Check for precise/granular data
        precision_risk, precision_drivers = self._check_precision(values)
        risk_factors.append(precision_risk)
        drivers.extend(precision_drivers)

        # Calculate record risk using severity + breadth instead of plain max.
        record_risk = self._combine_risk_factors(risk_factors)

        return record_risk, drivers

    def _combine_risk_factors(self, risk_factors: List[float]) -> float:
        """
        Combine multiple independent 0-100 risk-factor scores into one
        record-level score using a soft saturating sum (probabilistic OR).

        Treat each factor as an independent "probability of being
        identifiable" in [0,1] (factor/100). The combined probability that
        AT LEAST ONE factor causes identification is:

            p_combined = 1 - product(1 - p_i)

        This means:
          - A single 90 stays close to 90 (one severe factor still drives
            most of the score).
          - Multiple simultaneous severe factors (e.g. 90 + 100 + 80 + 90)
            push the combined score above any single one of them, capped
            at 100 — instead of being indistinguishable from a single 90.
          - Multiple weak factors (e.g. several 20s) accumulate
            meaningfully instead of being thrown away by max().
        """
        active = [f for f in risk_factors if f and f > 0]
        if not active:
            return 0.0

        prob_none = 1.0
        for f in active:
            p = max(0.0, min(1.0, f / 100.0))
            prob_none *= (1.0 - p)

        combined = (1.0 - prob_none) * 100.0
        return min(100.0, combined)
    
    def _is_anonymized_value(self, val_str: str) -> bool:
        """Return True if value has already been anonymized (hash, redacted, truncated)"""
        # Hex hash (32+ chars of 0-9a-f) — product of hashing anonymization
        if re.match(r'^[a-f0-9]{32,}$', val_str, re.I):
            return True
        # Truncated values ending in '...'
        if val_str.endswith('...'):
            return True
        # Redaction markers
        if val_str in ('[REDACTED]', '[DATE]', '[LOCATION]', '***', 'REDACTED'):
            return True
        # Bucketed ranges like '10-20', '100k-200k'
        if re.match(r'^\d+[k]?[-–]\d+[k]?$', val_str):
            return True
        return False

    def _check_uniqueness(self, values: List[Any]) -> Tuple[float, List[str]]:
        """Check if values appear unique or rare.

        Accumulates distinct hit types (UUID, email, phone, long string,
        precise number) via the soft-OR combiner so a record with several
        different identifier types scores higher than one with just a
        single identifier type, even though both used to cap at the same
        max().
        """
        drivers = []
        hits = []

        for val in values:
            val_str = str(val)
            
            # Skip already-anonymized values — don't penalize the privacy engine's own output
            if self._is_anonymized_value(val_str):
                continue
            
            # UUID-like patterns (non-hashed)
            if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', val_str, re.I):
                hits.append(80)
                drivers.append("UUID-like identifiers present")
            
            # Email patterns
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', val_str):
                hits.append(90)
                drivers.append("Email addresses detected (direct identifiers)")
            
            # Phone number patterns
            if re.match(r'^\+?\d{10,13}$', val_str):
                hits.append(80)
                drivers.append("Phone numbers detected")
            
            # Very long strings that are NOT hashes suggest raw identifiers
            if len(val_str) > 20 and not re.match(r'^[a-f0-9]+$', val_str, re.I):
                hits.append(50)
                drivers.append("Long unique values detected")
            
            # Very specific numerical values (like exact amounts)
            if re.match(r'^\d+\.\d{4,}$', val_str):
                hits.append(50)
                drivers.append("Highly precise numerical values")
        
        risk = self._combine_risk_factors(hits)
        return risk, drivers
    
    def _check_sensitivity(self, field_value_pairs: List[Tuple[str, Any]]) -> Tuple[float, List[str]]:
        """Check for sensitive data patterns.

        IMPORTANT: checks BOTH the column/field name and the value text.
        Previously this only scanned value text, so a column literally
        named "ssn" containing "123-45-6789", or "salary" containing
        95000, or "password" containing "hunter2" scored ZERO — because
        none of those VALUES contain the words "ssn"/"salary"/"password";
        only the COLUMN NAMES do. That silently zeroed out sensitivity
        risk for some of the most common real-world sensitive columns,
        which (combined with the max()-collapse bug) made unrelated
        high-risk datasets produce inconsistent/incorrect scores.

        Accumulates distinct sensitive-category hits via the soft-OR
        combiner instead of max(), so e.g. SSN + credit card + health data
        together score meaningfully higher than any single category alone.
        """
        drivers = []
        hits = []
        
        # Sensitive keywords checked against column name + value text
        sensitive_patterns = {
            r'\b(password|passwd|pwd|secret)\b': ("Potential credential data", 100),
            r'\b(ssn|social.security)\b': ("Social security patterns", 100),
            r'\b(credit.card|card.number|cvv)\b': ("Financial data patterns", 100),
            r'\b(diagnosis|medical|health|patient)\b': ("Healthcare-related data", 90),
            r'\b(salary|income|wage|compensation)\b': ("Financial compensation data", 80),
            r'\b(address|street|apartment)\b': ("Location data detected", 70),
            r'\b(zip|zipcode|postal.?code|pincode)\b': ("Postal/zip code (quasi-identifier)", 35),
            r'\b(birth|dob)\b': ("Birth date data", 55),
            r'\bage\b': ("Age data present", 35),
        }

        # Person-name fields: checked ONLY against the column name (not the
        # value), and scoped to avoid false positives on fields like
        # "username", "filename", "company_name" which aren't direct
        # personal identifiers in the same way "full_name"/"first_name" are.
        name_field_pattern = r'\b(full.?name|first.?name|last.?name|surname|customer.?name|patient.?name)\b'
        
        for field_name, val in field_value_pairs:
            val_str_raw = str(val)
            
            # If the VALUE has already been anonymized (hashed, redacted,
            # masked, bucketed), don't penalize it just because the COLUMN
            # NAME still says "salary" or "ssn" — the privacy engine's own
            # output shouldn't be flagged as if it were raw sensitive data.
            if self._is_anonymized_value(val_str_raw):
                continue

            field_str = str(field_name).lower()
            if re.search(name_field_pattern, field_str, re.I):
                hits.append(65)
                if "Personal name field detected (quasi-identifier)" not in drivers:
                    drivers.append("Personal name field detected (quasi-identifier)")
            # Bare "name" column (not username/filename/etc, those end in
            # "name" but aren't a person's name by themselves) — moderate.
            elif field_str.strip() == 'name':
                hits.append(50)
                if "Generic 'name' field detected" not in drivers:
                    drivers.append("Generic 'name' field detected")
            
            val_str = val_str_raw.lower()
            # Check the column name AND the value text against each pattern.
            combined_text = f"{field_str} {val_str}"
            
            for pattern, (driver, pattern_risk) in sensitive_patterns.items():
                if re.search(pattern, combined_text, re.I):
                    hits.append(pattern_risk)
                    if driver not in drivers:
                        drivers.append(driver)
            
            # Check for exact age values (high risk if precise)
            if re.match(r'^\d{1,3}$', str(val)) and 0 < int(str(val)) < 120:
                hits.append(25)
                if "Precise age values present" not in drivers:
                    drivers.append("Precise age values present")
        
        risk = self._combine_risk_factors(hits)
        return risk, drivers
    
    def _check_combination_risk(self, values: List[Any]) -> Tuple[int, List[str]]:
        """Check if combination of values increases identification risk"""
        drivers = []
        risk = 0
        
        # More data points = higher combination risk
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
        """Check for overly precise or granular data.

        Accumulates distinct precision-hit types (timestamp, GPS,
        high-precision decimal) via the soft-OR combiner instead of max().
        """
        drivers = []
        hits = []
        
        for val in values:
            val_str = str(val)
            
            # Skip already-anonymized values
            if self._is_anonymized_value(val_str):
                continue
            
            # Timestamps with high precision
            if re.match(r'\d{4}-\d{2}-\d{2}.\d{2}:\d{2}:\d{2}', val_str):
                hits.append(70)
                drivers.append("Precise timestamps enable temporal correlation")
            
            # GPS coordinates
            if re.match(r'^-?\d+\.\d{4,},\s*-?\d+\.\d{4,}$', val_str):
                hits.append(90)
                drivers.append("GPS coordinates (exact location data)")
            
            # Very specific decimal numbers (but only if not already noised/bucketed)
            if re.match(r'^\d+\.\d{4,}$', val_str):
                hits.append(60)
                drivers.append("High-precision measurements")
        
        risk = self._combine_risk_factors(hits)
        return risk, drivers
    
    def _calculate_final_risk(self, record_risks: List[float]) -> int:
        """Calculate final risk score from individual record risks.

        Previously this rounded to the nearest of only 10 coarse buckets
        ([10,20,...,100]), which is the second half of why unrelated
        "high risk" datasets collapsed to the same number — once the
        weighted combination landed anywhere in, say, the 86-94 range, it
        was forced to exactly 90. That's now replaced with a plain
        continuous 0-100 integer score so real differences in severity
        survive into the final output.
        """
        if not record_risks:
            return 10
        
        # Use weighted approach: max risk influences heavily
        max_risk = max(record_risks)
        avg_risk = sum(record_risks) / len(record_risks)
        
        # 40% weight to max, 60% to average
        combined = (max_risk * 0.4) + (avg_risk * 0.6)
        
        # Clamp to valid range and return as a continuous score (no bucket snapping)
        final = max(0, min(100, round(combined)))
        
        return int(final)
    
    def _consolidate_drivers(self, all_drivers: List[str]) -> List[str]:
        """Remove duplicates and prioritize most critical drivers"""
        # Count occurrences
        driver_counts = Counter(all_drivers)
        
        # Get unique drivers, sorted by frequency
        unique_drivers = sorted(driver_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Return top 5 most common drivers
        return [driver for driver, _ in unique_drivers[:5]]
    
    def _generate_output(self, risk_score: int, drivers: List[str]) -> Dict[str, Any]:
        """Generate formatted output"""
        # Calculate risk level
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
        
        # Generate risk meter visualization
        filled = int((risk_score / 100) * 20)
        empty = 20 - filled
        meter = "█" * filled + "░" * empty
        
        return {
            "risk_score": risk_score,
            "risk_level": level,
            "risk_meter": f"[{meter}] {risk_score} / 100",
            "primary_risk_drivers": drivers if drivers else ["Insufficient data for detailed analysis"]
        }
    def analyze_anonymized_dataset(
        self,
        records: List[Dict[str, Any]],
        privacy_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a PREVIOUSLY ANONYMIZED dataset for residual re-identification risk.
        """
        if not records:
            return self._generate_output(10, ["No data to analyze"])

        # Base structural risk from the anonymized records
        base_result = self.analyze_dataset(records)
        base_score = base_result["risk_score"]

        transformations: Dict[str, Any] = privacy_metadata.get("transformations", {})
        if not transformations:
            # No metadata available � fall back to standard analysis
            return base_result

        # -- Count how many columns received each class of protection ---------
        dp_protected_cols = 0       # TRUE differential privacy (numeric)
        hashed_cols = 0             # Irreversible hash / redaction
        masked_cols = 0             # Partial masking (email, phone)
        suppressed_cols = 0         # k-anonymity suppression
        generalized_cols = 0        # Generalization / bucketing
        total_cols = len(transformations)

        for col, info in transformations.items():
            mechanism = info.get("mechanism", "") or ""
            privacy_guarantee = info.get("privacy_guarantee", "")
            col_type = info.get("type", "")

            # If mechanism isn't explicitly provided, infer from type
            if not mechanism:
                if col_type == "identifier":
                    mechanism = "hashing"
                elif col_type == "sensitive":
                    mechanism = "redaction"
                elif col_type == "categorical":
                    mechanism = "k_anonymity"
                elif col_type in ("quasi_identifier", "temporal", "geospatial"):
                    mechanism = "generalization"

            if privacy_guarantee == "DIFFERENTIAL_PRIVACY":
                dp_protected_cols += 1
            elif mechanism in ("hashing", "redaction", "pseudonymization"):
                hashed_cols += 1
            elif mechanism in ("masking",):
                masked_cols += 1
            elif mechanism in ("k_anonymity", "suppression"):
                suppressed_cols += 1
            elif mechanism in ("generalization", "bucketing", "rounding"):
                generalized_cols += 1
            else:
                pass

        # -- Compute a protection coverage ratio ------------------------------
        if total_cols > 0:
            weighted_protected = (
                dp_protected_cols * 1.0
                + hashed_cols * 1.0
                + masked_cols * 0.7
                + suppressed_cols * 0.5
                + generalized_cols * 0.4
            )
            coverage = min(weighted_protected / total_cols, 1.0)
        else:
            coverage = 0.0

        # -- Discount the combination-risk component --------------------------
        effective_unprotected_cols = total_cols - (dp_protected_cols + hashed_cols)
        if effective_unprotected_cols <= 3:
            combination_discount = 0.85   # Almost everything protected
        elif effective_unprotected_cols <= 6:
            combination_discount = 0.65
        elif effective_unprotected_cols <= 10:
            combination_discount = 0.45
        else:
            combination_discount = 0.20   # Many unprotected cols remain

        # -- Apply discounts to base score ------------------------------------
        discount_factor = coverage * combination_discount
        discounted = base_score * (1.0 - discount_factor)

        # Enforce a realistic floor
        residual_floor = max(10, base_score * 0.10)
        final_score_raw = max(discounted, residual_floor)

        # Round to a continuous 0-100 integer score (no bucket snapping —
        # same fix applied here as in _calculate_final_risk, since this
        # used to also collapse distinct post-privatization risk levels
        # into one of only 10 values).
        final_score = int(max(0, min(100, round(final_score_raw))))

        # -- Build informative drivers list ------------------------------------
        drivers = []
        if dp_protected_cols:
            drivers.append(f"{dp_protected_cols} numeric column(s) protected with DP")
        if hashed_cols:
            drivers.append(f"{hashed_cols} identifier(s) hashed/pseudonymized")
        if masked_cols:
            drivers.append(f"{masked_cols} quasi-identifier(s) masked")
        if suppressed_cols:
            drivers.append(f"{suppressed_cols} categorical column(s) k-anonymized")
        if generalized_cols:
            drivers.append(f"{generalized_cols} column(s) generalized/bucketed")
        if effective_unprotected_cols > 0:
            drivers.append(f"{effective_unprotected_cols} column(s) carry residual risk")

        return self._generate_output(final_score, drivers)