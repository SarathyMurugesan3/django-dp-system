"""
JWT Admin Authentication System
================================
Super Admin login → JWT token → protected admin routes

ENDPOINTS:
  POST /api/privacy/admin/login/          ← get JWT token (no auth needed)
  POST /api/privacy/admin/create-user/   ← JWT required
  POST /api/privacy/admin/create-team/   ← JWT required
  DELETE /api/privacy/admin/delete-user/ ← JWT required

ENVIRONMENT VARIABLES (set in Render dashboard):
  ADMIN_USERNAME   e.g. "superadmin"
  ADMIN_PASSWORD   e.g. "StrongPassword123!"
  JWT_SECRET_KEY   e.g. "your-random-secret-string"
  JWT_EXPIRY_HOURS e.g. "24"
"""

import jwt
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .privacy_budget_models import PrivacyBudgetLedger
from .team_models import Team, TeamMembership

# ─────────────────────────────────────────────────────
# Config — read from environment variables
# ─────────────────────────────────────────────────────
ADMIN_USERNAME  = os.environ.get("ADMIN_USERNAME",  "superadmin")
ADMIN_PASSWORD  = os.environ.get("ADMIN_PASSWORD",  "ChangeMe@123!")
JWT_SECRET_KEY  = os.environ.get("JWT_SECRET_KEY",  "shadowsafe-default-secret-change-me")
JWT_EXPIRY_HRS  = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
JWT_ALGORITHM   = "HS256"


