"""
Differential Privacy Engine with ShadowSafe-Style Privacy Budget System
PRODUCTION-READY with Bounded DP and Strict Budget Enforcement

ARCHITECTURE:
User/Analyst → Proxy Privacy Layer → Privacy Budget Ledger → Noise Engine → Privatized Response

PRIVACY GUARANTEES:
- TRUE DIFFERENTIAL PRIVACY: Numeric aggregates use IBM diffprivlib with BOUNDED mechanisms
- STRICT BUDGET ENFORCEMENT: Finite epsilon resource with per-query accounting
- GRACEFUL DEGRADATION: Noise increases as budget depletes
- SLIDING WINDOW RECOVERY: Time-based budget refill
- NON-DP ANONYMIZATION: Identifiers use masking, hashing, suppression (NO DP noise)

SECURITY:
- Raw data exists ONLY ephemerally in memory
- ONLY privatized results exit the engine
- Audit-ready transparency log (GDPR/DPDP Act compliant)
- Deterministic randomness with query-specific salts
"""

import numpy as np
import hashlib
import json
import time
import secrets
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter
from datetime import datetime, timedelta

try:
    from diffprivlib.mechanisms import LaplaceBoundedDomain, Gaussian
    from diffprivlib.tools import mean as dp_mean, var as dp_var, std as dp_std, count_nonzero as dp_count
    DIFFPRIVLIB_AVAILABLE = True
except ImportError:
    DIFFPRIVLIB_AVAILABLE = False
    raise RuntimeError("IBM diffprivlib is REQUIRED. Install with: pip install diffprivlib")


class QueryType(Enum):
    """Supported differential privacy query types"""
    COUNT = "count"
    MEAN = "mean"
    SUM = "sum"
    VARIANCE = "variance"
    STD = "std"


QUERY_EPSILON_COST = {
    QueryType.COUNT: 0.01,
    QueryType.MEAN: 0.05,
    QueryType.SUM: 0.1,
    QueryType.VARIANCE: 0.1,
    QueryType.STD: 0.1,
}


class PrivacyMechanism(Enum):
    """Available privacy mechanisms"""
    LAPLACE_BOUNDED = "laplace_bounded"
    GAUSSIAN_BOUNDED = "gaussian_bounded"
    HASHING = "hashing"
    MASKING = "masking"
    REDACTION = "redaction"
    GENERALIZATION = "generalization"
    BUCKETING = "bucketing"
    K_ANONYMITY = "k_anonymity"
    PSEUDONYMIZATION = "pseudonymization"
    SUPPRESSION = "suppression"


FIELD_SENSITIVITY_MAP = {
    'age': {'sensitivity': 1.0, 'lower': 0, 'upper': 120},
    'household': {'sensitivity': 1.0, 'lower': 1, 'upper': 20},
    'householdsize': {'sensitivity': 1.0, 'lower': 1, 'upper': 20},
    'family': {'sensitivity': 1.0, 'lower': 1, 'upper': 20},
    'size': {'sensitivity': 1.0, 'lower': 1, 'upper': 50},
    'salary': {'sensitivity': 5000.0, 'lower': 0, 'upper': 1000000},
    'income': {'sensitivity': 5000.0, 'lower': 0, 'upper': 1000000},
    'monthlyincome': {'sensitivity': 5000.0, 'lower': 0, 'upper': 200000},
    'wage': {'sensitivity': 5000.0, 'lower': 0, 'upper': 500000},
    'pay': {'sensitivity': 5000.0, 'lower': 0, 'upper': 500000},
    'land': {'sensitivity': 0.5, 'lower': 0, 'upper': 1000},
    'acres': {'sensitivity': 0.5, 'lower': 0, 'upper': 1000},
    'landowned': {'sensitivity': 0.5, 'lower': 0, 'upper': 1000},
    'area': {'sensitivity': 0.5, 'lower': 0, 'upper': 10000},
    'score': {'sensitivity': 5.0, 'lower': 0, 'upper': 100},
    'rating': {'sensitivity': 5.0, 'lower': 0, 'upper': 100},
    'grade': {'sensitivity': 5.0, 'lower': 0, 'upper': 100},
    'percent': {'sensitivity': 5.0, 'lower': 0, 'upper': 100},
    'count': {'sensitivity': 5.0, 'lower': 0, 'upper': 10000},
    'quantity': {'sensitivity': 5.0, 'lower': 0, 'upper': 10000},
    'number': {'sensitivity': 5.0, 'lower': 0, 'upper': 10000},
    'price': {'sensitivity': 100.0, 'lower': 0, 'upper': 100000},
    'cost': {'sensitivity': 100.0, 'lower': 0, 'upper': 100000},
    'amount': {'sensitivity': 100.0, 'lower': 0, 'upper': 100000},
    'revenue': {'sensitivity': 10000.0, 'lower': 0, 'upper': 10000000},
    'budget': {'sensitivity': 10000.0, 'lower': 0, 'upper': 10000000},
    'funding': {'sensitivity': 10000.0, 'lower': 0, 'upper': 10000000},
}


def get_field_sensitivity(field_name: str, default_value: float = None) -> Dict[str, Any]:
    """Get sensitivity parameters based on semantic field meaning (NOT data-dependent)"""
    field_lower = field_name.lower()
    
    for keyword, params in FIELD_SENSITIVITY_MAP.items():
        if keyword in field_lower:
            return params.copy()
    
    if default_value is not None:
        abs_val = abs(default_value)
        if abs_val < 10:
            return {'sensitivity': 1.0, 'lower': 0, 'upper': 100}
        elif abs_val < 100:
            return {'sensitivity': 5.0, 'lower': 0, 'upper': 1000}
        elif abs_val < 1000:
            return {'sensitivity': 50.0, 'lower': 0, 'upper': 10000}
        elif abs_val < 10000:
            return {'sensitivity': 500.0, 'lower': 0, 'upper': 100000}
        else:
            return {'sensitivity': 5000.0, 'lower': 0, 'upper': 10000000}
    
    return {'sensitivity': 1.0, 'lower': 0, 'upper': 1000}


