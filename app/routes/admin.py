from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.admin import AdminCreate, AdminOut
from app.crud import admin as crud_admin
from app.utils.auth_admin import get_current_admin
from app.models.admin import Admin
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.crud.account import get_account_by_id, update_balance, create_transaction
from app.schemas.account import AccountResponse
from app.schemas.customer import CustomerResponse
from app.crud.customer import get_customer_by_id, delete_customer
from app.crud.account import delete_account


router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/", response_model=AdminOut)
def create_admin(
    admin: AdminCreate, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    if crud_admin.get_admin_by_username(db, admin.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    return crud_admin.create_admin(db, admin)

# --- MOVED UP: Static routes must come before dynamic routes like /{admin_id} ---
@router.get("/customers", response_model=List[CustomerResponse])
def get_all_customers(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(get_current_admin)
):
    # This fetches all customers from the database
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers
# -------------------------------------------------------------------------------

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
        update_balance(db, account, amount)
        create_transaction(db, Transaction(account_id=account.id, type="credit", amount=amount, details=f"Credited by admin {current_admin.id}"))
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
        update_balance(db, account, -amount)
        create_transaction(db, Transaction(account_id=account.id, type="debit", amount=amount, details=f"Debited by admin {current_admin.id}"))
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
    # 1. Get the customer
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 2. Check their accounts for money
    # (Assuming strict banking rules: you can't delete a user with money)
    for account in customer.accounts:
        if account.balance > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Customer has active account ({account.account_type}) with funds. Cannot delete."
            )

    # 3. Clean up empty accounts first (to avoid Foreign Key errors)
    for account in customer.accounts:
        delete_account(db, account.id)

    # 4. Delete the customer
    delete_customer(db, customer_id)
    
    return {"detail": "Customer and associated accounts deleted"}