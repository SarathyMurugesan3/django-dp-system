"""
Query Fingerprinting System for Detecting Repeated Queries

Prevents privacy leakage by detecting similar queries with slight variations
(e.g., age > 18, age > 19, age > 20) and increasing budget cost.
"""

import hashlib
import json
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone


class QueryFingerprint:
    """
    Represents a normalized query fingerprint for similarity detection
    """
    
    def __init__(self, table_name: str, field_name: str, query_type: str, filters: Dict[str, Any]):
        self.table_name = table_name.lower()
        self.field_name = field_name.lower()
        self.query_type = query_type.lower()
        self.filters = self._normalize_filters(filters)
        self.fingerprint_hash = self._generate_hash()
    
    def _normalize_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize filters to canonical form for comparison"""
        if not filters:
            return {}
        
        normalized = {}
        for field, condition in filters.items():
            field_lower = field.lower()
            
            if isinstance(condition, dict):
                operator = condition.get('operator', '=').lower()
                value = condition.get('value')
                
                # Normalize operator
                operator_map = {
                    '==': '=',
                    'eq': '=',
                    'equals': '=',
                    'gt': '>',
                    'gte': '>=',
                    'lt': '<',
                    'lte': '<=',
                    'ne': '!=',
                    'neq': '!='
                }
                operator = operator_map.get(operator, operator)
                
                normalized[field_lower] = {
                    'operator': operator,
                    'value': value
                }
            else:
                # Simple equality
                normalized[field_lower] = {
                    'operator': '=',
                    'value': condition
                }
        
        return normalized
    
    def _generate_hash(self) -> str:
        """Generate hash for exact match detection"""
        canonical = {
            'table': self.table_name,
            'field': self.field_name,
            'type': self.query_type,
            'filters': self.filters
        }
        canonical_str = json.dumps(canonical, sort_keys=True)
        return hashlib.sha256(canonical_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'table_name': self.table_name,
            'field_name': self.field_name,
            'query_type': self.query_type,
            'filters': self.filters,
            'fingerprint_hash': self.fingerprint_hash
        }


class FingerprintMatcher:
    """
    Detects similar queries and calculates budget multipliers
    """
    
    @staticmethod
    def calculate_similarity(fp1: QueryFingerprint, fp2: QueryFingerprint) -> float:
        """
        Calculate similarity score between two query fingerprints (0.0 to 1.0)
        
        Returns:
            1.0 = Identical queries
            0.0 = Completely different queries
        """
        # Different tables or fields = not similar
        if fp1.table_name != fp2.table_name:
            return 0.0
        if fp1.field_name != fp2.field_name:
            return 0.0
        if fp1.query_type != fp2.query_type:
            return 0.0
        
        # Same fingerprint hash = identical
        if fp1.fingerprint_hash == fp2.fingerprint_hash:
            return 1.0
        
        # Compare filters
        filters1 = fp1.filters
        filters2 = fp2.filters
        
        # Different number of filters = less similar
        if set(filters1.keys()) != set(filters2.keys()):
            return 0.2  # Some overlap but different structure
        
        # Compare each filter
        total_similarity = 0.0
        num_filters = len(filters1)
        
        for field in filters1.keys():
            f1 = filters1[field]
            f2 = filters2[field]
            
            # Same operator?
            if f1['operator'] == f2['operator']:
                operator_match = 1.0
            elif FingerprintMatcher._are_related_operators(f1['operator'], f2['operator']):
                operator_match = 0.5
            else:
                operator_match = 0.0
            
            # Similar values?
            value_similarity = FingerprintMatcher._calculate_value_similarity(
                f1['value'], f2['value'], f1['operator']
            )
            
            # Average operator and value similarity
            filter_similarity = (operator_match + value_similarity) / 2
            total_similarity += filter_similarity
        
        return total_similarity / num_filters if num_filters > 0 else 0.0
    
    @staticmethod
    def _are_related_operators(op1: str, op2: str) -> bool:
        """Check if two operators are related (e.g., > and >=)"""
        related_pairs = [
            {'>', '>='},
            {'<', '<='},
            {'=', '!='}
        ]
        return any({op1, op2} == pair for pair in related_pairs)
    
    @staticmethod
    def _calculate_value_similarity(val1: Any, val2: Any, operator: str) -> float:
        """Calculate similarity between filter values"""
        # Exact match
        if val1 == val2:
            return 1.0
        
        # Both numeric - calculate relative difference
        try:
            v1 = float(val1)
            v2 = float(val2)
            
            # For comparison operators (>, <, >=, <=)
            if operator in ['>', '<', '>=', '<=']:
                # Calculate percentage difference
                if v1 == 0 and v2 == 0:
                    return 1.0
                
                avg = (abs(v1) + abs(v2)) / 2
                if avg == 0:
                    return 1.0
                
                diff_pct = abs(v1 - v2) / avg
                
                # Very close values (within 5%) = very similar
                if diff_pct < 0.05:
                    return 0.98
                elif diff_pct < 0.1:
                    return 0.95
                elif diff_pct < 0.2:
                    return 0.85
                elif diff_pct < 0.5:
                    return 0.6
                else:
                    return 0.3
            else:
                # For equality operators
                return 0.0 if v1 != v2 else 1.0
        
        except (ValueError, TypeError):
            # String comparison
            if isinstance(val1, str) and isinstance(val2, str):
                if val1.lower() == val2.lower():
                    return 1.0
                # Partial match
                if val1.lower() in val2.lower() or val2.lower() in val1.lower():
                    return 0.5
            return 0.0
    
    @staticmethod
    def get_budget_multiplier(similarity: float) -> float:
        """
        Calculate budget multiplier based on similarity score
        
        Higher similarity = Higher multiplier (more expensive)
        """
        if similarity < 0.3:
            return 1.0  # Different queries - no penalty
        elif similarity < 0.6:
            return 1.5  # Somewhat similar
        elif similarity < 0.8:
            return 2.0  # Similar
        elif similarity < 0.95:
            return 3.0  # Very similar
        else:
            return 5.0  # Nearly identical - strong penalty
    
    @staticmethod
    def find_similar_queries(
        current_fp: QueryFingerprint,
        history: List[Dict[str, Any]],
        time_window_hours: int = 24
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Find similar queries in history and return max multiplier
        
        Args:
            current_fp: Current query fingerprint
            history: List of previous query fingerprints
            time_window_hours: Only consider queries within this time window
        
        Returns:
            (max_multiplier, list_of_similar_queries)
        """
        cutoff_time = timezone.now() - timedelta(hours=time_window_hours)
        
        max_multiplier = 1.0
        similar_queries = []
        
        for hist_query in history:
            # Skip old queries
            query_time = hist_query.get('timestamp')
            if isinstance(query_time, str):
                query_time = datetime.fromisoformat(query_time.replace('Z', '+00:00'))
            
            if query_time < cutoff_time:
                continue
            
            # Create fingerprint from history
            hist_fp = QueryFingerprint(
                table_name=hist_query['table_name'],
                field_name=hist_query['field_name'],
                query_type=hist_query['query_type'],
                filters=hist_query['filters']
            )
            
            # Calculate similarity
            similarity = FingerprintMatcher.calculate_similarity(current_fp, hist_fp)
            
            if similarity > 0.3:  # Threshold for "similar"
                multiplier = FingerprintMatcher.get_budget_multiplier(similarity)
                
                if multiplier > max_multiplier:
                    max_multiplier = multiplier
                
                similar_queries.append({
                    'similarity': round(similarity, 3),
                    'multiplier': multiplier,
                    'timestamp': hist_query['timestamp'],
                    'filters': hist_query['filters']
                })
        
        return max_multiplier, similar_queries
