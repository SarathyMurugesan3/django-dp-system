"""
Privacy Policies
Configurable rules and transformations for different privacy requirements
"""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple


class PrivacyLevel(Enum):
    """Privacy protection levels"""
    MINIMAL = 1      # Basic protection, maximize utility
    STANDARD = 2     # Balanced protection
    STRICT = 3       # Strong protection
    MAXIMUM = 4      # Maximum protection, utility may suffer


@dataclass
class PrivacyPolicy:
    """Configuration for privacy transformations"""
    name: str
    level: PrivacyLevel
    epsilon: float
    delta: float
    k_anonymity: int
    description: str
    
    # Transformation rules
    transform_identifiers: bool = True
    transform_quasi_identifiers: bool = True
    add_noise_to_numeric: bool = True
    generalize_categorical: bool = True
    redact_sensitive: bool = True
    
    # Advanced options
    preserve_statistical_properties: bool = True
    enable_t_closeness: bool = False
    enable_l_diversity: bool = False
    
    # Utility vs Privacy trade-off (0-1, higher = more utility)
    utility_weight: float = 0.5


class PolicyLibrary:
    """Pre-configured privacy policies for different use cases"""
    
    @staticmethod
    def get_policy(policy_name: str) -> PrivacyPolicy:
        """Get a predefined policy by name"""
        
        policies = {
            'minimal': PolicyLibrary.minimal_protection(),
            'standard': PolicyLibrary.standard_protection(),
            'strict': PolicyLibrary.strict_protection(),
            'maximum': PolicyLibrary.maximum_protection(),
            'research': PolicyLibrary.research_policy(),
            'production': PolicyLibrary.production_policy(),
            'healthcare': PolicyLibrary.healthcare_policy(),
            'financial': PolicyLibrary.financial_policy(),
        }
        
        return policies.get(policy_name.lower(), PolicyLibrary.standard_protection())
    
    @staticmethod
    def minimal_protection() -> PrivacyPolicy:
        """Minimal privacy protection - maximize data utility"""
        return PrivacyPolicy(
            name="Minimal Protection",
            level=PrivacyLevel.MINIMAL,
            epsilon=5.0,
            delta=1e-4,
            k_anonymity=3,
            description="Basic privacy with maximum utility preservation",
            transform_identifiers=True,
            transform_quasi_identifiers=False,
            add_noise_to_numeric=False,
            generalize_categorical=False,
            redact_sensitive=True,
            preserve_statistical_properties=True,
            utility_weight=0.9
        )
    
    @staticmethod
    def standard_protection() -> PrivacyPolicy:
        """Standard privacy protection - balanced approach"""
        return PrivacyPolicy(
            name="Standard Protection",
            level=PrivacyLevel.STANDARD,
            epsilon=2.0,  # Higher epsilon = less privacy, more utility
            delta=1e-5,
            k_anonymity=5,
            description="Balanced privacy and utility",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=True,
            redact_sensitive=True,
            preserve_statistical_properties=True,
            utility_weight=0.5
        )
    
    @staticmethod
    def strict_protection() -> PrivacyPolicy:
        """Strict privacy protection"""
        return PrivacyPolicy(
            name="Strict Protection",
            level=PrivacyLevel.STRICT,
            epsilon=1.0,  # Lower epsilon = better privacy
            delta=1e-6,
            k_anonymity=10,
            description="Strong privacy with moderate utility",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=True,
            redact_sensitive=True,
            preserve_statistical_properties=False,
            enable_l_diversity=True,
            utility_weight=0.3
        )
    
    @staticmethod
    def maximum_protection() -> PrivacyPolicy:
        """Maximum privacy protection"""
        return PrivacyPolicy(
            name="Maximum Protection",
            level=PrivacyLevel.MAXIMUM,
            epsilon=0.5,
            delta=1e-7,
            k_anonymity=20,
            description="Maximum privacy, utility may be limited",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=True,
            redact_sensitive=True,
            preserve_statistical_properties=False,
            enable_t_closeness=True,
            enable_l_diversity=True,
            utility_weight=0.1
        )
    
    @staticmethod
    def research_policy() -> PrivacyPolicy:
        """Policy optimized for research datasets"""
        return PrivacyPolicy(
            name="Research Policy",
            level=PrivacyLevel.STANDARD,
            epsilon=2.5,
            delta=1e-5,
            k_anonymity=5,
            description="Preserve statistical properties for research",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=False,  # Keep categories intact
            redact_sensitive=True,
            preserve_statistical_properties=True,
            utility_weight=0.7
        )
    
    @staticmethod
    def production_policy() -> PrivacyPolicy:
        """Policy for production environments"""
        return PrivacyPolicy(
            name="Production Policy",
            level=PrivacyLevel.STRICT,
            epsilon=1.0,
            delta=1e-6,
            k_anonymity=7,
            description="Production-grade privacy protection",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=True,
            redact_sensitive=True,
            preserve_statistical_properties=True,
            enable_l_diversity=True,
            utility_weight=0.4
        )
    
    @staticmethod
    def healthcare_policy() -> PrivacyPolicy:
        """HIPAA-compliant policy for healthcare data"""
        return PrivacyPolicy(
            name="Healthcare Policy (HIPAA)",
            level=PrivacyLevel.STRICT,
            epsilon=0.8,
            delta=1e-6,
            k_anonymity=10,
            description="HIPAA-compliant privacy for healthcare",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=True,
            redact_sensitive=True,
            preserve_statistical_properties=True,
            enable_t_closeness=True,
            enable_l_diversity=True,
            utility_weight=0.3
        )
    
    @staticmethod
    def financial_policy() -> PrivacyPolicy:
        """Policy for financial data"""
        return PrivacyPolicy(
            name="Financial Policy",
            level=PrivacyLevel.STRICT,
            epsilon=1.0,
            delta=1e-6,
            k_anonymity=10,
            description="Privacy for financial data",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=True,
            redact_sensitive=True,
            preserve_statistical_properties=True,
            enable_l_diversity=True,
            utility_weight=0.4
        )
    
    @staticmethod
    def custom_policy(
        epsilon: float,
        k_anonymity: int,
        utility_weight: float = 0.5
    ) -> PrivacyPolicy:
        """Create a custom policy with specific parameters"""
        
        # Determine level based on epsilon
        if epsilon >= 3.0:
            level = PrivacyLevel.MINIMAL
        elif epsilon >= 1.5:
            level = PrivacyLevel.STANDARD
        elif epsilon >= 0.8:
            level = PrivacyLevel.STRICT
        else:
            level = PrivacyLevel.MAXIMUM
        
        return PrivacyPolicy(
            name="Custom Policy",
            level=level,
            epsilon=epsilon,
            delta=1e-5,
            k_anonymity=k_anonymity,
            description=f"Custom policy (ε={epsilon}, k={k_anonymity})",
            transform_identifiers=True,
            transform_quasi_identifiers=True,
            add_noise_to_numeric=True,
            generalize_categorical=True,
            redact_sensitive=True,
            preserve_statistical_properties=True,
            utility_weight=utility_weight
        )
    
    @staticmethod
    def list_available_policies() -> List[Dict[str, Any]]:
        """List all available predefined policies"""
        
        policy_names = [
            'minimal', 'standard', 'strict', 'maximum',
            'research', 'production', 'healthcare', 'financial'
        ]
        
        policies_info = []
        for name in policy_names:
            policy = PolicyLibrary.get_policy(name)
            policies_info.append({
                'name': name,
                'display_name': policy.name,
                'level': policy.level.name,
                'epsilon': policy.epsilon,
                'k_anonymity': policy.k_anonymity,
                'description': policy.description,
                'utility_weight': policy.utility_weight
            })
        
        return policies_info


