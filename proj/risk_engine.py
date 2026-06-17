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
    
    def _analyze_record(self, record: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        Analyze a single record for identifiability and sensitivity
        
        Returns:
            Tuple of (risk_score, list_of_drivers)
        """
        risk_factors = []
        drivers = []
        
        values = [v for v in record.values() if v is not None and str(v).strip()]
        
        if not values:
            return 10, ["Empty record"]
        
        # 1. Check for uniqueness indicators
        unique_risk, unique_drivers = self._check_uniqueness(values)
        risk_factors.append(unique_risk)
        drivers.extend(unique_drivers)
        
        # 2. Check for sensitive data patterns
        sensitivity_risk, sensitivity_drivers = self._check_sensitivity(values)
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
        
        # Calculate record risk (max of all factors)
        record_risk = max(risk_factors) if risk_factors else 10
        
        # 5. Check for anonymization markers to apply risk discount
        discount = self._get_anonymization_discount(values)
        if discount < 1.0:
            record_risk = int(record_risk * discount)
            # Add driver and remove conflicting high-risk drivers if heavily discounted
            if "Risk reduced due to strong anonymization/masking" not in drivers:
                drivers.append("Risk reduced due to strong anonymization/masking")
        
        return record_risk, drivers
    
    def _get_anonymization_discount(self, values: List[Any]) -> float:
        """Calculate a discount factor if data appears anonymized"""
        anonymized_fields = 0
        
        for val in values:
            val_str = str(val)
            # Masking
            if '*' in val_str or 'XXXX' in val_str or '[MASKED]' in val_str:
                anonymized_fields += 1
            # Pseudonyms
            elif val_str.startswith('Person_') or val_str.startswith('District '):
                anonymized_fields += 1
            # Hashes (hex strings of various lengths, often used to match original length)
            elif re.match(r'^[a-fA-F0-9]{6,64}$', val_str) and not val_str.isdigit():
                anonymized_fields += 1
            # Range buckets
            elif re.match(r'^\d+-\d+$', val_str) or re.match(r'^\d+\+$', val_str):
                anonymized_fields += 1
        
        if anonymized_fields == 0:
            return 1.0
            
        ratio = anonymized_fields / len(values)
        if ratio > 0.4:
            return 0.2  # 80% risk reduction if heavily anonymized
        elif ratio > 0.15:
            return 0.4  # 60% reduction
        else:
            return 0.6  # 40% reduction
    
    def _check_uniqueness(self, values: List[Any]) -> Tuple[int, List[str]]:
        """Check if values appear unique or rare"""
        drivers = []
        risk = 0
        
        for val in values:
            val_str = str(val)
            
            # Very long strings suggest unique identifiers (skip hex hashes and phrases)
            if len(val_str) > 20 and not (re.match(r'^[a-fA-F0-9]{6,64}$', val_str) and not val_str.isdigit()) and ' ' not in val_str:
                risk = max(risk, 70)
                drivers.append("Very long unique values detected")
            
            # UUID-like patterns
            if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', val_str, re.I):
                risk = max(risk, 80)
                drivers.append("UUID-like identifiers present")
            
            # Email patterns
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', val_str):
                risk = max(risk, 90)
                drivers.append("Email addresses detected (direct identifiers)")
            
            # Phone number patterns
            if re.match(r'^\+?\d{10,13}(?:\.0)?$', val_str):
                risk = max(risk, 80)
                drivers.append("Phone numbers detected")
            
            # Very specific numerical values (like exact amounts)
            if re.match(r'^\d+\.\d{2,}$', val_str):
                risk = max(risk, 50)
                drivers.append("Highly precise numerical values")
        
        return risk, drivers
    
    def _check_sensitivity(self, values: List[Any]) -> Tuple[int, List[str]]:
        """Check for sensitive data patterns"""
        drivers = []
        risk = 0
        
        # Checking sensitive patterns against values directly causes false positives 
        # (e.g. 'Rental Income' triggers 'income' -> 80 risk).
        # We only check for specific dangerous data types in values, like exact age.
        for val in values:
            val_str = str(val).strip()

            # Exact age values
            if re.match(r'^\d{1,3}$', val_str) and 0 < int(val_str) < 120:
                risk = max(risk, 25)
                if "Precise age values present" not in drivers:
                    drivers.append("Precise age values present")

            # Aadhaar: exactly 12 digits (with or without spaces or dashes)
            aadhaar_clean = val_str.replace(' ', '').replace('-', '')
            if re.match(r'^\d{12}(?:\.0)?$', aadhaar_clean):
                risk = max(risk, 95)
                if "Aadhaar-format identifier detected" not in drivers:
                    drivers.append("Aadhaar-format identifier detected")

            # Credit Card: 16 digits (with or without spaces or dashes)
            cc_clean = val_str.replace(' ', '').replace('-', '')
            if re.match(r'^\d{16}(?:\.0)?$', cc_clean):
                risk = max(risk, 95)
                if "Credit card format detected" not in drivers:
                    drivers.append("Credit card format detected")

            # PAN: exactly 5 letters + 4 digits + 1 letter
            if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', val_str.upper()):
                risk = max(risk, 95)
                if "PAN-format identifier detected" not in drivers:
                    drivers.append("PAN-format identifier detected")

            # IFSC: 4 letters + 0 + 6 alphanumeric
            if re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', val_str.upper()):
                risk = max(risk, 80)
                if "IFSC code detected" not in drivers:
                    drivers.append("IFSC code detected")
                    
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
    
    def _check_precision(self, values: List[Any]) -> Tuple[int, List[str]]:
        """Check for overly precise or granular data"""
        drivers = []
        risk = 0
        
        for val in values:
            val_str = str(val)
            
            # Timestamps with high precision
            if re.match(r'\d{4}-\d{2}-\d{2}.\d{2}:\d{2}:\d{2}', val_str):
                risk = max(risk, 70)
                drivers.append("Precise timestamps enable temporal correlation")
            
            # GPS coordinates
            if re.match(r'^-?\d+\.\d{4,},\s*-?\d+\.\d{4,}$', val_str):
                risk = max(risk, 90)
                drivers.append("GPS coordinates (exact location data)")
            
            # Very specific decimal numbers
            if re.match(r'^\d+\.\d{4,}$', val_str):
                risk = max(risk, 60)
                drivers.append("High-precision measurements")
        
        return risk, drivers
    
    def _calculate_final_risk(self, record_risks: List[int]) -> int:
        """Calculate final risk score from individual record risks"""
        if not record_risks:
            return 10
        
        # Use weighted approach: max risk influences heavily
        max_risk = max(record_risks)
        avg_risk = sum(record_risks) / len(record_risks)
        
        # 70% weight to max, 30% to average
        combined = (max_risk * 0.7) + (avg_risk * 0.3)
        combined = min(100, max(10, combined))
        
        # Round to nearest valid score
        valid_scores = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        final = min(valid_scores, key=lambda x: abs(x - combined))
        
        return final
    
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