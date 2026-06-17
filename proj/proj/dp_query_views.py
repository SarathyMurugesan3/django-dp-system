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
    Execute differential privacy query with budget enforcement
    
    Supports two modes:
    
    1. Direct Data Mode (backward compatible):
    {
      "user_id": "analyst_001",
      "query_type": "mean",
      "data": [25, 30, 35, 40, 45],
      "lower_bound": 0,
      "upper_bound": 100,
      "field_name": "age"
    }
    
    2. Database Query Mode (new):
    {
      "user_id": "analyst_001",
      "table_name": "demographics",
      "field_name": "age",
      "query_type": "mean",
      "filters": {
        "age": {"operator": ">", "value": 18}
      }
    }
    """
    user_id = request.data.get("user_id", "default")
    query_type_str = request.data.get("query_type", "count")
    
    # Check if this is a database query or direct data query
    table_name = request.data.get("table_name")
    
    if table_name:
        # Database query mode - use shared logic
        from .db_query_views import process_db_query
        
        # Extract fields
        field_name = request.data.get("field_name")
        filters = request.data.get("filters", {})
        
        response_data, status_code = process_db_query(user_id, table_name, field_name, query_type_str, filters)
        return Response(response_data, status=status_code)
    
    # Direct data mode (original behavior)
    data = request.data.get("data", [])
    lower_bound = request.data.get("lower_bound", 0)
    upper_bound = request.data.get("upper_bound", 1000)
    field_name = request.data.get("field_name", "value")
    
    try:
        query_type = QueryType(query_type_str.lower())
    except ValueError:
        return Response({
            "error": "Invalid query type",
            "valid_types": ["count", "mean", "sum", "variance", "std"]
        }, status=400)
    
    if not data:
        return Response({
            "error": "data array required for direct data mode",
            "hint": "Either provide 'data' array OR provide 'table_name' + 'field_name' for database queries"
        }, status=400)
    
    # Use wrapper for PrivacyEngine compatibility
    engine = PrivacyEngine(budget_manager=budget_manager_wrapper)
    
    result, metadata = engine.execute_dp_query(
        data=data,
        query_type=query_type,
        user_id=user_id,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        field_name=field_name
    )
    
    if result is None:
        return Response(metadata, status=429)
    
    return Response({
        "result": result,
        "metadata": metadata
    })



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
