"""
Column Classifier
Automatically detects column types and sensitivity levels for any dataset schema
"""
import re
from typing import List, Dict, Any, Tuple
from collections import Counter
from datetime import datetime


class ColumnType:
    """Column type classifications"""
    IDENTIFIER = "identifier"  # Direct identifiers (ID, email, SSN)
    QUASI_IDENTIFIER = "quasi_identifier"  # Can identify when combined (name, age, zip)
    NUMERIC = "numeric"  # Numeric data (salary, count, measurement)
    CATEGORICAL = "categorical"  # Categories (gender, status, type)
    TEMPORAL = "temporal"  # Dates, timestamps
    GEOSPATIAL = "geospatial"  # Location data
    SENSITIVE = "sensitive"  # Explicitly sensitive (password, medical)
    GENERIC = "generic"  # Unknown/mixed type


class SensitivityLevel:
    """Sensitivity classifications"""
    CRITICAL = "critical"  # Must be heavily protected
    HIGH = "high"  # High risk
    MODERATE = "moderate"  # Medium risk
    LOW = "low"  # Low risk


class ColumnClassifier:
    """
    Automatically classifies columns in any dataset by analyzing:
    - Column names (semantic analysis)
    - Data patterns (regex matching)
    - Statistical properties
    - Value distributions
    """
    
    def __init__(self):
        # Semantic patterns for column name analysis
        self.name_patterns = {
            'identifier': {
                'patterns': [
                    r'\b(id|identifier|uuid|guid|key)\b',
                    r'\b(email|mail|e-mail)\b',
                    r'\b(ssn|social.?security)\b',
                    r'\b(username|user.?name|login)\b',
                    r'\b(account|account.?number)\b',
                    r'\b(license|permit|registration)\b'
                ],
                'sensitivity': 'high'
            },
            'quasi_identifier': {
                'patterns': [
                    r'\b(name|first.?name|last.?name|full.?name)\b',
                    r'\b(age|birth|dob|date.?of.?birth)\b',
                    r'\b(zip|zipcode|postal|postcode)\b',
                    r'\b(phone|telephone|mobile|cell)\b',
                    r'\b(address|street|location|city|state|province)\b',
                    r'\b(gender|sex)\b',
                    r'\b(race|ethnicity|nationality)\b',
                    r'\b(occupation|job|title|position)\b'
                ],
                'sensitivity': 'moderate'
            },
            'sensitive': {
                'patterns': [
                    r'\b(password|passwd|pwd|secret|token)\b',
                    r'\b(credit.?card|card.?number|cvv|cvc)\b',
                    r'\b(medical|health|diagnosis|condition)\b',
                    r'\b(salary|income|wage|compensation|pay)\b',
                    r'\b(bank|routing|account.?number)\b',
                    r'\b(tax|ein|tin)\b'
                ],
                'sensitivity': 'critical'
            },
            'temporal': {
                'patterns': [
                    r'\b(date|time|timestamp|datetime|created|updated|modified)\b',
                    r'\b(year|month|day|hour|minute|second)\b'
                ],
                'sensitivity': 'low'
            },
            'geospatial': {
                'patterns': [
                    r'\b(lat|latitude|long|longitude|coord|gps)\b',
                    r'\b(location|geo|position)\b'
                ],
                'sensitivity': 'moderate'
            },
            'numeric': {
                'patterns': [
                    r'\b(count|total|sum|amount|quantity|number)\b',
                    r'\b(price|cost|value|revenue)\b',
                    r'\b(score|rating|rank)\b',
                    r'\b(percentage|percent|ratio|rate)\b'
                ],
                'sensitivity': 'low'
            }
        }
        
        # Value pattern matchers
        self.value_patterns = {
            'email': r'^[\w\.-]+@[\w\.-]+\.\w+$',
            'phone': r'^\+?[\d\s\-\(\)]{10,}$',
            'uuid': r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
            'ssn': r'^\d{3}-?\d{2}-?\d{4}$',
            'credit_card': r'^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$',
            'date_iso': r'^\d{4}-\d{2}-\d{2}',
            'timestamp': r'\d{4}-\d{2}-\d{2}.\d{2}:\d{2}:\d{2}',
            'gps': r'^-?\d+\.\d{4,},\s*-?\d+\.\d{4,}$',
            'url': r'^https?://[\w\.-]+',
            'ip_address': r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
            'password_hash': r'^[a-f0-9]{32,}$|^\$2[aby]\$[\d]+\$',
        }
    
    def classify_columns(
        self, 
        records: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Classify all columns in the dataset
        
        Args:
            records: List of dictionaries representing dataset
            
        Returns:
            Dictionary mapping column names to classification info
        """
        if not records:
            return {}
        
        classifications = {}
        
        # Get all column names
        all_columns = set()
        for record in records:
            all_columns.update(record.keys())
        
        # Classify each column
        for column_name in all_columns:
            # Extract column values (sample for efficiency)
            column_values = self._extract_column_values(records, column_name)
            
            # Perform classification
            classification = self._classify_single_column(column_name, column_values)
            
            classifications[column_name] = classification
        
        return classifications
    
    def _extract_column_values(
        self, 
        records: List[Dict], 
        column_name: str,
        max_sample: int = 100
    ) -> List[Any]:
        """Extract values for a single column (with sampling)"""
        
        values = []
        for record in records[:max_sample]:
            if column_name in record:
                val = record[column_name]
                if val is not None:
                    values.append(val)
        
        return values
    
    def _classify_single_column(
        self, 
        column_name: str, 
        values: List[Any]
    ) -> Dict[str, Any]:
        """
        Classify a single column based on name and values
        
        Returns:
            Dictionary with type, sensitivity, confidence, and recommendations
        """
        if not values:
            return {
                'type': ColumnType.GENERIC,
                'sensitivity': SensitivityLevel.LOW,
                'confidence': 0.0,
                'recommended_mechanism': 'suppression',
                'reasoning': 'No data available'
            }
        
        # Step 1: Analyze column name semantically
        name_classification = self._classify_by_name(column_name)
        
        # Step 2: Analyze value patterns
        value_classification = self._classify_by_values(values)
        
        # Step 3: Analyze statistical properties
        stats_classification = self._classify_by_statistics(values)
        
        # Step 4: Combine classifications
        final_classification = self._combine_classifications(
            name_classification,
            value_classification,
            stats_classification,
            column_name
        )
        
        # Step 5: Add recommendations
        final_classification['recommended_mechanism'] = self._recommend_mechanism(
            final_classification
        )
        
        return final_classification
    
    def _classify_by_name(self, column_name: str) -> Dict[str, Any]:
        """Classify based on column name semantic analysis"""
        
        column_name_lower = column_name.lower()
        
        # Check each category
        for category, info in self.name_patterns.items():
            for pattern in info['patterns']:
                if re.search(pattern, column_name_lower, re.IGNORECASE):
                    return {
                        'type': category,
                        'sensitivity': info['sensitivity'],
                        'confidence': 0.8,
                        'reasoning': f"Column name matches {category} pattern"
                    }
        
        # No match
        return {
            'type': ColumnType.GENERIC,
            'sensitivity': SensitivityLevel.LOW,
            'confidence': 0.0,
            'reasoning': 'No semantic pattern match'
        }
    
    def _classify_by_values(self, values: List[Any]) -> Dict[str, Any]:
        """Classify based on actual value patterns"""
        
        if not values:
            return {'type': ColumnType.GENERIC, 'confidence': 0.0}
        
        # Sample values for analysis
        sample_size = min(50, len(values))
        sample = values[:sample_size]
        
        # Convert to strings for pattern matching
        string_values = [str(v) for v in sample]
        
        # Check value patterns
        pattern_matches = {}
        for pattern_name, pattern in self.value_patterns.items():
            matches = sum(1 for v in string_values if re.match(pattern, v, re.IGNORECASE))
            match_ratio = matches / len(string_values)
            
            if match_ratio > 0.8:  # High confidence
                pattern_matches[pattern_name] = match_ratio
        
        # If we have pattern matches, classify accordingly
        if pattern_matches:
            top_pattern = max(pattern_matches.items(), key=lambda x: x[1])
            pattern_name, confidence = top_pattern
            
            return self._pattern_to_classification(pattern_name, confidence)
        
        # Check if numeric
        numeric_count = sum(1 for v in sample if self._is_numeric(v))
        if numeric_count / len(sample) > 0.8:
            return {
                'type': ColumnType.NUMERIC,
                'sensitivity': SensitivityLevel.LOW,
                'confidence': 0.7,
                'reasoning': 'Values are primarily numeric'
            }
        
        # Check if categorical (limited unique values)
        unique_ratio = len(set(string_values)) / len(string_values)
        if unique_ratio < 0.5:
            return {
                'type': ColumnType.CATEGORICAL,
                'sensitivity': SensitivityLevel.LOW,
                'confidence': 0.6,
                'reasoning': 'Limited unique values suggest categorical'
            }
        
        return {'type': ColumnType.GENERIC, 'confidence': 0.0}
    
    def _classify_by_statistics(self, values: List[Any]) -> Dict[str, Any]:
        """Classify based on statistical properties"""
        
        # Calculate uniqueness ratio
        unique_count = len(set(str(v) for v in values))
        uniqueness_ratio = unique_count / len(values) if len(values) > 0 else 0
        
        # High uniqueness suggests identifier
        if uniqueness_ratio > 0.95:
            return {
                'type': ColumnType.IDENTIFIER,
                'sensitivity': SensitivityLevel.HIGH,
                'confidence': 0.7,
                'reasoning': f'Very high uniqueness ({uniqueness_ratio:.2%})'
            }
        
        # Medium uniqueness suggests quasi-identifier
        elif uniqueness_ratio > 0.7:
            return {
                'type': ColumnType.QUASI_IDENTIFIER,
                'sensitivity': SensitivityLevel.MODERATE,
                'confidence': 0.6,
                'reasoning': f'High uniqueness ({uniqueness_ratio:.2%})'
            }
        
        # Low uniqueness suggests categorical
        elif uniqueness_ratio < 0.3:
            return {
                'type': ColumnType.CATEGORICAL,
                'sensitivity': SensitivityLevel.LOW,
                'confidence': 0.6,
                'reasoning': f'Low uniqueness ({uniqueness_ratio:.2%})'
            }
        
        return {'type': ColumnType.GENERIC, 'confidence': 0.0}
    
    def _combine_classifications(
        self,
        name_class: Dict,
        value_class: Dict,
        stats_class: Dict,
        column_name: str
    ) -> Dict[str, Any]:
        """Combine multiple classification signals into final classification"""
        
        # Weight classifications by confidence
        candidates = []
        
        if name_class['confidence'] > 0:
            candidates.append((name_class, name_class['confidence'] * 1.2))  # Name gets priority
        
        if value_class.get('confidence', 0) > 0:
            candidates.append((value_class, value_class['confidence']))
        
        if stats_class.get('confidence', 0) > 0:
            candidates.append((stats_class, stats_class['confidence'] * 0.8))  # Stats less reliable
        
        if not candidates:
            return {
                'type': ColumnType.GENERIC,
                'sensitivity': SensitivityLevel.LOW,
                'confidence': 0.5,
                'reasoning': 'Default classification',
                'column_name': column_name
            }
        
        # Choose highest weighted classification
        best_classification, best_weight = max(candidates, key=lambda x: x[1])
        
        # Add column name to result
        result = best_classification.copy()
        result['column_name'] = column_name
        result['confidence'] = min(best_weight, 1.0)
        
        return result
    
    def _pattern_to_classification(
        self, 
        pattern_name: str, 
        confidence: float
    ) -> Dict[str, Any]:
        """Convert pattern match to classification"""
        
        pattern_map = {
            'email': (ColumnType.IDENTIFIER, SensitivityLevel.HIGH),
            'phone': (ColumnType.QUASI_IDENTIFIER, SensitivityLevel.MODERATE),
            'uuid': (ColumnType.IDENTIFIER, SensitivityLevel.HIGH),
            'ssn': (ColumnType.IDENTIFIER, SensitivityLevel.CRITICAL),
            'credit_card': (ColumnType.SENSITIVE, SensitivityLevel.CRITICAL),
            'date_iso': (ColumnType.TEMPORAL, SensitivityLevel.LOW),
            'timestamp': (ColumnType.TEMPORAL, SensitivityLevel.LOW),
            'gps': (ColumnType.GEOSPATIAL, SensitivityLevel.MODERATE),
            'url': (ColumnType.GENERIC, SensitivityLevel.LOW),
            'ip_address': (ColumnType.QUASI_IDENTIFIER, SensitivityLevel.MODERATE),
            'password_hash': (ColumnType.SENSITIVE, SensitivityLevel.CRITICAL),
        }
        
        col_type, sensitivity = pattern_map.get(
            pattern_name, 
            (ColumnType.GENERIC, SensitivityLevel.LOW)
        )
        
        return {
            'type': col_type,
            'sensitivity': sensitivity,
            'confidence': confidence,
            'reasoning': f'Matches {pattern_name} pattern'
        }
    
    def _recommend_mechanism(self, classification: Dict) -> str:
        """Recommend privacy mechanism based on classification"""
        
        col_type = classification['type']
        sensitivity = classification['sensitivity']
        
        # Critical sensitivity always gets redaction
        if sensitivity == SensitivityLevel.CRITICAL:
            return 'redaction'
        
        # Type-based recommendations
        recommendations = {
            ColumnType.IDENTIFIER: 'hashing',
            ColumnType.QUASI_IDENTIFIER: 'k_anonymity',
            ColumnType.NUMERIC: 'laplace_noise',
            ColumnType.CATEGORICAL: 'k_anonymity',
            ColumnType.TEMPORAL: 'generalization',
            ColumnType.GEOSPATIAL: 'generalization',
            ColumnType.SENSITIVE: 'redaction',
            ColumnType.GENERIC: 'suppression'
        }
        
        return recommendations.get(col_type, 'suppression')
    
    def _is_numeric(self, value: Any) -> bool:
        """Check if value is numeric"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def generate_report(self, classifications: Dict[str, Dict]) -> str:
        """Generate human-readable classification report"""
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("COLUMN CLASSIFICATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Group by type
        by_type = {}
        for col_name, info in classifications.items():
            col_type = info['type']
            if col_type not in by_type:
                by_type[col_type] = []
            by_type[col_type].append((col_name, info))
        
        # Print by type
        for col_type, columns in sorted(by_type.items()):
            report_lines.append(f"\n{col_type.upper()} COLUMNS ({len(columns)}):")
            report_lines.append("-" * 80)
            
            for col_name, info in sorted(columns):
                report_lines.append(f"\n  Column: {col_name}")
                report_lines.append(f"    Sensitivity: {info['sensitivity']}")
                report_lines.append(f"    Confidence: {info['confidence']:.2%}")
                report_lines.append(f"    Recommended: {info['recommended_mechanism']}")
                report_lines.append(f"    Reasoning: {info['reasoning']}")
        
        report_lines.append("\n" + "=" * 80)
        
        return "\n".join(report_lines)