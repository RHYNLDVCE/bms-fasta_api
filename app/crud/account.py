from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.transaction import Transaction

def create_account(db: Session, account: Account):
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

def get_accounts_by_customer(db: Session, customer_id: int):
    return db.query(Account).filter(Account.customer_id == customer_id).all()

def get_account_by_id(db: Session, account_id: int):
    return db.query(Account).filter(Account.id == account_id).first()

# --- NEW: Get by Account Number (For Transfers) ---
def get_account_by_number(db: Session, account_number: str):
    return db.query(Account).filter(Account.account_number == account_number).first()

# --- NEW: Lock Row (For Safety) ---
def get_account_for_update(db: Session, account_id: int):
    return db.query(Account).filter(Account.id == account_id).with_for_update().first()

def update_balance(db: Session, account: Account, amount: float):
    account.balance += amount
    db.add(account)
    return account

def delete_account(db: Session, account_id: int):
    account = get_account_by_id(db, account_id)
    if account:
        db.delete(account)
        db.commit()
        return True
    return False