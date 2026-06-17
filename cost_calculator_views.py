from rest_framework.decorators import api_view
from rest_framework.response import Response
from .privacy_engine import QueryType, QUERY_EPSILON_COST

@api_view(["POST"])
def calculate_query_cost(request):
    """
    Calculate privacy cost before executing a query
    
    Helps users understand the epsilon cost and plan their queries
    
    Body:
    {
        "query_type": "mean",
        "dataset_size": 1000,
        "bounds": [0, 100]
    }
    """
    query_type_str = request.data.get("query_type", "").lower()
    dataset_size = request.data.get("dataset_size", 0)
    bounds = request.data.get("bounds", [0, 100])
    
    try:
        query_type = QueryType(query_type_str)
    except ValueError:
        return Response({
            "error": "Invalid query type",
            "valid_types": ["count", "mean", "sum", "variance", "std"]
        }, status=400)
    
    epsilon_cost = QUERY_EPSILON_COST[query_type]
    
    # Calculate sensitivity based on query type and bounds
    if query_type == QueryType.COUNT:
        sensitivity = 1.0
        explanation = "COUNT queries have low cost (ε=0.01) because they only reveal the number of records, not individual values."
    elif query_type == QueryType.MEAN:
        sensitivity = (bounds[1] - bounds[0]) / max(dataset_size, 1)
        explanation = "MEAN queries have medium cost (ε=0.05) because they reveal the central tendency of data."
    elif query_type == QueryType.SUM:
        sensitivity = (bounds[1] - bounds[0]) * dataset_size
        explanation = "SUM queries have high cost (ε=0.1) because they can reveal more information about individual contributions."
    elif query_type in [QueryType.VARIANCE, QueryType.STD]:
        sensitivity = (bounds[1] - bounds[0]) ** 2
        explanation = f"{query_type.value.upper()} queries have high cost (ε=0.1) because they reveal data spread and distribution."
    else:
        sensitivity = 1.0
        explanation = "Standard query cost applies."
    
    # Calculate how many queries possible with standard budget
    standard_budget = 10.0
    queries_possible = int(standard_budget / epsilon_cost)
    
    return Response({
        "query_type": query_type.value,
        "epsilon_cost": epsilon_cost,
        "sensitivity": round(sensitivity, 4),
        "recommended_epsilon": epsilon_cost,
        "cost_explanation": explanation,
        "queries_possible_with_standard_budget": queries_possible,
        "budget_impact": {
            "10_queries": round(10 * epsilon_cost, 2),
            "50_queries": round(50 * epsilon_cost, 2),
            "100_queries": round(100 * epsilon_cost, 2)
        },
        "comparison": {
            "COUNT_cost": QUERY_EPSILON_COST[QueryType.COUNT],
            "MEAN_cost": QUERY_EPSILON_COST[QueryType.MEAN],
            "SUM_cost": QUERY_EPSILON_COST[QueryType.SUM]
        }
    })
