from rest_framework.decorators import api_view
from rest_framework.response import Response
from .privacy_engine import PrivacyEngine, QueryType
from .db_budget_manager import DatabaseBudgetWrapper, DatabasePrivacyBudgetManager

# Use wrapper for PrivacyEngine (provides compatible interface)
budget_manager_wrapper = DatabaseBudgetWrapper()

# Use direct manager for admin endpoints (works with Django models)
budget_manager = DatabasePrivacyBudgetManager()

@api_view(["POST"])
def execute_dp_query(request):
    """
    Execute differential privacy query on database with deterministic noise.
    
    This is an alias for /api/privacy/db-query/ for backward compatibility.
    NO DATA ARRAY REQUIRED - queries database directly.
    
    Example:
    {
      "user_id": "analyst_001",
      "table_name": "dataset_records",
      "field_name": "Age",
      "query_type": "mean",
      "filters": {"Gender": "Female"}
    }
    """
    # Simply delegate to db_query_views by importing the core processing logic
    # We import the internal processing function, not the view decorator
    from .db_query_views import execute_db_query
    
    # Call the view function directly - it will handle the REST framework request properly
    # Since both are @api_view decorated, they work with the same request type
    return execute_db_query(request)



@api_view(["GET"])
def get_budget_status(request, user_id):
    """Get current budget status for a user"""
    ledger = budget_manager.get_or_create_ledger(user_id)
    degradation_factor = budget_manager.get_degradation_factor(ledger)
    
    return Response({
        "user_id": user_id,
        "epsilon_remaining": round(ledger.epsilon_remaining, 6),
        "epsilon_total": ledger.max_epsilon,
        "budget_percentage": round((ledger.epsilon_remaining / ledger.max_epsilon) * 100, 2),
        "degradation_factor": degradation_factor,
        "total_queries": ledger.transactions.count(),
        "last_refill": ledger.last_refill.isoformat()
    })


@api_view(["GET"])
def get_audit_log(request, user_id):
    """Get audit log for a user (GDPR/DPDP compliant)"""
    ledger = budget_manager.get_or_create_ledger(user_id)
    audit_log = budget_manager.get_audit_log(ledger)
    
    return Response({
        "user_id": user_id,
        "audit_log": audit_log,
        "total_transactions": ledger.transactions.count()
    })


@api_view(["POST"])
def reset_budget(request, user_id):
    """Admin endpoint to reset user budget"""
    new_epsilon = request.data.get("epsilon", None)
    
    ledger = budget_manager.get_or_create_ledger(user_id)
    budget_manager.reset_budget(ledger, new_epsilon)
    ledger.refresh_from_db()  # Refresh to get updated values
    
    return Response({
        "message": "Budget reset successful",
        "user_id": user_id,
        "new_epsilon": ledger.epsilon_remaining
    })