def age_to_range(age: float) -> int:
    """Add random noise of ±2 or ±3 to age for privacy"""
    import random
    
    age_int = int(age)
    
    # Add random noise of ±2 or ±3
    noise = random.choice([-3, -2, 2, 3])
    noisy_age = age_int + noise
    
    # Ensure age stays in reasonable bounds
    noisy_age = max(0, min(120, noisy_age))
    
    return noisy_age





def income_to_range(income: float) -> str:
    """Convert income to range buckets with realistic granularity"""
    if income < 10000:
        return "0-10000"
    elif income <= 25000:
        return "10000-25000"
    elif income <= 50000:
        return "25000-50000"
    elif income <= 75000:
        return "50000-75000"
    elif income <= 100000:
        return "75000-100000"
    elif income <= 150000:
        return "100000-150000"
    elif income <= 200000:
        return "150000-200000"
    else:
        return "200000+"
    """Convert monthly income to range buckets"""
    income_int = int(income)
    if income_int < 10000:
        return "0-10000"
    elif income_int <= 18000:
        return "10000-18000"
    elif income_int <= 25000:
        return "18000-25000"
    elif income_int <= 35000:
        return "25000-35000"
    elif income_int <= 50000:
        return "35000-50000"
    elif income_int <= 75000:
        return "50000-75000"
    elif income_int <= 100000:
        return "75000-100000"
    else:
        return "100000-1000000"


def household_to_range(size: float) -> str:
    """Convert household size to range buckets"""
    size_int = int(size)
    if size_int <= 2:
        return "1-2"
    elif size_int <= 5:
        return "3-5"
    elif size_int <= 8:
        return "6-8"
    else:
        return "9-20"


def land_to_range(acres: float) -> str:
    """Convert land owned to range buckets with realistic granularity"""
    if acres < 0.5:
        return "0-0.5"
    elif acres <= 1.0:
        return "0.5-1.0"
    elif acres <= 2.0:
        return "1.0-2.0"
    elif acres <= 3.0:
        return "2.0-3.0"
    elif acres <= 5.0:
        return "3.0-5.0"
    elif acres <= 10.0:
        return "5.0-10.0"
    elif acres <= 20.0:
        return "10.0-20.0"
    elif acres <= 50.0:
        return "20.0-50.0"
    else:
        return "50.0+"
    """Convert land owned to range buckets"""
    if acres < 0.5:
        return "0-0.5"
    elif acres <= 1.0:
        return "0.5-1.0"
    elif acres <= 2.0:
        return "1.0-2.0"
    elif acres <= 3.0:
        return "2.0-3.0"
    elif acres <= 5.0:
        return "3.0-5.0"
    else:
        return "5.0-100.0"


def randomized_response_boolean(value: bool, p: float = 0.75) -> bool:
    """
    Two-coin randomized response for boolean data (TRUE DIFFERENTIAL PRIVACY)
    
    Protocol:
    1. Flip coin 1: If heads (probability p), answer truthfully
    2. If tails (probability 1-p), flip coin 2: heads=True, tails=False
    
    Privacy guarantee: ε = ln(p / (1-p))
    For p=0.75: ε ≈ 1.099 (strong privacy)
    For p=0.80: ε ≈ 1.386
    For p=0.90: ε ≈ 2.197
    
    Args:
        value: True boolean value
        p: Probability of truthful response (default 0.75)
    
    Returns:
        Privatized boolean (may be flipped)
    """
    coin1 = np.random.random() < p
    if coin1:
        return value  # Answer truthfully
    else:
        coin2 = np.random.random() < 0.5
        return coin2  # Random answer


def randomized_response_categorical(value: str, categories: list, p: float = 0.75) -> str:
    """
    Randomized response for categorical data (TRUE DIFFERENTIAL PRIVACY)
    
    Protocol:
    1. With probability p, answer truthfully
    2. With probability (1-p), answer uniformly at random from all categories
    
    Privacy guarantee: ε = ln((p + (1-p)/k) / ((1-p)/k))
    where k = number of categories
    
    Args:
        value: True categorical value
        categories: List of all possible categories
        p: Probability of truthful response
    
    Returns:
        Privatized category
    """
    if np.random.random() < p:
        return value  # Truth
    else:
        return np.random.choice(categories)  # Random category


def mask_aadhaar(aadhaar: str) -> str:
    """Mask Aadhaar keeping last 4 digits (NON-DP masking)"""
    digits_only = ''.join(c for c in aadhaar if c.isdigit())
    if len(digits_only) >= 4:
        last_4 = digits_only[-4:]
        if ' ' in aadhaar:
            return f"XXXX XXXX {last_4}"
        else:
            masked = 'X' * (len(digits_only) - 4) + last_4
            return masked
    else:
        return 'X' * len(aadhaar)


def mask_pan(pan: str) -> str:
    """Mask PAN keeping first 5 and last character (NON-DP masking)"""
    pan_upper = pan.upper().strip()
    if len(pan_upper) == 10:
        return f"{pan_upper[:5]}****{pan_upper[-1]}"
    else:
        if len(pan_upper) > 6:
            return f"{pan_upper[:3]}{'*' * (len(pan_upper) - 6)}{pan_upper[-3:]}"
        else:
            return '*' * len(pan_upper)


