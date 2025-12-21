from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func # <--- Used for summing balances
import requests 

from app.core.database import get_db
from app.core.config import settings
from app.schemas.admin import AdminCreate, AdminOut
from app.crud import admin as crud_admin
from app.utils.auth_admin import get_current_admin
from app.models.admin import Admin
from app.models.account import Account
from app.models.customer import Customer
from app.crud.account import get_account_by_id, update_balance 
from app.schemas.account import AccountResponse
from app.schemas.customer import CustomerResponse
from app.crud.customer import get_customer_by_id, delete_customer, search_customers # <--- Import search
from app.crud.account import delete_account


router = APIRouter(prefix="/admin", tags=["Admin"])

# ... (keep create_admin route) ...

# --- NEW: Dashboard Stats Endpoint ---
@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    total_customers = db.query(Customer).count()
    total_accounts = db.query(Account).count()
    total_holdings = db.query(func.sum(Account.balance)).scalar() or 0.0
    
    return {
        "total_customers": total_customers,
        "total_accounts": total_accounts,
        "total_holdings": total_holdings
    }

# --- UPDATED: Search-Only Customer List ---
@router.get("/customers", response_model=List[CustomerResponse])
def get_customers(
    q: Optional[str] = None, # Search Query
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    if q:
        # If there is a search term, run the server-side search
        return search_customers(db, q)
    
    # If NO search term, return EMPTY list (Prevents fetching everyone)
    return []


@router.post("/", response_model=AdminOut)
def create_admin(
    admin: AdminCreate, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    if crud_admin.get_admin_by_username(db, admin.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    return crud_admin.create_admin(db, admin)

@router.get("/customers", response_model=List[CustomerResponse])
def get_all_customers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers

@router.get("/{admin_id}", response_model=AdminOut)
def read_admin(
    admin_id: int, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    db_admin = crud_admin.get_admin(db, admin_id)
    if not db_admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return db_admin

@router.delete("/{admin_id}", response_model=dict)
def remove_admin(
    admin_id: int, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    success = crud_admin.delete_admin(db, admin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Admin not found")
    return {"detail": "Admin deleted"}

@router.post("/{account_id}/credit", response_model=AccountResponse)
def credit_account(
    account_id: int, 
    amount: float, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    account = get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    try:
        # 1. Update SQL Balance
        update_balance(db, account, amount)
        
        # 2. Call Node.js Microservice (Log as Deposit)
        try:
            requests.post(settings.TRANSACTION_SERVICE_URL, json={
                "accountId": account.id,
                "type": "deposit",
                "amount": amount,
                "details": f"Credited by Admin {current_admin.username}"
            }, timeout=2)
        except Exception as e:
            print(f"Warning: Failed to save transaction history: {e}")

        db.commit()
        db.refresh(account)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Credit failed")
        
    return account

@router.post("/{account_id}/debit", response_model=AccountResponse)
def debit_account(
    account_id: int, 
    amount: float, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    account = get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if amount <= 0 or account.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance or invalid amount")

    try:
        # 1. Update SQL Balance
        update_balance(db, account, -amount)
        
        # 2. Call Node.js Microservice (Log as Withdraw)
        try:
            requests.post(settings.TRANSACTION_SERVICE_URL, json={
                "accountId": account.id,
                "type": "withdraw",
                "amount": amount,
                "details": f"Debited by Admin {current_admin.username}"
            }, timeout=2)
        except Exception as e:
            print(f"Warning: Failed to save transaction history: {e}")

        db.commit()
        db.refresh(account)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Debit failed")
        
    return account

@router.delete("/customers/{customer_id}")
def remove_customer(
    customer_id: int, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    for account in customer.accounts:
        if account.balance > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Customer has active account ({account.account_type}) with funds. Cannot delete."
            )

    for account in customer.accounts:
        delete_account(db, account.id)

    delete_customer(db, customer_id)
    
    return {"detail": "Customer and associated accounts deleted"}