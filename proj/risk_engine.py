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
        
        return record_risk, drivers
    
    def _check_uniqueness(self, values: List[Any]) -> Tuple[int, List[str]]:
        """Check if values appear unique or rare"""
        drivers = []
        risk = 0
        
        for val in values:
            val_str = str(val)
            
            # Very long strings suggest unique identifiers
            if len(val_str) > 20:
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
            if re.match(r'^\+?\d{10,13}$', val_str):
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
        
        # Sensitive keywords (domain-agnostic)
        sensitive_patterns = {
            r'\b(password|passwd|pwd|secret)\b': ("Potential credential data", 100),
            r'\b(ssn|social.security)\b': ("Social security patterns", 100),
            r'\b(credit.card|card.number|cvv)\b': ("Financial data patterns", 100),
            r'\b(diagnosis|medical|health|patient)\b': ("Healthcare-related data", 90),
            r'\b(salary|income|wage|compensation)\b': ("Financial compensation data", 80),
            r'\b(address|street|apartment|zip)\b': ("Location data detected", 70),
            r'\b(birth|dob|age)\b': ("Age/birth-related data", 60),
        }
        
        for val in values:
            val_str = str(val).lower()
            
            for pattern, (driver, pattern_risk) in sensitive_patterns.items():
                if re.search(pattern, val_str, re.I):
                    risk = max(risk, pattern_risk)
                    if driver not in drivers:
                        drivers.append(driver)
            
            # Check for exact age values (high risk if precise)
            if re.match(r'^\d{1,3}$', str(val)) and 0 < int(str(val)) < 120:
                risk = max(risk, 25)
                if "Precise age values present" not in drivers:
                    drivers.append("Precise age values present")
        
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
        combined = (max_risk * 0.4) + (avg_risk * 0.6)
        
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