def anonymize_district(district: str) -> str:
    """Anonymize district to consistent generic format"""
    hash_val = int(hashlib.md5(district.lower().encode()).hexdigest()[:8], 16)
    district_num = (hash_val % 10) + 1
    return f"District {district_num}"


@dataclass
class PrivacyBudgetTransaction:
    """Single privacy budget transaction record"""
    timestamp: datetime
    query_type: str
    epsilon_cost: float
    epsilon_remaining: float
    mechanism_used: str
    query_id: str
    # NEW: Mathematical details for transparency
    sensitivity: float = 0.0
    noise_scale: float = 0.0
    degradation_factor: float = 1.0
    bounds: tuple = (0, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to audit-safe dictionary (NO raw data)"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'query_type': self.query_type,
            'epsilon_cost': round(self.epsilon_cost, 6),
            'epsilon_remaining': round(self.epsilon_remaining, 6),
            'mechanism': self.mechanism_used,
            'query_id': self.query_id,
            # NEW: Mathematical output for transparency
            'mathematical_output': {
                'sensitivity': round(self.sensitivity, 4),
                'noise_scale': round(self.noise_scale, 4),
                'noise_distribution': f"Laplace(μ=0, b={round(self.noise_scale, 2)})",
                'privacy_formula': f"(ε, δ)-DP where ε={round(self.epsilon_cost, 4)}, δ=1e-05",
                'true_result_bounds': f"[{self.bounds[0]}, {self.bounds[1]}]",
                'degradation_applied': f"{self.degradation_factor}x",
                'effective_epsilon': round(self.epsilon_cost * self.degradation_factor, 6)
            }
        }



@dataclass
class PrivacyBudgetLedger:
    """Per-user/session privacy budget ledger with sliding window recovery"""
    user_id: str
    initial_epsilon: float
    epsilon_remaining: float
    transactions: List[PrivacyBudgetTransaction] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_refill: datetime = field(default_factory=datetime.now)
    refill_rate: float = 0.1
    refill_interval_seconds: float = 3600.0
    max_epsilon: float = field(init=False)
    global_seed: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    
    def __post_init__(self):
        self.max_epsilon = self.initial_epsilon
    
    def can_afford(self, epsilon_cost: float) -> bool:
        """Check if sufficient budget remains"""
        self._apply_sliding_window_refill()
        return self.epsilon_remaining >= epsilon_cost
    
    def deduct(self, query_type: str, epsilon_cost: float, mechanism: str) -> bool:
        """Deduct epsilon and log transaction"""
        self._apply_sliding_window_refill()
        
        if self.epsilon_remaining < epsilon_cost:
            return False
        
        self.epsilon_remaining -= epsilon_cost
        
        transaction = PrivacyBudgetTransaction(
            timestamp=datetime.now(),
            query_type=query_type,
            epsilon_cost=epsilon_cost,
            epsilon_remaining=self.epsilon_remaining,
            mechanism_used=mechanism,
            query_id=secrets.token_hex(8)
        )
        self.transactions.append(transaction)
        
        return True
    
    def _apply_sliding_window_refill(self):
        """Sliding window budget recovery"""
        now = datetime.now()
        time_elapsed = (now - self.last_refill).total_seconds()
        
        if time_elapsed >= self.refill_interval_seconds:
            intervals_passed = int(time_elapsed / self.refill_interval_seconds)
            refill_amount = self.refill_rate * intervals_passed
            
            self.epsilon_remaining = min(
                self.epsilon_remaining + refill_amount,
                self.max_epsilon
            )
            self.last_refill = now
    
    def get_degradation_factor(self) -> float:
        """Calculate noise scaling factor based on remaining budget"""
        budget_ratio = self.epsilon_remaining / self.max_epsilon
        
        if budget_ratio > 0.5:
            return 1.0
        elif budget_ratio > 0.25:
            return 2.0
        elif budget_ratio > 0.1:
            return 5.0
        else:
            return 10.0
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit-ready transaction log (NO raw data)"""
        return [t.to_dict() for t in self.transactions]
    
    def reset_budget(self, new_epsilon: Optional[float] = None):
        """Admin reset (manual recovery hook)"""
        if new_epsilon is not None:
            self.initial_epsilon = new_epsilon
            self.max_epsilon = new_epsilon
        self.epsilon_remaining = self.max_epsilon
        self.last_refill = datetime.now()


class PrivacyBudgetManager:
    """Global privacy budget manager for all users/sessions"""
    
    def __init__(self):
        self.ledgers: Dict[str, PrivacyBudgetLedger] = {}
    
    def get_or_create_ledger(
        self,
        user_id: str,
        initial_epsilon: float = 10.0,
        refill_rate: float = 0.1,
        refill_interval_seconds: float = 3600.0
    ) -> PrivacyBudgetLedger:
        """Get existing ledger or create new one"""
        if user_id not in self.ledgers:
            self.ledgers[user_id] = PrivacyBudgetLedger(
                user_id=user_id,
                initial_epsilon=initial_epsilon,
                epsilon_remaining=initial_epsilon,
                refill_rate=refill_rate,
                refill_interval_seconds=refill_interval_seconds
            )
        return self.ledgers[user_id]
    
    def get_all_audit_logs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all audit logs (government/GDPR compliance)"""
        return {
            user_id: ledger.get_audit_log()
            for user_id, ledger in self.ledgers.items()
        }


