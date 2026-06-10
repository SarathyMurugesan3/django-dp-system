"""
Database-backed Privacy Budget Manager for Production

This replaces the in-memory PrivacyBudgetManager with database persistence.
Supports:
- Multiple server instances (load balancing)
- Server restarts without data loss
- Complete audit trail
- GDPR/DPDP compliance
"""

from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import secrets
import hashlib
import time
from typing import Dict, Optional, Tuple
from .privacy_budget_models import (
    PrivacyBudgetLedger as LedgerModel,
    PrivacyBudgetTransaction as TransactionModel,
    PrivacyBudgetRefill as RefillModel
)


class DatabasePrivacyBudgetManager:
    """
    Production-ready privacy budget manager with database persistence
    """
    
    @staticmethod
    def get_or_create_ledger(user_id: str, max_epsilon: float = 10.0) -> LedgerModel:
        """
        Get existing ledger or create new one
        
        Thread-safe with database locking
        """
        ledger, created = LedgerModel.objects.get_or_create(
            user_id=user_id,
            defaults={
                'max_epsilon': max_epsilon,
                'epsilon_remaining': max_epsilon,
                'global_seed': secrets.token_bytes(32),
                'last_refill': timezone.now()
            }
        )
        
        if not created:
            # Auto-refill if time has passed
            DatabasePrivacyBudgetManager.refill_budget(ledger)
        
        return ledger
    
    @staticmethod
    def can_afford(ledger: LedgerModel, epsilon_cost: float) -> bool:
        """
        Check if user has enough budget
        
        Refreshes ledger from database to get latest value
        """
        ledger.refresh_from_db()  # Get latest from DB
        return ledger.epsilon_remaining >= epsilon_cost
    
    @staticmethod
    def get_degradation_factor(ledger: LedgerModel) -> float:
        """
        Calculate noise multiplier based on budget percentage
        """
        budget_pct = (ledger.epsilon_remaining / ledger.max_epsilon) * 100
        
        if budget_pct > 50:
            return 1.0   # Normal noise
        elif budget_pct > 25:
            return 2.0   # 2x noise
        elif budget_pct > 10:
            return 5.0   # 5x noise
        else:
            return 10.0  # 10x noise (critical)
    
    @staticmethod
    @transaction.atomic
    def deduct(
        ledger: LedgerModel,
        query_type: str,
        epsilon_cost: float,
        mechanism: str,
        sensitivity: float = 0.0,
        noise_scale: float = 0.0,
        degradation_factor: float = 1.0,
        bounds: Tuple[float, float] = (0, 0)
    ) -> str:
        """
        Deduct epsilon and record transaction
        
        Uses database transaction for atomicity
        Prevents race conditions with SELECT FOR UPDATE
        """
        # Lock the ledger row to prevent concurrent modifications
        ledger = LedgerModel.objects.select_for_update().get(pk=ledger.pk)
        
        # Deduct epsilon
        ledger.epsilon_remaining -= epsilon_cost
        ledger.save(update_fields=['epsilon_remaining', 'updated_at'])
        
        # Generate unique query ID
        query_id = hashlib.sha256(
            f"{ledger.user_id}{time.time()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        # Create transaction record
        transaction_record = TransactionModel.objects.create(
            ledger=ledger,
            query_id=query_id,
            query_type=query_type,
            epsilon_cost=epsilon_cost,
            epsilon_remaining=ledger.epsilon_remaining,
            mechanism_used=mechanism,
            sensitivity=sensitivity,
            noise_scale=noise_scale,
            degradation_factor=degradation_factor,
            bounds_lower=bounds[0],
            bounds_upper=bounds[1]
        )
        
        return query_id
    
    @staticmethod
    @transaction.atomic
    def spend_budget(user_id: str, epsilon_cost: float, query_type: str) -> Tuple[bool, str]:
        try:
            # Lock the row for this transaction — prevents race condition
            ledger = LedgerModel.objects.select_for_update().get(user_id=user_id)
        except LedgerModel.DoesNotExist:
            return False, "Ledger not found"

        if ledger.epsilon_remaining < epsilon_cost:
            return False, f"Insufficient budget. Remaining: {ledger.epsilon_remaining:.4f}"

        ledger.epsilon_remaining -= epsilon_cost
        ledger.save()

        TransactionModel.objects.create(
            ledger=ledger,
            epsilon_cost=epsilon_cost,
            query_type=query_type,
            epsilon_remaining=ledger.epsilon_remaining,
            mechanism_used='direct',
            query_id=secrets.token_hex(8)
        )

        return True, f"Spent ε={epsilon_cost}. Remaining: {ledger.epsilon_remaining:.4f}"

    @staticmethod
    @transaction.atomic
    def refill_budget(ledger: LedgerModel) -> Optional[float]:
        """
        Sliding window budget recovery
        
        Refills 10% per hour, up to max_epsilon
        """
        now = timezone.now()
        time_since_refill = now - ledger.last_refill
        hours_elapsed = time_since_refill.total_seconds() / 3600
        
        if hours_elapsed >= 1:
            # Lock ledger for update
            ledger = LedgerModel.objects.select_for_update().get(pk=ledger.pk)
            
            epsilon_before = ledger.epsilon_remaining
            refill_amount = min(
                ledger.max_epsilon * 0.1 * hours_elapsed,
                ledger.max_epsilon - ledger.epsilon_remaining
            )
            
            if refill_amount > 0:
                ledger.epsilon_remaining = min(
                    ledger.epsilon_remaining + refill_amount,
                    ledger.max_epsilon
                )
                ledger.last_refill = now
                ledger.save(update_fields=['epsilon_remaining', 'last_refill', 'updated_at'])
                
                # Record refill for audit
                RefillModel.objects.create(
                    ledger=ledger,
                    refill_amount=refill_amount,
                    epsilon_before=epsilon_before,
                    epsilon_after=ledger.epsilon_remaining,
                    refill_type='AUTOMATIC'
                )
                
                return refill_amount
        
        return None
    
    @staticmethod
    @transaction.atomic
    def reset_budget(ledger: LedgerModel, new_epsilon: Optional[float] = None) -> None:
        """
        Admin reset of budget
        """
        ledger = LedgerModel.objects.select_for_update().get(pk=ledger.pk)
        
        epsilon_before = ledger.epsilon_remaining
        
        if new_epsilon is not None:
            ledger.max_epsilon = new_epsilon
            ledger.epsilon_remaining = new_epsilon
        else:
            ledger.epsilon_remaining = ledger.max_epsilon
        
        ledger.last_refill = timezone.now()
        ledger.save()
        
        # Record admin reset
        RefillModel.objects.create(
            ledger=ledger,
            refill_amount=ledger.epsilon_remaining - epsilon_before,
            epsilon_before=epsilon_before,
            epsilon_after=ledger.epsilon_remaining,
            refill_type='ADMIN'
        )
    
    @staticmethod
    def get_audit_log(ledger: LedgerModel, limit: int = 100) -> list:
        """
        Get audit log for user
        """
        transactions = ledger.transactions.all()[:limit]
        return [t.to_dict() for t in transactions]
    
    @staticmethod
    def get_all_budgets() -> list:
        """
        Get all user budgets (admin endpoint)
        """
        ledgers = LedgerModel.objects.all().prefetch_related('transactions')
        
        result = []
        for ledger in ledgers:
            budget_pct = (ledger.epsilon_remaining / ledger.max_epsilon) * 100
            
            if budget_pct > 50:
                status = "HIGH"
            elif budget_pct > 25:
                status = "MEDIUM"
            elif budget_pct > 10:
                status = "LOW"
            else:
                status = "CRITICAL"
            
            last_transaction = ledger.transactions.first()
            
            result.append({
                'user_id': ledger.user_id,
                'epsilon_remaining': round(ledger.epsilon_remaining, 6),
                'epsilon_total': ledger.max_epsilon,
                'budget_percentage': round(budget_pct, 2),
                'status': status,
                'total_queries': ledger.transactions.count(),
                'last_query': last_transaction.timestamp.isoformat() if last_transaction else None,
                'last_refill': ledger.last_refill.isoformat()
            })
        
        return result


# Global instance (but now backed by database)
budget_manager = DatabasePrivacyBudgetManager()


class DatabaseBudgetWrapper:
    """
    Wrapper to make DatabasePrivacyBudgetManager compatible with PrivacyEngine
    
    PrivacyEngine expects a budget manager with get_or_create_ledger() that returns
    an object with methods like can_afford(), deduct(), get_degradation_factor(), etc.
    
    This wrapper provides that interface while using the database backend.
    """
    
    def __init__(self):
        self.db_manager = DatabasePrivacyBudgetManager()
    
    def get_or_create_ledger(self, user_id: str, initial_epsilon: float = 10.0, **kwargs):
        """
        Get or create ledger - returns a wrapper object that provides the expected interface
        """
        ledger_model = self.db_manager.get_or_create_ledger(user_id, initial_epsilon)
        return LedgerWrapper(ledger_model, self.db_manager)


class LedgerWrapper:
    """
    Wrapper around Django LedgerModel to provide the interface expected by PrivacyEngine
    """
    
    def __init__(self, ledger_model, db_manager):
        self.ledger_model = ledger_model
        self.db_manager = db_manager
        self.user_id = ledger_model.user_id
        self.epsilon_remaining = ledger_model.epsilon_remaining
        self.max_epsilon = ledger_model.max_epsilon
        self.last_refill = ledger_model.last_refill
        self.global_seed = bytes(ledger_model.global_seed)
        self.transactions = []  # Populated on demand
    
    def can_afford(self, epsilon_cost: float) -> bool:
        """Check if user has enough budget"""
        self.ledger_model.refresh_from_db()
        self.epsilon_remaining = self.ledger_model.epsilon_remaining
        return self.db_manager.can_afford(self.ledger_model, epsilon_cost)
    
    def deduct(self, query_type: str, epsilon_cost: float, mechanism: str) -> str:
        """Deduct epsilon and record transaction"""
        query_id = self.db_manager.deduct(
            self.ledger_model,
            query_type=query_type,
            epsilon_cost=epsilon_cost,
            mechanism=mechanism
        )
        # Refresh to get updated epsilon_remaining
        self.ledger_model.refresh_from_db()
        self.epsilon_remaining = self.ledger_model.epsilon_remaining
        return query_id
    
    def get_degradation_factor(self) -> float:
        """Calculate noise scaling factor based on remaining budget"""
        self.ledger_model.refresh_from_db()
        return self.db_manager.get_degradation_factor(self.ledger_model)
    
    def get_audit_log(self) -> list:
        """Get audit log for user"""
        return self.db_manager.get_audit_log(self.ledger_model)
    
    def reset_budget(self, new_epsilon: float = None):
        """Admin reset of budget"""
        self.db_manager.reset_budget(self.ledger_model, new_epsilon)
        self.ledger_model.refresh_from_db()
        self.epsilon_remaining = self.ledger_model.epsilon_remaining

