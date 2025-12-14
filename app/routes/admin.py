from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.admin import AdminCreate, AdminOut
from app.crud import admin as crud_admin
from app.utils.auth_admin import get_current_admin
from app.models.admin import Admin
from app.models.account import Account
from app.models.transaction import Transaction
from app.crud.account import get_account_by_id, update_balance, create_transaction
from app.schemas.account import AccountResponse

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

# UPDATED: Added db.commit() because CRUD no longer auto-commits
@router.post("/{account_id}/credit", response_model=AccountResponse)
def credit_account(account_id: int, amount: float, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
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

# UPDATED: Added db.commit() because CRUD no longer auto-commits
@router.post("/{account_id}/debit", response_model=AccountResponse)
def debit_account(account_id: int, amount: float, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
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