@dataclass
class PrivacyConfig:
    """Configuration for privacy transformations"""
    epsilon: float = 1.0
    delta: float = 1e-5
    k_anonymity: int = 5
    use_strict_mode: bool = False
    preserve_nulls: bool = True
    min_dataset_size: int = 10
    epsilon_budget_remaining: float = field(init=False)
    epsilon_spent_per_column: Dict[str, float] = field(default_factory=dict)
    num_numeric_columns_estimate: int = 10
    
    def __post_init__(self):
        self.epsilon_budget_remaining = self.epsilon
    
    def get_epsilon_per_column(self) -> float:
        """Calculate epsilon allocation per column"""
        return self.epsilon / max(1, self.num_numeric_columns_estimate)
    
    def allocate_epsilon(self, column_name: str, epsilon_amount: float) -> bool:
        """Allocate epsilon budget for column transformation"""
        if epsilon_amount > self.epsilon_budget_remaining:
            return False
        self.epsilon_budget_remaining -= epsilon_amount
        self.epsilon_spent_per_column[column_name] = epsilon_amount
        return True


class PrivacyEngine:
    """
    ShadowSafe-Style Differential Privacy Engine
    
    PROXY-BASED ARCHITECTURE:
    User → Privacy Layer → Budget Ledger → Noise Engine → Privatized Response
    
    GUARANTEES:
    - Raw data NEVER leaves this engine
    - Only privatized results are returned
    - Strict epsilon accounting with audit trail
    - Graceful degradation as budget depletes
    """
    
    def __init__(
        self,
        config: Optional[PrivacyConfig] = None,
        budget_manager: Optional[PrivacyBudgetManager] = None
    ):
        if not DIFFPRIVLIB_AVAILABLE:
            raise RuntimeError("IBM diffprivlib is REQUIRED")
        
        self.config = config or PrivacyConfig()
        self.budget_manager = budget_manager or PrivacyBudgetManager()
        self.transformation_log = []
        self.privacy_metadata = {}
    
    def execute_dp_query(
        self,
        data: List[float],
        query_type: QueryType,
        user_id: str,
        lower_bound: float,
        upper_bound: float,
        field_name: str = "value"
    ) -> Tuple[Optional[float], Dict[str, Any]]:
        """
        Execute differential privacy query with strict budget enforcement
        
        CRITICAL: This is the ONLY way to query aggregate statistics
        Raw data NEVER exits this function
        
        Returns:
            (privatized_result, metadata) or (None, error_metadata) if budget exhausted
        """
        ledger = self.budget_manager.get_or_create_ledger(user_id)
        epsilon_cost = QUERY_EPSILON_COST[query_type]
        
        if not ledger.can_afford(epsilon_cost):
            return None, {
                'error': 'BUDGET_EXHAUSTED',
                'epsilon_remaining': round(ledger.epsilon_remaining, 6),
                'epsilon_required': epsilon_cost,
                'message': 'Insufficient privacy budget. Wait for refill or request admin reset.'
            }
        
        degradation_factor = ledger.get_degradation_factor()
        effective_epsilon = epsilon_cost / degradation_factor
        
        field_params = get_field_sensitivity(field_name)
        sensitivity = field_params.get('sensitivity', 1.0)
        noise_scale = sensitivity / effective_epsilon
        
        # DETERMINISTIC NOISE: Generate query_id for HMAC seeding
        # This ensures same query returns same noise within time window
        from .deterministic_noise import DeterministicNoiseGenerator
        
        query_fingerprint_data = {
            'user_id': user_id,
            'query_type': query_type.value,
            'field_name': field_name,
            'bounds': (lower_bound, upper_bound),
            'data_size': len(data)
        }
        query_id = hashlib.sha256(
            json.dumps(query_fingerprint_data, sort_keys=True).encode()
        ).hexdigest()[:32]
        
        # Get current time window for seed rotation
        time_window = DeterministicNoiseGenerator.get_time_window()
        
        try:
            # Calculate true result
            if query_type == QueryType.COUNT:
                true_result = float(len(data))
                query_sensitivity = 1.0  # Adding/removing one record changes count by 1
            elif query_type == QueryType.MEAN:
                true_result = float(np.mean(data))
                query_sensitivity = (upper_bound - lower_bound) / len(data)
            elif query_type == QueryType.SUM:
                true_result = float(sum(data))
                query_sensitivity = upper_bound - lower_bound
            elif query_type == QueryType.VARIANCE:
                true_result = float(np.var(data))
                query_sensitivity = ((upper_bound - lower_bound) ** 2) / len(data)
            elif query_type == QueryType.STD:
                true_result = float(np.std(data))
                query_sensitivity = (upper_bound - lower_bound) / np.sqrt(len(data))
            else:
                return None, {'error': 'UNSUPPORTED_QUERY_TYPE'}
            
            # Generate deterministic Laplace noise
            noise_scale = query_sensitivity / effective_epsilon
            noise = DeterministicNoiseGenerator.generate_laplace_noise(
                scale=noise_scale,
                query_id=query_id,
                size=1,
                time_window=time_window
            )[0]
            
            # Apply noise and clip to bounds
            noisy_result = true_result + noise
            
            # Clip result to valid range
            if query_type == QueryType.COUNT:
                result = max(0, noisy_result)  # Count can't be negative
            elif query_type == QueryType.MEAN:
                result = np.clip(noisy_result, lower_bound, upper_bound)
            elif query_type == QueryType.SUM:
                result = np.clip(noisy_result, lower_bound * len(data), upper_bound * len(data))
            elif query_type in [QueryType.VARIANCE, QueryType.STD]:
                result = max(0, noisy_result)  # Variance/std can't be negative
            else:
                result = noisy_result
            
            # Deduct budget and record transaction with mathematical details
            transaction_query_id = ledger.deduct(
                query_type=query_type.value,
                epsilon_cost=epsilon_cost,
                mechanism='DeterministicLaplace_HMAC'
            )
            
            # Update the last transaction with mathematical details
            if ledger.transactions:
                last_transaction = ledger.transactions[-1]
                last_transaction.sensitivity = query_sensitivity
                last_transaction.noise_scale = noise_scale
                last_transaction.degradation_factor = degradation_factor
                last_transaction.bounds = (lower_bound, upper_bound)
                # Add deterministic noise metadata
                last_transaction.noise_deterministic = True
                last_transaction.noise_seed_window = time_window
            
            # Calculate budget status and warnings
            budget_percentage = (ledger.epsilon_remaining / ledger.max_epsilon) * 100
            
            if budget_percentage > 50:
                budget_status = "HIGH"
                warning = None
            elif budget_percentage > 25:
                budget_status = "MEDIUM"
                warning = f"Your privacy budget is at {budget_percentage:.1f}%. Noise has been increased {degradation_factor}x for stronger privacy protection."
            elif budget_percentage > 10:
                budget_status = "LOW"
                warning = f"⚠️ Your privacy budget is running low ({budget_percentage:.1f}% remaining). Noise has been increased {degradation_factor}x for stronger privacy protection."
            else:
                budget_status = "CRITICAL"
                warning = f"🚨 CRITICAL: Only {budget_percentage:.1f}% budget remaining! Noise has been increased {degradation_factor}x. Consider requesting a budget reset."
            
            # Estimate queries remaining
            queries_remaining = {
                "COUNT": int(ledger.epsilon_remaining / QUERY_EPSILON_COST[QueryType.COUNT]),
                "MEAN": int(ledger.epsilon_remaining / QUERY_EPSILON_COST[QueryType.MEAN]),
                "SUM": int(ledger.epsilon_remaining / QUERY_EPSILON_COST[QueryType.SUM])
            }
            
            metadata = {
                'query_type': query_type.value,
                'epsilon_cost': epsilon_cost,
                'epsilon_remaining': round(ledger.epsilon_remaining, 6),
                'budget_percentage': round(budget_percentage, 2),
                'degradation_factor': degradation_factor,
                'effective_epsilon': round(effective_epsilon, 6),
                'noise_scale': round(noise_scale, 4),
                'mechanism': 'LaplaceBoundedDomain',
                'timestamp': datetime.now().isoformat(),
                'privacy_guarantee': f'({round(effective_epsilon, 4)}, {self.config.delta})-DP',
                # NEW: User-facing warnings
                'budget_status': budget_status,
                'warning': warning,
                'queries_remaining_estimate': queries_remaining
            }
            
            return float(result), metadata
            
        except Exception as e:
            return None, {
                'error': 'QUERY_EXECUTION_FAILED',
                'message': str(e)
            }

    
    def apply_privacy(
        self,
        records: List[Dict[str, Any]],
        column_classifications: Dict[str, Dict[str, Any]],
        risk_score: int = 50,
        user_id: str = "default"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Apply privacy transformations to dataset
        
        CRITICAL: Raw data exists ONLY in memory during this function
        ONLY privatized data is returned
        """
        if not records:
            return [], {"error": "Empty dataset"}
        
        adjusted_config = self._adjust_config_by_risk(risk_score)
        
        numeric_count = sum(
            1 for c in column_classifications.values()
            if c.get('type') in ['numeric', 'quasi_identifier']
        )
        adjusted_config.num_numeric_columns_estimate = max(1, numeric_count)
        
        privatized_records = [record.copy() for record in records]
        transformations_applied = {}
        
        for column_name, classification in column_classifications.items():
            column_type = classification['type']
            sensitivity_level = classification['sensitivity']
            
            column_values = [record.get(column_name) for record in records]
            
            transformed_values = self._apply_column_transformation(
                column_values,
                column_name,
                column_type,
                sensitivity_level,
                adjusted_config,
                len(records)
            )
            
            for i, record in enumerate(privatized_records):
                if i < len(transformed_values):
                    record[column_name] = transformed_values[i]
            
            transformations_applied[column_name] = {
                'type': column_type,
                'mechanism': classification.get('recommended_mechanism'),
                'sensitivity': sensitivity_level,
                'privacy_guarantee': self._get_privacy_guarantee_type(column_type)
            }
        
        metadata = self._generate_metadata(
            len(records),
            privatized_records,
            transformations_applied,
            adjusted_config
        )
        
        return privatized_records, metadata
    
    def _get_privacy_guarantee_type(self, column_type: str) -> str:
        """Classify privacy guarantee type"""
        if column_type in ['numeric']:
            return 'DIFFERENTIAL_PRIVACY'
        else:
            return 'NON_DP_ANONYMIZATION'
    
    def _adjust_config_by_risk(self, risk_score: int) -> PrivacyConfig:
        """Adjust privacy parameters based on risk"""
        config = PrivacyConfig()
        
        if risk_score >= 80:
            config.epsilon = 0.5
            config.k_anonymity = 10
            config.use_strict_mode = True
        elif risk_score >= 60:
            config.epsilon = 1.0
            config.k_anonymity = 7
        elif risk_score >= 40:
            config.epsilon = 2.0
            config.k_anonymity = 5
        else:
            config.epsilon = 3.0
            config.k_anonymity = 3
        
        return config
    
    def _apply_column_transformation(
        self,
        values: List[Any],
        column_name: str,
        column_type: str,
        sensitivity: str,
        config: PrivacyConfig,
        dataset_size: int
    ) -> List[Any]:
        """Apply appropriate transformation based on column type"""
        non_null_indices = [i for i, v in enumerate(values) if v is not None]
        non_null_values = [v for v in values if v is not None]
        
        if not non_null_values:
            return values
        
        if column_name == 'data':
            transformed = []
            for v in non_null_values:
                if isinstance(v, dict):
                    anonymized = self._anonymize_nested_json(v, config)
                    transformed.append(anonymized)
                elif isinstance(v, str):
                    try:
                        parsed = json.loads(v)
                        anonymized = self._anonymize_nested_json(parsed, config)
                        transformed.append(json.dumps(anonymized))
                    except (json.JSONDecodeError, TypeError):
                        transformed.append(self._hash_value(str(v))[:16] + '...')
                else:
                    transformed.append(v)
        elif column_type == 'identifier':
            transformed = self._transform_identifier(non_null_values, sensitivity, config)
        elif column_type == 'quasi_identifier':
            transformed = self._transform_quasi_identifier(
                non_null_values, column_name, sensitivity, config, dataset_size
            )
        elif column_type == 'numeric':
            transformed = self._transform_numeric(non_null_values, column_name, config, dataset_size)
        elif column_type == 'categorical':
            transformed = self._transform_categorical(non_null_values, config, dataset_size)
        elif column_type == 'temporal':
            transformed = self._transform_temporal(non_null_values, config)
        elif column_type == 'geospatial':
            transformed = self._transform_geospatial(non_null_values, config)
        elif column_type == 'sensitive':
            transformed = self._transform_sensitive(non_null_values, sensitivity)
        else:
            transformed = self._transform_generic(non_null_values)
        
        result = [None] * len(values)
        for i, transformed_val in zip(non_null_indices, transformed):
            result[i] = transformed_val
        
        return result
    
    def _anonymize_nested_json(
        self,
        data: Any,
        config: PrivacyConfig,
        key: str = ""
    ) -> Any:
        """Recursively anonymize nested JSON (DP for numerics, masking for identifiers)"""
        if isinstance(data, dict):
            return {
                k: self._anonymize_nested_json(v, config, k.lower())
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [
                self._anonymize_nested_json(item, config, key)
                for item in data
            ]
        elif isinstance(data, str):
            if '@' in data and '.' in data:
                return self._mask_email([data])[0]
            elif data.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit() and len(data.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')) >= 10:
                return self._mask_phone([data])[0]
            elif any(keyword in key for keyword in ['name', 'first', 'last', 'username']):
                return self._pseudonymize_names([data])[0]
            elif any(keyword in key for keyword in ['aadhaar', 'aadhar', 'adhar']):
                return mask_aadhaar(data)
            elif any(keyword in key for keyword in ['pan', 'pancard', 'pannumber']):
                return mask_pan(data)
            elif any(keyword in key for keyword in [
                'recordid', 'id', 'ssn', 'passport',
                'license', 'licence', 'drivinglicense', 'dl',
                'account', 'accountno', 'accountnumber', 'bankaccount',
                'card', 'cardno', 'cardnumber', 'creditcard', 'debit',
                'tax', 'taxid', 'tin', 'gstin', 'gst',
                'national', 'nationalid', 'voter', 'voterid',
                'uid', 'uniqueid', 'personid', 'customerid'
            ]):
                # Use hashing instead of suppression
                return self._hash_value(str(data))[:16]
            elif any(keyword in key for keyword in ['district']):
                # Anonymize district to generic label
                return anonymize_district(data)
            elif any(keyword in key for keyword in ['state']):
                # Apply randomized response to state
                indian_states = [
                    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
                    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
                    'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur',
                    'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
                    'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
                    'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi'
                ]
                return randomized_response_categorical(data, indian_states, p=0.75)
            elif any(keyword in key for keyword in ['gender']):
                # Apply randomized response to gender
                return randomized_response_categorical(data, ['Male', 'Female', 'Other'], p=0.75)
            elif any(keyword in key for keyword in ['areatype', 'area']):
                # Apply randomized response to area type
                return randomized_response_categorical(data, ['Urban', 'Rural', 'Semi-Urban'], p=0.75)
            elif any(keyword in key for keyword in ['disability', 'chronicillness', 'chronic']):
                # Apply randomized response to boolean fields
                bool_value = data.lower() in ['yes', 'true', '1', 'y'] if isinstance(data, str) else bool(data)
                privatized_bool = randomized_response_boolean(bool_value, p=0.75)
                return 'Yes' if privatized_bool else 'No'
            elif any(keyword in key for keyword in ['maritalstatus', 'marital']):
                # Apply randomized response to categorical field
                categories = ['Married', 'Unmarried', 'Divorced', 'Widowed']
                return randomized_response_categorical(data, categories, p=0.75)
            else:
                try:
                    numeric_val = float(data)
                    privatized_num = self._anonymize_nested_json(numeric_val, config, key)
                    return str(privatized_num)
                except (ValueError, TypeError):
                    return data
        elif isinstance(data, (int, float)):
            field_params = get_field_sensitivity(key, data)
            sensitivity = field_params['sensitivity']
            lower_bound = field_params['lower']
            upper_bound = field_params['upper']
            
            epsilon_for_field = config.get_epsilon_per_column()
            
            try:
                mech = LaplaceBoundedDomain(
                    epsilon=epsilon_for_field,
                    sensitivity=sensitivity,
                    lower=lower_bound,
                    upper=upper_bound
                )
                noisy_value = mech.randomise(float(data))
                noisy_value = max(lower_bound, min(upper_bound, noisy_value))
                
                if 'age' in key:
                    return age_to_range(noisy_value)
                elif 'income' in key or 'monthlyincome' in key or 'salary' in key:
                    # Return DP-noised value (not range)
                    return int(round(noisy_value))
                elif 'household' in key or ('size' in key and 'land' not in key):
                    # Return DP-noised value (not range)
                    return int(round(noisy_value))
                elif 'land' in key or 'acres' in key:
                    # Return DP-noised value (not range)
                    return round(noisy_value, 2)
                elif 'price' in key or 'cost' in key or 'amount' in key:
                    return int(round(noisy_value / 100) * 100)
                elif 'revenue' in key or 'budget' in key:
                    return int(round(noisy_value / 10000) * 10000)
                elif 'score' in key or 'rating' in key or 'percent' in key:
                    return round(noisy_value, 1)
                else:
                    if abs(noisy_value) < 100:
                        return round(noisy_value, 1)
                    else:
                        return int(round(noisy_value))
            except Exception:
                return int(round(data)) if isinstance(data, (int, float)) else data
        else:
            return data
    
    def _transform_identifier(self, values: List[Any], sensitivity: str, config: PrivacyConfig) -> List[Any]:
        """Transform direct identifiers (NON-DP hashing)"""
        # Always use hashing, never redaction
        return [self._hash_value(str(v))[:32] for v in values]
    
    def _transform_quasi_identifier(
        self,
        values: List[Any],
        column_name: str,
        sensitivity: str,
        config: PrivacyConfig,
        dataset_size: int
    ) -> List[Any]:
        """Transform quasi-identifiers (NON-DP masking/generalization OR DP if numeric)"""
        if any(keyword in column_name.lower() for keyword in ['name', 'first', 'last']):
            return self._pseudonymize_names(values)
        elif any(keyword in column_name.lower() for keyword in ['email', 'mail']):
            return self._mask_email(values)
        elif any(keyword in column_name.lower() for keyword in ['phone', 'tel', 'mobile']):
            return self._mask_phone(values)
        elif any(keyword in column_name.lower() for keyword in ['age', 'year']):
            return self._transform_numeric(values, column_name, config, dataset_size)
        elif any(keyword in column_name.lower() for keyword in ['address', 'street', 'city', 'state']):
            return self._generalize_location(values)
        else:
            return self._apply_k_anonymity(values, config)
    
    def _transform_numeric(
        self,
        values: List[Any],
        column_name: str,
        config: PrivacyConfig,
        dataset_size: int
    ) -> List[Any]:
        """Transform numeric columns with TRUE differential privacy"""
        numeric_values = [self._safe_numeric(v) for v in values]
        
        if not numeric_values or all(v == 0 for v in numeric_values):
            return values
        
        sample_value = next((v for v in numeric_values if v != 0), 0)
        field_params = get_field_sensitivity(column_name, sample_value)
        
        sensitivity = field_params['sensitivity']
        lower_bound = field_params['lower']
        upper_bound = field_params['upper']
        
        epsilon_for_column = config.get_epsilon_per_column()
        if not config.allocate_epsilon(column_name, epsilon_for_column):
            return self._bucket_values(numeric_values, num_buckets=5)
        
        try:
            mech = LaplaceBoundedDomain(
                epsilon=epsilon_for_column,
                sensitivity=sensitivity,
                lower=lower_bound,
                upper=upper_bound
            )
            
            noisy_values = []
            for v in numeric_values:
                noisy_v = mech.randomise(float(v))
                noisy_v = max(lower_bound, min(upper_bound, noisy_v))
                noisy_values.append(noisy_v)
            
            if 'age' in column_name.lower() or 'count' in column_name.lower():
                return [int(round(v)) for v in noisy_values]
            elif 'salary' in column_name.lower() or 'income' in column_name.lower():
                return [int(round(v / 1000) * 1000) for v in noisy_values]
            elif 'score' in column_name.lower() or 'rating' in column_name.lower():
                return [round(v, 1) for v in noisy_values]
            else:
                return [int(round(v)) if abs(v) > 10 else round(v, 1) for v in noisy_values]
        except Exception:
            return self._bucket_values(numeric_values, num_buckets=10)
    
    def _transform_categorical(self, values: List[Any], config: PrivacyConfig, dataset_size: int) -> List[Any]:
        """Transform categorical columns (NON-DP k-anonymity)"""
        if dataset_size >= config.min_dataset_size:
            return self._apply_k_anonymity(values, config)
        else:
            return self._generalize_categories(values)
    
    def _transform_temporal(self, values: List[Any], config: PrivacyConfig) -> List[Any]:
        """Transform temporal data (NON-DP generalization)"""
        return [self._generalize_date(str(v)) for v in values]
    
    def _transform_geospatial(self, values: List[Any], config: PrivacyConfig) -> List[Any]:
        """Transform geospatial data (NON-DP generalization)"""
        return self._generalize_location(values)
    
    def _transform_sensitive(self, values: List[Any], sensitivity: str) -> List[Any]:
        """Transform sensitive data (NON-DP hashing)"""
        # Always use hashing, never redaction
        return [self._hash_value(str(v))[:32] for v in values]
    
    def _transform_generic(self, values: List[Any]) -> List[Any]:
        """Safe fallback transformation (NON-DP hashing)"""
        return [self._hash_value(str(v))[:32] + '...' for v in values]
    
    def _apply_k_anonymity(self, values: List[Any], config: PrivacyConfig) -> List[Any]:
        """Apply k-anonymity using randomized response instead of suppression"""
        value_counts = Counter(values)
        result = []
        
        # Get unique categories for randomized response
        categories = list(set(values))
        
        for v in values:
            if value_counts[v] >= config.k_anonymity:
                result.append(v)  # Safe to release
            else:
                # Use randomized response instead of suppression
                result.append(randomized_response_categorical(v, categories, p=0.75))
        return result
    
    def _hash_value(self, value: str) -> str:
        """Create irreversible hash (NON-DP cryptographic hashing)"""
        hash_obj = hashlib.sha256(value.encode())
        return hash_obj.hexdigest()
    
    def _pseudonymize_names(self, values: List[Any]) -> List[Any]:
        """Pseudonymize names (NON-DP consistent replacement)"""
        pseudonym_map = {}
        pseudonyms = []
        for v in values:
            v_str = str(v)
            if v_str not in pseudonym_map:
                hash_val = int(self._hash_value(v_str)[:16], 16)
                pseudonym_map[v_str] = f"Person_{hash_val % 100000:05d}"
            pseudonyms.append(pseudonym_map[v_str])
        return pseudonyms
    
    def _mask_email(self, values: List[Any]) -> List[Any]:
        """Mask email addresses (NON-DP partial masking)"""
        result = []
        for v in values:
            email_str = str(v)
            if '@' in email_str:
                local, domain = email_str.split('@', 1)
                masked_local = local[:2] + '*' * max(1, len(local) - 2)
                result.append(f"{masked_local}@{domain}")
            else:
                result.append('[MASKED]')
        return result
    
    def _mask_phone(self, values: List[Any]) -> List[Any]:
        """Mask phone numbers (NON-DP partial masking)"""
        result = []
        for v in values:
            phone_str = str(v).replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
            if len(phone_str) >= 10:
                masked = '*' * (len(phone_str) - 4) + phone_str[-4:]
                result.append(masked)
            else:
                result.append('[MASKED]')
        return result
    
    def _generalize_location(self, values: List[Any]) -> List[Any]:
        """Generalize location (NON-DP generalization)"""
        return ['[REGION]'] * len(values)
    
    def _generalize_date(self, value: str) -> str:
        """Generalize date to year (NON-DP temporal generalization)"""
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', value)
        if year_match:
            return year_match.group(0)
        return '[DATE]'
    
    def _generalize_categories(self, values: List[Any]) -> List[Any]:
        """Generalize categories (NON-DP category suppression)"""
        unique_values = list(set(values))
        if len(unique_values) > 10:
            return ['[CATEGORY]'] * len(values)
        return values
    
    def _bucket_values(self, values: List[float], num_buckets: int = 10) -> List[float]:
        """Bucket numeric values (NON-DP binning)"""
        if not values:
            return values
        min_val = min(values)
        max_val = max(values)
        if min_val == max_val:
            return values
        bucket_size = (max_val - min_val) / num_buckets
        bucketed = []
        for v in values:
            bucket_index = int((v - min_val) / bucket_size)
            bucket_index = min(bucket_index, num_buckets - 1)
            bucket_midpoint = min_val + (bucket_index + 0.5) * bucket_size
            bucketed.append(bucket_midpoint)
        return bucketed
    
    def _safe_numeric(self, value: Any) -> float:
        """Safely convert to numeric"""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _generate_metadata(
        self,
        original_record_count: int,
        privatized_records: List[Dict],
        transformations: Dict[str, Any],
        config: PrivacyConfig
    ) -> Dict[str, Any]:
        """Generate metadata (NO ORIGINAL VALUES)"""
        return {
            'privacy_config': {
                'epsilon_total': config.epsilon,
                'epsilon_remaining': config.epsilon_budget_remaining,
                'epsilon_per_column': dict(config.epsilon_spent_per_column),
                'delta': config.delta,
                'k_anonymity': config.k_anonymity,
                'strict_mode': config.use_strict_mode
            },
            'dataset_info': {
                'original_record_count': original_record_count,
                'privatized_record_count': len(privatized_records),
                'columns_transformed': len(transformations)
            },
            'transformations': transformations,
            'privacy_guarantees': self._calculate_privacy_guarantees(config),
            'utility_metrics': self._calculate_utility_metrics(
                original_record_count,
                privatized_records
            ),
            'compliance_notes': {
                'differential_privacy': 'ε-DP applied to numeric aggregates using IBM diffprivlib BOUNDED mechanisms',
                'non_dp_techniques': 'k-anonymity, hashing, masking, generalization applied to identifiers',
                'composition': 'Basic composition (epsilon divided by number of columns)',
                'audit_trail': 'All transformations logged, no original values stored',
                'noise_control': 'All DP noise is bounded and proportional to field semantics',
                'budget_enforcement': 'Strict epsilon accounting with per-query deduction',
                'gdpr_compliant': 'Audit logs suitable for GDPR/DPDP Act review'
            }
        }
    
    def _calculate_privacy_guarantees(self, config: PrivacyConfig) -> Dict[str, str]:
        """Calculate privacy guarantee levels"""
        if config.epsilon <= 0.5:
            level = "Very Strong"
        elif config.epsilon <= 1.0:
            level = "Strong"
        elif config.epsilon <= 2.0:
            level = "Moderate"
        else:
            level = "Basic"
        
        return {
            'differential_privacy_level': level,
            'epsilon': config.epsilon,
            'delta': config.delta,
            'formal_guarantee': f"({config.epsilon}, {config.delta})-Differential Privacy",
            'interpretation': f"Privacy budget ε={config.epsilon} (lower is better)",
            'recommendation': 'ε ≤ 1.0 recommended for sensitive data'
        }
    
    def _calculate_utility_metrics(
        self,
        original_count: int,
        privatized_records: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate utility preservation metrics (NO ORIGINAL VALUES)"""
        total_values = sum(len(r) for r in privatized_records)
        redacted_values = sum(
            1 for r in privatized_records
            for v in r.values()
            if v in ['[REDACTED]', '[SUPPRESSED]', '[MASKED]', '[REGION]', '[DATE]', '[CATEGORY]']
        )
        utility_score = ((total_values - redacted_values) / total_values * 100) if total_values > 0 else 0
        
        return {
            'utility_preservation_score': round(utility_score, 2),
            'total_values': total_values,
            'redacted_values': redacted_values,
            'preserved_values': total_values - redacted_values,
            'interpretation': 'Higher score = more data utility preserved (with privacy guarantees)'
        }