"""
Django models for storing query fingerprints
"""

from django.db import models
from django.utils import timezone


class QueryFingerprintModel(models.Model):
    """
    Store query fingerprints for similarity detection
    """
    user_id = models.CharField(max_length=255, db_index=True)
    table_name = models.CharField(max_length=255)
    field_name = models.CharField(max_length=255)
    query_type = models.CharField(max_length=50)  # mean, sum, count, etc.
    
    # Fingerprint data
    fingerprint_hash = models.CharField(max_length=64, db_index=True)
    filters_json = models.JSONField()
    
    # Budget tracking
    epsilon_cost = models.FloatField()
    budget_multiplier = models.FloatField(default=1.0)
    effective_cost = models.FloatField()  # epsilon_cost * budget_multiplier
    
    # Metadata
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    result_value = models.FloatField(null=True, blank=True)  # Store DP result
    
    class Meta:
        db_table = 'query_fingerprints'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user_id', '-timestamp']),
            models.Index(fields=['fingerprint_hash']),
            models.Index(fields=['table_name', 'field_name']),
        ]
    
    def __str__(self):
        return f"{self.user_id} - {self.query_type}({self.field_name}) - {self.timestamp}"
