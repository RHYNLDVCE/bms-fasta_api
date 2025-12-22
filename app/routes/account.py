from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import random
import requests 
from pydantic import BaseModel # <--- Added for the lookup response model

from app.core.database import get_db
from app.core.config import settings
from app.models.account import Account
from app.models.customer import Customer
from app.schemas.account import AccountCreate, AccountResponse
from app.crud.account import (
    create_account, 
    get_accounts_by_customer, 
    get_account_by_id,
    get_account_by_number, 
    get_account_for_update,
    update_balance, 
    delete_account
)
from app.utils.auth_customer import get_current_customer

router = APIRouter(prefix="/accounts", tags=["Accounts"])

# --- NEW: Schema for Lookup Response ---
class AccountLookupResponse(BaseModel):
    account_number: str
    owner_name: str

def generate_account_number():
    return "".join([str(random.randint(0, 9)) for _ in range(9)])

# --- NEW: Lookup Endpoint ---
@router.get("/lookup/{account_number}", response_model=AccountLookupResponse)
def lookup_account_owner(
    account_number: str,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    # 1. Find the account
    account = get_account_by_number(db, account_number)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # 2. Find the owner
    owner = db.query(Customer).filter(Customer.id == account.customer_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Account owner not found")

    # 3. Censor the name (e.g., "John Doe" -> "J*** D***")
    def censor(name):
        if not name: return "***"
        return name[0] + "***" if len(name) > 0 else "***"
        
    censored_name = f"{censor(owner.first_name)} {censor(owner.last_name)}"
    
    return {"account_number": account.account_number, "owner_name": censored_name}

@router.post("/", response_model=AccountResponse)
def create_customer_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    new_account_number = generate_account_number()
    while db.query(Account).filter(Account.account_number == new_account_number).first():
        new_account_number = generate_account_number()

    account = Account(
        customer_id=current_customer.id,
        account_type=payload.account_type,
        account_number=new_account_number,
        balance=0.0
    )
    return create_account(db, account)

@router.get("/", response_model=List[AccountResponse])
def list_customer_accounts(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    return get_accounts_by_customer(db, current_customer.id)

@router.get("/{account_id}", response_model=AccountResponse)
def get_account_details(
    account_id: int,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    account = get_account_by_id(db, account_id)
    if not account or account.customer_id != current_customer.id:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.post("/{account_id}/withdraw", response_model=AccountResponse)
def withdraw_account(
    account_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    try:
        # 1. Lock Row
        account = get_account_for_update(db, account_id)
        
        if not account or account.customer_id != current_customer.id:
            raise HTTPException(status_code=404, detail="Account not found")
            
        if account.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        # 2. Update Balance
        update_balance(db, account, -amount)
        
        # 3. Call Node.js Microservice
        try:
            requests.post(settings.TRANSACTION_SERVICE_URL, json={
                "accountId": account.id,
                "type": "withdraw",
                "amount": amount,
                "details": "ATM Withdrawal"
            }, timeout=2)
        except Exception as e:
            print(f"Warning: Failed to save transaction history: {e}")
        
        db.commit()
        db.refresh(account)
        return account
        
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Withdrawal failed")

@router.post("/transfer", response_model=List[AccountResponse])
def transfer_account(
    from_account_id: int,
    to_account_number: str,
    amount: float,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer)
):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    try:
        # 1. Resolve Target Account Number -> ID
        target_account_lookup = get_account_by_number(db, to_account_number)
        if not target_account_lookup:
            raise HTTPException(status_code=404, detail="Target account number not found")
        
        to_account_id = target_account_lookup.id

        if str(from_account_id) == str(to_account_id):
             raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

        # 2. Lock Rows (Sorted ID order to prevent Deadlock)
        first_id, second_id = sorted([from_account_id, to_account_id])
        get_account_for_update(db, first_id)
        get_account_for_update(db, second_id)
        
        # 3. Fetch fresh objects
        from_account = get_account_by_id(db, from_account_id)
        to_account = get_account_by_id(db, to_account_id)

        # --- FIX: VALIDATION CHECKS ---
        if not from_account or from_account.customer_id != current_customer.id:
            raise HTTPException(status_code=404, detail="Source account not found")
            
        if not to_account:  # <--- THIS WAS MISSING
            raise HTTPException(status_code=404, detail="Target account not found")

        if from_account.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        # ------------------------------

        # 4. Update Balances
        update_balance(db, from_account, -amount)
        update_balance(db, to_account, amount)

        # 5. Call Node.js Microservice
        try:
            # Sender Receipt
            requests.post(settings.TRANSACTION_SERVICE_URL, json={
                "accountId": from_account.id,
                "type": "transfer",
                "amount": amount,
                "details": f"To Acc: {to_account.account_number}"
            }, timeout=2)
            
            # Receiver Receipt
            requests.post(settings.TRANSACTION_SERVICE_URL, json={
                "accountId": to_account.id,
                "type": "deposit",
                "amount": amount,
                "details": f"From Acc: {from_account.account_number}"
            }, timeout=2)
        except Exception as e:
            print(f"Warning: Failed to save transaction history: {e}")
        
        db.commit()
        db.refresh(from_account)
        db.refresh(to_account)
        return [from_account, to_account]

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transfer failed")

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
        raise HTTPException(status_code=400, detail="Cannot close account with remaining balance.")

    delete_account(db, account_id)
    return None