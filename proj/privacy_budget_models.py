from django.db import models
from django.utils import timezone
import json

class PrivacyBudgetLedger(models.Model):
    """
    Database-backed privacy budget ledger for production use
    
    Persists across server restarts and supports multiple instances
    """
    user_id = models.CharField(max_length=255, unique=True, db_index=True)
    team_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)  # NEW
    max_epsilon = models.FloatField(default=10.0)
    epsilon_remaining = models.FloatField(default=10.0)
    last_refill = models.DateTimeField(default=timezone.now)
    global_seed = models.BinaryField(max_length=32)  # For deterministic randomness
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'privacy_budget_ledgers'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"{self.user_id} - {self.epsilon_remaining}/{self.max_epsilon} ε"


class PrivacyBudgetTransaction(models.Model):
    """
    Individual privacy budget transaction record
    
    Audit trail for GDPR/DPDP compliance
    """
    ledger = models.ForeignKey(
        PrivacyBudgetLedger,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    query_id = models.CharField(max_length=64, unique=True, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    query_type = models.CharField(max_length=50)  # count, mean, sum, etc.
    epsilon_cost = models.FloatField()
    epsilon_remaining = models.FloatField()
    mechanism_used = models.CharField(max_length=100)  # LaplaceBoundedDomain, etc.
    
    # Mathematical details for transparency
    sensitivity = models.FloatField(default=0.0)
    noise_scale = models.FloatField(default=0.0)
    degradation_factor = models.FloatField(default=1.0)
    bounds_lower = models.FloatField(default=0.0)
    bounds_upper = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'privacy_budget_transactions'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ledger', '-timestamp']),
            models.Index(fields=['query_id']),
            models.Index(fields=['timestamp']),
        ]
    
    def to_dict(self):
        """Convert to audit-safe dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'query_type': self.query_type,
            'epsilon_cost': round(self.epsilon_cost, 6),
            'epsilon_remaining': round(self.epsilon_remaining, 6),
            'mechanism': self.mechanism_used,
            'query_id': self.query_id,
            'mathematical_output': {
                'sensitivity': round(self.sensitivity, 4),
                'noise_scale': round(self.noise_scale, 4),
                'noise_distribution': f"Laplace(μ=0, b={round(self.noise_scale, 2)})",
                'privacy_formula': f"(ε, δ)-DP where ε={round(self.epsilon_cost, 4)}, δ=1e-05",
                'true_result_bounds': f"[{self.bounds_lower}, {self.bounds_upper}]",
                'degradation_applied': f"{self.degradation_factor}x",
                'effective_epsilon': round(self.epsilon_cost * self.degradation_factor, 6)
            }
        }
    
    def __str__(self):
        return f"{self.query_type} - ε={self.epsilon_cost} - {self.timestamp}"


class PrivacyBudgetRefill(models.Model):
    """
    Track budget refills for audit purposes
    """
    ledger = models.ForeignKey(
        PrivacyBudgetLedger,
        on_delete=models.CASCADE,
        related_name='refills'
    )
    timestamp = models.DateTimeField(default=timezone.now)
    refill_amount = models.FloatField()
    epsilon_before = models.FloatField()
    epsilon_after = models.FloatField()
    refill_type = models.CharField(
        max_length=50,
        choices=[
            ('AUTOMATIC', 'Automatic (Sliding Window)'),
            ('ADMIN', 'Admin Manual Reset'),
            ('SCHEDULED', 'Scheduled Refill')
        ]
    )
    
    class Meta:
        db_table = 'privacy_budget_refills'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.ledger.user_id} - +{self.refill_amount}ε - {self.refill_type}"
