from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer

class Account(Base):
    __tablename__ = "accounts"
    
    # Prevent negative balances at the database level
    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_positive_balance'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Unique 9-digit number
    account_number: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False) 

    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False)
    account_type: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="accounts")