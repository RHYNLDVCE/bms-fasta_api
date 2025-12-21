from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import random # <--- Import this
import string # <--- Import this

from app.core.database import get_db
from app.models.account import Account
from app.models.customer import Customer
from app.schemas.account import AccountCreate, AccountResponse
from app.crud.account import create_account, get_accounts_by_customer, get_account_by_id, update_balance, create_transaction, delete_account
from app.utils.auth_customer import get_current_customer
from app.models.transaction import Transaction

router = APIRouter(prefix="/accounts", tags=["Accounts"])

# --- Helper Function ---
def generate_account_number():
    """Generates a random 9-digit string."""
    return "".join([str(random.randint(0, 9)) for _ in range(9)])

# --- Updated Route ---
@router.post("/", response_model=AccountResponse)
def create_customer_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    # 1. Generate the number
    new_account_number = generate_account_number()

    # 2. Check for collision (optional but recommended for production)
    # while db.query(Account).filter(Account.account_number == new_account_number).first():
    #     new_account_number = generate_account_number()

    # 3. Create Account with the number
    account = Account(
        customer_id=current_customer.id,
        account_type=payload.account_type,
        account_number=new_account_number,  # <--- THIS WAS MISSING
        balance=0.0
    )
    return create_account(db, account)

# ... (Rest of the file remains the same)
@router.get("/", response_model=List[AccountResponse])
def list_customer_accounts(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    return get_accounts_by_customer(db, current_customer.id)

@router.post("/{account_id}/withdraw", response_model=AccountResponse)
def withdraw_account(
    account_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    account = get_account_by_id(db, account_id)
    if not account or account.customer_id != current_customer.id:
        raise HTTPException(status_code=404, detail="Account not found")
    if amount <= 0 or account.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance or invalid amount")

    try:
        update_balance(db, account, -amount)
        create_transaction(db, Transaction(account_id=account.id, type="withdraw", amount=amount))
        db.commit()
        db.refresh(account)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Withdrawal failed")
        
    return account

@router.post("/transfer", response_model=List[AccountResponse])
def transfer_account(
    from_account_id: int,
    to_account_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    from_account = get_account_by_id(db, from_account_id)
    to_account = get_account_by_id(db, to_account_id)

    if not from_account or from_account.customer_id != current_customer.id:
        raise HTTPException(status_code=404, detail="Source account not found")
    if not to_account:
        raise HTTPException(status_code=404, detail="Target account not found")
    if amount <= 0 or from_account.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance or invalid amount")

    try:
        update_balance(db, from_account, -amount)
        update_balance(db, to_account, amount)

        create_transaction(db, Transaction(account_id=from_account.id, type="transfer", amount=amount, details=f"To account {to_account.id}"))
        create_transaction(db, Transaction(account_id=to_account.id, type="transfer", amount=amount, details=f"From account {from_account.id}"))
        
        db.commit()
        db.refresh(from_account)
        db.refresh(to_account)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transfer failed")

    return [from_account, to_account]

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    account = get_account_by_id(db, account_id)
    
    if not account or account.customer_id != current_customer.id:
        raise HTTPException(status_code=404, detail="Account not found")

    if account.balance != 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot close account with remaining balance. Please withdraw funds first."
        )

    delete_account(db, account_id)
    return None