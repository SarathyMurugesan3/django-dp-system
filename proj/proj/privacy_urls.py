"""
URL Configuration for Privacy-Enhanced API
"""
from django.urls import path
from .privacy_views import (
    assess_and_privatize,
    privatize_only,
    classify_columns,
    list_policies,
    validate_policy,
    compare_policies
)
from .dp_query_views import (
    get_budget_status,
    get_audit_log,
    reset_budget
)
from .admin_views import (
    get_all_budgets,
    set_custom_budget,
    get_system_stats,
    export_audit_log,
    reset_all_budgets
)
from .cost_calculator_views import calculate_query_cost
from .db_query_views import execute_db_query, get_query_history
from .team_views import create_team, join_team, get_team_members, leave_team
from .privatized_table_views import get_privatized_table

urlpatterns = [
    path('assess-and-privatize/', assess_and_privatize),
    path('privatize/', privatize_only),
    path('classify/', classify_columns),
    path('policies/', list_policies),
    path('policies/validate/', validate_policy),
    path('policies/compare/', compare_policies),
    
    # ShadowSafe-Style Budget System Endpoints
    # NOTE: dp-query is an alias for db-query (both use same view function)
    path('dp-query/', execute_db_query),  # Alias for backward compatibility
    path('budget-status/<str:user_id>/', get_budget_status),
    path('audit-log/<str:user_id>/', get_audit_log),
    path('reset-budget/<str:user_id>/', reset_budget),
    
    # NEW: Database Query Endpoints with Fingerprinting
    path('db-query/', execute_db_query),
    path('query-history/<str:user_id>/', get_query_history),
    
    # NEW: Privatized Table Data
    path('privatized-table/', get_privatized_table),
    
    # NEW: Team Management Endpoints
    path('teams/create/', create_team),
    path('teams/join/', join_team),
    path('teams/<str:team_id>/members/', get_team_members),
    path('teams/leave/', leave_team),
    
    # Cost Calculator
    path('calculate-cost/', calculate_query_cost),
    
    # Admin Dashboard Endpoints
    path('admin/budgets/', get_all_budgets),
    path('admin/set-budget/<str:user_id>/', set_custom_budget),
    path('admin/stats/', get_system_stats),
    path('admin/export-audit/', export_audit_log),
    path('admin/reset-all/', reset_all_budgets),
]