# ─────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────
def _generate_token(username: str) -> str:
    """Generate a signed JWT token for the admin user."""
    payload = {
        "sub":   username,
        "role":  "superadmin",
        "iat":   datetime.now(tz=timezone.utc),
        "exp":   datetime.now(tz=timezone.utc) + timedelta(hours=JWT_EXPIRY_HRS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _verify_token(token: str) -> dict | None:
    """Verify and decode a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("role") != "superadmin":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def admin_jwt_required(view_func):
    """
    Decorator: protects a view — requires valid superadmin JWT.

    Usage:
        @api_view(["POST"])
        @admin_jwt_required
        def my_protected_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response({
                "error":   "Unauthorized",
                "message": "Missing or invalid Authorization header. Use: Bearer <token>"
            }, status=401)

        token = auth_header.split(" ", 1)[1]
        payload = _verify_token(token)

        if payload is None:
            return Response({
                "error":   "Unauthorized",
                "message": "Invalid or expired JWT token. Please login again."
            }, status=401)

        # Attach admin info to request for use in the view
        request.admin_user = payload.get("sub")
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────
# ENDPOINT 1: Admin Login — POST /api/privacy/admin/login/
# ─────────────────────────────────────────────────────
@api_view(["POST"])
def admin_login(request):
    """
    Super Admin Login

    Body:
    {
        "username": "superadmin",
        "password": "ChangeMe@123!"
    }

    Returns:
    {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in_hours": 24,
        "token_type": "Bearer"
    }
    """
    username = request.data.get("username", "")
    password = request.data.get("password", "")

    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return Response({
            "error":   "Invalid credentials",
            "message": "Username or password is incorrect."
        }, status=401)

    token = _generate_token(username)

    return Response({
        "token":           token,
        "token_type":      "Bearer",
        "expires_in_hours": JWT_EXPIRY_HRS,
        "usage":           "Add to request header → Authorization: Bearer <token>",
        "admin":           username,
        "logged_in_at":    datetime.now(tz=timezone.utc).isoformat()
    }, status=200)


# ─────────────────────────────────────────────────────
# ENDPOINT 2: Create User — POST /api/privacy/admin/create-user/
# ─────────────────────────────────────────────────────
@api_view(["POST"])
@admin_jwt_required
def admin_create_user(request):
    """
    [PROTECTED] Create a new user with a privacy budget.
    Requires: Authorization: Bearer <token>

    Body:
    {
        "user_id":  "analyst_001",
        "epsilon":  10.0,       (optional, default 10.0)
        "team_id":  "team_01"   (optional)
    }
    """
    user_id = request.data.get("user_id", "").strip()
    epsilon  = float(request.data.get("epsilon", 10.0))
    team_id  = request.data.get("team_id", None)

    if not user_id:
        return Response({
            "error": "user_id is required"
        }, status=400)

    if epsilon <= 0:
        return Response({
            "error": "epsilon must be a positive number"
        }, status=400)

    # Check if user already exists
    if PrivacyBudgetLedger.objects.filter(user_id=user_id).exists():
        return Response({
            "error":   "User already exists",
            "user_id": user_id,
            "message": "Use PATCH /admin/set-budget/<user_id>/ to update their budget."
        }, status=409)

    # Validate team if provided
    if team_id:
        if not Team.objects.filter(team_id=team_id).exists():
            return Response({
                "error":   "Team not found",
                "team_id": team_id
            }, status=404)

    # Create user ledger
    import secrets
    from django.utils import timezone as dj_timezone
    ledger = PrivacyBudgetLedger.objects.create(
        user_id=user_id,
        max_epsilon=epsilon,
        epsilon_remaining=epsilon,
        global_seed=secrets.token_bytes(32),
        last_refill=dj_timezone.now(),
        team_id=team_id
    )

    # Add to team if specified
    if team_id:
        team = Team.objects.get(team_id=team_id)
        TeamMembership.objects.get_or_create(
            user_id=user_id,
            defaults={"team": team, "role": "member"}
        )

    return Response({
        "message":           "User created successfully",
        "user_id":           ledger.user_id,
        "epsilon_budget":    ledger.max_epsilon,
        "epsilon_remaining": ledger.epsilon_remaining,
        "team_id":           ledger.team_id,
        "created_at":        ledger.created_at.isoformat(),
        "created_by":        request.admin_user
    }, status=201)


# ─────────────────────────────────────────────────────
# ENDPOINT 3: Create Team — POST /api/privacy/admin/create-team/
# ─────────────────────────────────────────────────────
@api_view(["POST"])
@admin_jwt_required
def admin_create_team(request):
    """
    [PROTECTED] Create a new team.
    Requires: Authorization: Bearer <token>

    Body:
    {
        "team_id":     "data_team_01",
        "team_name":   "Data Analysis Team",
        "description": "Team for health data analysis",
        "max_members": 10,
        "shared_budget": false
    }
    """
    team_id      = request.data.get("team_id", "").strip()
    team_name    = request.data.get("team_name", "").strip()
    description  = request.data.get("description", "")
    max_members  = int(request.data.get("max_members", 10))
    shared_budget = request.data.get("shared_budget", False)

    if not team_id or not team_name:
        return Response({
            "error": "team_id and team_name are required"
        }, status=400)

    if Team.objects.filter(team_id=team_id).exists():
        return Response({
            "error":   "Team already exists",
            "team_id": team_id
        }, status=409)

    team = Team.objects.create(
        team_id=team_id,
        team_name=team_name,
        description=description,
        max_members=max_members,
        shared_budget=shared_budget
    )

    return Response({
        "message":       "Team created successfully",
        "team_id":       team.team_id,
        "team_name":     team.team_name,
        "description":   team.description,
        "max_members":   team.max_members,
        "shared_budget": team.shared_budget,
        "created_at":    team.created_at.isoformat(),
        "created_by":    request.admin_user
    }, status=201)


# ─────────────────────────────────────────────────────
# ENDPOINT 4: List All Users — GET /api/privacy/admin/users/
# ─────────────────────────────────────────────────────
@api_view(["GET"])
@admin_jwt_required
def admin_list_users(request):
    """
    [PROTECTED] List all registered users and their budget status.
    Requires: Authorization: Bearer <token>
    """
    ledgers = PrivacyBudgetLedger.objects.all().order_by("-created_at")

    users = []
    for l in ledgers:
        pct = (l.epsilon_remaining / l.max_epsilon) * 100 if l.max_epsilon > 0 else 0
        users.append({
            "user_id":           l.user_id,
            "team_id":           l.team_id,
            "epsilon_remaining": round(l.epsilon_remaining, 4),
            "epsilon_total":     l.max_epsilon,
            "budget_percent":    round(pct, 1),
            "status":            "HIGH" if pct > 50 else "MEDIUM" if pct > 25 else "LOW" if pct > 10 else "CRITICAL",
            "created_at":        l.created_at.isoformat(),
        })

    return Response({
        "total_users": len(users),
        "users":       users
    }, status=200)


# ─────────────────────────────────────────────────────
# ENDPOINT 5: Delete User — DELETE /api/privacy/admin/delete-user/
# ─────────────────────────────────────────────────────
@api_view(["DELETE"])
@admin_jwt_required
def admin_delete_user(request):
    """
    [PROTECTED] Delete a user and their entire budget history.
    Requires: Authorization: Bearer <token>

    Body:
    {
        "user_id": "analyst_001"
    }
    """
    user_id = request.data.get("user_id", "").strip()

    if not user_id:
        return Response({"error": "user_id is required"}, status=400)

    try:
        ledger = PrivacyBudgetLedger.objects.get(user_id=user_id)
        ledger.delete()
        # Also remove team membership
        TeamMembership.objects.filter(user_id=user_id).delete()
        return Response({
            "message":    f"User '{user_id}' deleted successfully",
            "deleted_by": request.admin_user
        }, status=200)
    except PrivacyBudgetLedger.DoesNotExist:
        return Response({
            "error":   "User not found",
            "user_id": user_id
        }, status=404)


# ─────────────────────────────────────────────────────
# ENDPOINT 6: Verify Token — GET /api/privacy/admin/verify-token/
# ─────────────────────────────────────────────────────
@api_view(["GET"])
@admin_jwt_required
def admin_verify_token(request):
    """
    [PROTECTED] Check if your JWT token is still valid.
    Requires: Authorization: Bearer <token>
    """
    return Response({
        "valid":      True,
        "admin_user": request.admin_user,
        "message":    "Token is valid"
    }, status=200)