class TransformationRules:
    """Rules for specific transformation scenarios"""
    
    @staticmethod
    def get_column_specific_rules() -> Dict[str, Dict[str, Any]]:
        """Get rules for specific column types"""
        
        return {
            'email': {
                'must_transform': True,
                'methods': ['masking', 'hashing', 'pseudonymization'],
                'preserve_domain': False,
                'min_protection': 'high'
            },
            'ssn': {
                'must_transform': True,
                'methods': ['redaction', 'hashing'],
                'preserve_format': False,
                'min_protection': 'critical'
            },
            'name': {
                'must_transform': True,
                'methods': ['pseudonymization', 'masking', 'generalization'],
                'preserve_length': True,
                'min_protection': 'moderate'
            },
            'age': {
                'must_transform': True,
                'methods': ['laplace_noise', 'bucketing', 'generalization'],
                'max_noise': 5,  # years
                'min_protection': 'moderate'
            },
            'salary': {
                'must_transform': True,
                'methods': ['gaussian_noise', 'bucketing'],
                'max_noise_percentage': 10,
                'min_protection': 'high'
            },
            'phone': {
                'must_transform': True,
                'methods': ['masking', 'hashing'],
                'preserve_last_digits': 4,
                'min_protection': 'moderate'
            },
            'address': {
                'must_transform': True,
                'methods': ['generalization', 'suppression'],
                'generalize_to': 'city_level',
                'min_protection': 'moderate'
            },
            'password': {
                'must_transform': True,
                'methods': ['redaction'],
                'allow_view': False,
                'min_protection': 'critical'
            },
            'ip_address': {
                'must_transform': True,
                'methods': ['masking', 'hashing', 'generalization'],
                'preserve_subnet': False,
                'min_protection': 'moderate'
            }
        }
    
    @staticmethod
    def get_risk_based_rules(risk_score: int) -> Dict[str, Any]:
        """Get transformation rules based on risk score"""
        
        if risk_score >= 80:
            return {
                'min_epsilon': 0.5,
                'max_epsilon': 1.0,
                'min_k_anonymity': 10,
                'force_strict_mode': True,
                'allow_utility_loss': True,
                'description': 'Very high risk - maximum protection required'
            }
        
        elif risk_score >= 60:
            return {
                'min_epsilon': 1.0,
                'max_epsilon': 2.0,
                'min_k_anonymity': 7,
                'force_strict_mode': True,
                'allow_utility_loss': False,
                'description': 'High risk - strict protection required'
            }
        
        elif risk_score >= 40:
            return {
                'min_epsilon': 2.0,
                'max_epsilon': 3.0,
                'min_k_anonymity': 5,
                'force_strict_mode': False,
                'allow_utility_loss': False,
                'description': 'Moderate risk - standard protection'
            }
        
        else:
            return {
                'min_epsilon': 3.0,
                'max_epsilon': 5.0,
                'min_k_anonymity': 3,
                'force_strict_mode': False,
                'allow_utility_loss': False,
                'description': 'Low risk - basic protection sufficient'
            }
    
    @staticmethod
    def validate_policy_compliance(
        policy: PrivacyPolicy,
        risk_score: int
    ) -> Tuple[bool, List[str]]:
        """Validate if policy meets minimum requirements for risk level"""
        
        rules = TransformationRules.get_risk_based_rules(risk_score)
        issues = []
        
        # Check epsilon
        if policy.epsilon > rules['max_epsilon']:
            issues.append(
                f"Epsilon too high ({policy.epsilon} > {rules['max_epsilon']}) for risk level"
            )
        
        # Check k-anonymity
        if policy.k_anonymity < rules['min_k_anonymity']:
            issues.append(
                f"k-anonymity too low ({policy.k_anonymity} < {rules['min_k_anonymity']})"
            )
        
        # Check strict mode
        if rules['force_strict_mode'] and policy.level.value < PrivacyLevel.STRICT.value:
            issues.append(
                f"Strict mode required for this risk level"
            )
        
        is_compliant = len(issues) == 0
        
        return is_compliant, issues


# Export main components
__all__ = [
    'PrivacyLevel',
    'PrivacyPolicy',
    'PolicyLibrary',
    'TransformationRules'
]