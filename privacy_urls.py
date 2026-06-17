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
    compare_policies,
    trigger_guardian_from_hacker,
    anonymization_proof
)
from .dp_query_views import (
    execute_dp_query,
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
from .auth_views import (
    admin_login,
    admin_create_user,
    admin_create_team,
    admin_list_users,
    admin_delete_user,
    admin_verify_token,
)
from .cost_calculator_views import calculate_query_cost
from .db_query_views import execute_db_query, get_query_history, list_tables
from .team_views import create_team, join_team, get_team_members, leave_team
from .privatized_table_views import get_privatized_table

urlpatterns = [
    path('anonymization-proof/', anonymization_proof),
    path('assess-and-privatize/', assess_and_privatize),
    path('privatize/', privatize_only),
    path('classify/', classify_columns),
    path('policies/', list_policies),
    path('policies/validate/', validate_policy),
    path('policies/compare/', compare_policies),
    path('trigger-guardian/', trigger_guardian_from_hacker),

    # ShadowSafe-Style Budget System Endpoints
    path('dp-query/', execute_dp_query),
    path('budget-status/<str:user_id>/', get_budget_status),
    path('audit-log/<str:user_id>/', get_audit_log),
    path('reset-budget/<str:user_id>/', reset_budget),

    # Database Query Endpoints with Fingerprinting
    path('db-query/', execute_db_query),
    path('query-history/<str:user_id>/', get_query_history),
    path('tables/', list_tables),

    # Privatized Table Data
    path('privatized-table/', get_privatized_table),

    # Team Management Endpoints (public)
    path('teams/join/', join_team),
    path('teams/<str:team_id>/members/', get_team_members),
    path('teams/leave/', leave_team),

    # Cost Calculator
    path('calculate-cost/', calculate_query_cost),

    # Admin Endpoints (no auth — budget/stats)
    path('admin/all-budgets/', get_all_budgets),
    path('admin/budgets/', get_all_budgets),
    path('admin/set-budget/<str:user_id>/', set_custom_budget),
    path('admin/system-stats/', get_system_stats),
    path('admin/stats/', get_system_stats),
    path('admin/export-audit-log/', export_audit_log),
    path('admin/reset-all-budgets/', reset_all_budgets),

    # JWT-Protected Admin Endpoints
    path('admin/login/',        admin_login),         # POST  - get JWT token (no auth needed)
    path('admin/verify-token/', admin_verify_token),  # GET   - check token valid [JWT]
    path('admin/create-user/',  admin_create_user),   # POST  - create user     [JWT]
    path('admin/create-team/',  admin_create_team),   # POST  - create team     [JWT]
    path('admin/users/',        admin_list_users),    # GET   - list all users  [JWT]
    path('admin/delete-user/',  admin_delete_user),   # DELETE - remove user   [JWT]
]
