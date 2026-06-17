"""
Team Management Models for Privacy Budget System

Supports:
- Team creation and management
- Team membership tracking
- Individual vs team-based privacy budgeting
"""

from django.db import models
from django.utils import timezone


class Team(models.Model):
    """Team model for grouping users"""
    team_id = models.CharField(max_length=255, unique=True, primary_key=True, db_index=True)
    team_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    max_members = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)
    
    # Team-level privacy budget (optional - can share budget)
    shared_budget = models.BooleanField(default=False)
    team_epsilon = models.FloatField(default=10.0, null=True, blank=True)
    
    class Meta:
        db_table = 'teams'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.team_name} ({self.team_id})"
    
    def member_count(self):
        """Get current number of members"""
        return self.teammembership_set.count()
    
    def is_full(self):
        """Check if team has reached max capacity"""
        return self.member_count() >= self.max_members


class TeamMembership(models.Model):
    """Team membership tracking"""
    user_id = models.CharField(max_length=255, unique=True, db_index=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    role = models.CharField(
        max_length=50,
        default='member',
        choices=[
            ('admin', 'Admin'),
            ('member', 'Member'),
            ('viewer', 'Viewer')
        ]
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'team_memberships'
        ordering = ['-joined_at']
        indexes = [
            models.Index(fields=['user_id', 'team']),
        ]
    
    def __str__(self):
        return f"{self.user_id} in {self.team.team_name}"
