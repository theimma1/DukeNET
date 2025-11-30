"""Payment Processing System"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum
from datetime import datetime
import uuid

class PaymentStatus(Enum):
    PENDING = "pending"
    ESCROWED = "escrowed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

@dataclass
class Payment:
    """Represents a payment transaction"""
    payment_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    buyer_id: str = ""
    agent_id: str = ""
    amount: float = 0.0
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    task_id: Optional[str] = None
    notes: str = ""
    
    def to_dict(self):
        return {
            "payment_id": self.payment_id,
            "buyer": self.buyer_id,
            "agent": self.agent_id,
            "amount": self.amount,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

@dataclass
class AgentWallet:
    """Agent earning wallet"""
    agent_id: str
    balance: float = 0.0              # Available to withdraw
    earned: float = 0.0               # Total earned
    pending: float = 0.0              # Awaiting settlement
    
    def deposit(self, amount: float):
        """Add earnings to pending"""
        self.pending += amount
    
    def settle(self, amount: float):
        """Move from pending to available balance"""
        if amount <= self.pending:
            self.pending -= amount
            self.balance += amount
            self.earned += amount
            return True
        return False
    
    def withdraw(self, amount: float) -> bool:
        """Withdraw from balance"""
        if amount <= self.balance:
            self.balance -= amount
            return True
        return False
    
    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "balance": f"{self.balance:.4f}",
            "earned": f"{self.earned:.4f}",
            "pending": f"{self.pending:.4f}",
        }

class PaymentProcessor:
    """Process payments for completed tasks"""
    
    def __init__(self):
        self.payments: Dict[str, Payment] = {}
        self.wallets: Dict[str, AgentWallet] = {}
        self.escrow: Dict[str, float] = {}  # task_id → amount
    
    def get_wallet(self, agent_id: str) -> AgentWallet:
        """Get or create agent wallet"""
        if agent_id not in self.wallets:
            self.wallets[agent_id] = AgentWallet(agent_id=agent_id)
        return self.wallets[agent_id]
    
    def create_payment(
        self,
        buyer_id: str,
        agent_id: str,
        amount: float,
        task_id: str
    ) -> Payment:
        """Create new payment"""
        payment = Payment(
            buyer_id=buyer_id,
            agent_id=agent_id,
            amount=amount,
            task_id=task_id,
            status=PaymentStatus.PENDING
        )
        self.payments[payment.payment_id] = payment
        return payment
    
    def escrow_payment(self, payment_id: str, task_id: str) -> bool:
        """Hold payment in escrow"""
        if payment_id not in self.payments:
            return False
        
        payment = self.payments[payment_id]
        payment.status = PaymentStatus.ESCROWED
        self.escrow[task_id] = payment.amount
        return True
    
    def release_payment(self, task_id: str) -> bool:
        """Release escrowed payment on task completion"""
        if task_id not in self.escrow:
            return False
        
        amount = self.escrow[task_id]
        
        # Find payment for this task
        payment = next(
            (p for p in self.payments.values() if p.task_id == task_id),
            None
        )
        
        if not payment:
            return False
        
        # Move to agent wallet
        wallet = self.get_wallet(payment.agent_id)
        wallet.deposit(amount)
        wallet.settle(amount)
        
        payment.status = PaymentStatus.COMPLETED
        payment.completed_at = datetime.now()
        
        del self.escrow[task_id]
        return True
    
    def refund_payment(self, task_id: str) -> bool:
        """Refund payment if task failed"""
        if task_id not in self.escrow:
            return False
        
        del self.escrow[task_id]
        
        payment = next(
            (p for p in self.payments.values() if p.task_id == task_id),
            None
        )
        
        if payment:
            payment.status = PaymentStatus.REFUNDED
            payment.completed_at = datetime.now()
        
        return True
    
    def get_agent_balance(self, agent_id: str) -> Dict:
        """Get agent balance"""
        return self.get_wallet(agent_id).to_dict()
    
    def get_all_wallets(self) -> Dict[str, Dict]:
        """Get all agent wallets"""
        return {
            agent_id: wallet.to_dict()
            for agent_id, wallet in self.wallets.items()
        }
