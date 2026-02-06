from rest_framework.decorators import api_view
from rest_framework.response import Response
from .privacy_engine import PrivacyBudgetManager
from .dp_query_views import budget_manager
import csv
import json
from io import StringIO
from datetime import datetime



@api_view(["GET"])
def get_all_budgets(request):
    """
    Admin endpoint: View all user budgets
    
    Returns overview of all active users and their privacy budgets
    """
    from .models import PrivacyBudgetLedger

    all_budgets = []
    
    # Query all ledgers from database
    ledgers = PrivacyBudgetLedger.objects.all()
    
    for ledger in ledgers:
        budget_percentage = (ledger.epsilon_remaining / ledger.max_epsilon) * 100
        
        # Determine status
        if budget_percentage > 50:
            status = "HIGH"
        elif budget_percentage > 25:
            status = "MEDIUM"
        elif budget_percentage > 10:
            status = "LOW"
        else:
            status = "CRITICAL"
        
        # Get transaction count
        transaction_count = ledger.transactions.count()
        
        # Get last transaction
        last_transaction = ledger.transactions.order_by('-timestamp').first()
        
        all_budgets.append({
            "user_id": ledger.user_id,
            "epsilon_remaining": round(ledger.epsilon_remaining, 6),
            "epsilon_total": ledger.max_epsilon,
            "budget_percentage": round(budget_percentage, 2),
            "status": status,
            "total_queries": transaction_count,
            "last_query": last_transaction.timestamp.isoformat() if last_transaction else None,
            "last_refill": ledger.last_refill.isoformat()
        })
    
    return Response({
        "total_users": len(all_budgets),
        "budgets": sorted(all_budgets, key=lambda x: x['budget_percentage'])
    })


@api_view(["POST"])
def set_custom_budget(request, user_id):
    """
    Admin endpoint: Set custom epsilon budget for a user
    
    Body: {"epsilon": 20.0}
    """
    new_epsilon = request.data.get("epsilon")
    
    if not new_epsilon or new_epsilon <= 0:
        return Response({
            "error": "Invalid epsilon value. Must be positive number."
        }, status=400)
    
    ledger = budget_manager.get_or_create_ledger(user_id)
    ledger.reset_budget(new_epsilon)
    
    return Response({
        "message": "Budget updated successfully",
        "user_id": user_id,
        "new_epsilon": new_epsilon,
        "epsilon_remaining": ledger.epsilon_remaining
    })


@api_view(["GET"])
def get_system_stats(request):
    """
    Admin endpoint: Get overall system statistics
    """
    from .models import PrivacyBudgetLedger, PrivacyBudgetTransaction
    
    ledgers = PrivacyBudgetLedger.objects.all()
    total_users = ledgers.count()
    total_queries = PrivacyBudgetTransaction.objects.count()
    
    # Calculate average budget usage
    if total_users > 0:
        avg_budget_used = sum(
            (ledger.max_epsilon - ledger.epsilon_remaining) / ledger.max_epsilon * 100
            for ledger in ledgers
        ) / total_users
    else:
        avg_budget_used = 0
    
    # Query type breakdown
    query_type_counts = {}
    for transaction in PrivacyBudgetTransaction.objects.all():
        query_type = transaction.query_type
        query_type_counts[query_type] = query_type_counts.get(query_type, 0) + 1
    
    # Users by status
    status_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "CRITICAL": 0}
    for ledger in ledgers:
        budget_percentage = (ledger.epsilon_remaining / ledger.max_epsilon) * 100
        if budget_percentage > 50:
            status_counts["HIGH"] += 1
        elif budget_percentage > 25:
            status_counts["MEDIUM"] += 1
        elif budget_percentage > 10:
            status_counts["LOW"] += 1
        else:
            status_counts["CRITICAL"] += 1
    
    return Response({
        "system_overview": {
            "total_users": total_users,
            "total_queries": total_queries,
            "average_budget_used_percent": round(avg_budget_used, 2)
        },
        "query_breakdown": query_type_counts,
        "user_status_distribution": status_counts
    })


@api_view(["POST"])
def export_audit_log(request):
    """
    Admin endpoint: Export audit logs for compliance (GDPR/DPDP Act)
    
    Body: {
        "user_id": "analyst_001",  // Optional, if not provided exports all
        "format": "json"  // or "csv"
    }
    """
    user_id = request.data.get("user_id")
    export_format = request.data.get("format", "json")
    
    # Collect audit logs
    from .models import PrivacyBudgetTransaction
    audit_data = []
    
    if user_id:
        # Single user
        transactions = PrivacyBudgetTransaction.objects.filter(ledger__user_id=user_id).order_by('-timestamp')
        for txn in transactions:
            audit_data.append({
                'timestamp': txn.timestamp.isoformat(),
                'query_type': txn.query_type,
                'epsilon_used': txn.epsilon_used,
                'result': txn.result,
                'user_id': user_id
            })
    else:
        # All users
        transactions = PrivacyBudgetTransaction.objects.all().order_by('-timestamp')
        for txn in transactions:
            audit_data.append({
                'timestamp': txn.timestamp.isoformat(),
                'query_type': txn.query_type,
                'epsilon_used': txn.epsilon_used,
                'result': txn.result,
                'user_id': txn.ledger.user_id
            })
    
    if export_format == "csv":
        # Generate CSV
        output = StringIO()
        if audit_data:
            fieldnames = audit_data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(audit_data)
        
        return Response({
            "format": "csv",
            "data": output.getvalue(),
            "total_records": len(audit_data),
            "exported_at": datetime.now().isoformat()
        })
    else:
        # JSON format
        return Response({
            "format": "json",
            "data": audit_data,
            "total_records": len(audit_data),
            "exported_at": datetime.now().isoformat()
        })


@api_view(["POST"])
def reset_all_budgets(request):
    """
    Admin endpoint: Reset all user budgets (use with caution!)
    
    Body: {"confirm": true, "epsilon": 10.0}
    """
    confirm = request.data.get("confirm", False)
    new_epsilon = request.data.get("epsilon", 10.0)
    
    if not confirm:
        return Response({
            "error": "Confirmation required. Set 'confirm': true"
        }, status=400)
    
    from .models import PrivacyBudgetLedger
    
    ledgers = PrivacyBudgetLedger.objects.all()
    reset_count = ledgers.count()
    
    for ledger in ledgers:
        ledger.epsilon_remaining = new_epsilon
        ledger.max_epsilon = new_epsilon
        ledger.save()
    
    return Response({
        "message": f"Reset {reset_count} user budgets",
        "new_epsilon": new_epsilon,
        "timestamp": datetime.now().isoformat()
    })
