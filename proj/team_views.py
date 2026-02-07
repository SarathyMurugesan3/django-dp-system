"""
Team Management API Views

Endpoints for creating teams, managing memberships, and team-based privacy budgeting
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from .team_models import Team, TeamMembership
from .privacy_budget_models import PrivacyBudgetLedger


@api_view(['POST'])
def create_team(request):
    """
    Create a new team
    
    POST /api/teams/create/
    {
        "team_id": "data_team_01",
        "team_name": "Data Analysis Team",
        "description": "Team for analyzing customer data",
        "max_members": 10,
        "shared_budget": false
    }
    """
    team_id = request.data.get('team_id')
    team_name = request.data.get('team_name')
    description = request.data.get('description', '')
    max_members = request.data.get('max_members', 10)
    shared_budget = request.data.get('shared_budget', False)
    
    if not team_id or not team_name:
        return Response({
            'error': 'team_id and team_name are required'
        }, status=400)
    
    # Check if team already exists
    if Team.objects.filter(team_id=team_id).exists():
        return Response({
            'error': 'Team with this ID already exists'
        }, status=400)
    
    # Create team
    team = Team.objects.create(
        team_id=team_id,
        team_name=team_name,
        description=description,
        max_members=max_members,
        shared_budget=shared_budget
    )
    
    return Response({
        'team_id': team.team_id,
        'team_name': team.team_name,
        'description': team.description,
        'max_members': team.max_members,
        'shared_budget': team.shared_budget,
        'created_at': team.created_at.isoformat(),
        'member_count': 0
    }, status=201)


@api_view(['POST'])
def join_team(request):
    """
    Join a team
    
    POST /api/teams/join/
    {
        "user_id": "analyst_001",
        "team_id": "data_team_01",
        "role": "member"
    }
    """
    user_id = request.data.get('user_id')
    team_id = request.data.get('team_id')
    role = request.data.get('role', 'member')
    
    if not user_id or not team_id:
        return Response({
            'error': 'user_id and team_id are required'
        }, status=400)
    
    # Check if team exists
    try:
        team = Team.objects.get(team_id=team_id)
    except Team.DoesNotExist:
        return Response({
            'error': 'Team not found'
        }, status=404)
    
    # Check if team is full
    if team.is_full():
        return Response({
            'error': f'Team is full (max {team.max_members} members)'
        }, status=400)
    
    # Check if user already in a team
    if TeamMembership.objects.filter(user_id=user_id).exists():
        existing = TeamMembership.objects.get(user_id=user_id)
        return Response({
            'error': f'User already in team {existing.team.team_id}'
        }, status=400)
    
    # Create membership
    membership = TeamMembership.objects.create(
        user_id=user_id,
        team=team,
        role=role
    )
    
    # Update user's ledger with team_id
    try:
        ledger = PrivacyBudgetLedger.objects.get(user_id=user_id)
        ledger.team_id = team_id
        ledger.save()
    except PrivacyBudgetLedger.DoesNotExist:
        pass  # Ledger will be created on first query
    
    return Response({
        'user_id': membership.user_id,
        'team_id': team.team_id,
        'team_name': team.team_name,
        'role': membership.role,
        'joined_at': membership.joined_at.isoformat(),
        'team_member_count': team.member_count()
    }, status=201)


@api_view(['GET'])
def get_team_members(request, team_id):
    """
    Get all members of a team
    
    GET /api/teams/<team_id>/members/
    """
    try:
        team = Team.objects.get(team_id=team_id)
    except Team.DoesNotExist:
        return Response({
            'error': 'Team not found'
        }, status=404)
    
    memberships = TeamMembership.objects.filter(team=team, is_active=True)
    
    members = []
    for m in memberships:
        # Get budget info if available
        try:
            ledger = PrivacyBudgetLedger.objects.get(user_id=m.user_id)
            epsilon_remaining = ledger.epsilon_remaining
        except PrivacyBudgetLedger.DoesNotExist:
            epsilon_remaining = None
        
        members.append({
            'user_id': m.user_id,
            'role': m.role,
            'joined_at': m.joined_at.isoformat(),
            'epsilon_remaining': epsilon_remaining
        })
    
    return Response({
        'team_id': team.team_id,
        'team_name': team.team_name,
        'member_count': len(members),
        'max_members': team.max_members,
        'shared_budget': team.shared_budget,
        'members': members
    })


@api_view(['POST'])
def leave_team(request):
    """
    Leave a team
    
    POST /api/teams/leave/
    {
        "user_id": "analyst_001"
    }
    """
    user_id = request.data.get('user_id')
    
    if not user_id:
        return Response({
            'error': 'user_id is required'
        }, status=400)
    
    try:
        membership = TeamMembership.objects.get(user_id=user_id, is_active=True)
    except TeamMembership.DoesNotExist:
        return Response({
            'error': 'User is not in any team'
        }, status=404)
    
    team_id = membership.team.team_id
    
    # Deactivate membership
    membership.is_active = False
    membership.save()
    
    # Remove team_id from ledger
    try:
        ledger = PrivacyBudgetLedger.objects.get(user_id=user_id)
        ledger.team_id = None
        ledger.save()
    except PrivacyBudgetLedger.DoesNotExist:
        pass
    
    return Response({
        'message': f'Successfully left team {team_id}',
        'user_id': user_id,
        'team_id': team_id
    })
