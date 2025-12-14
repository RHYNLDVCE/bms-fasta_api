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

# UPDATED: Removed db.commit() to allow atomic transactions in routes
def update_balance(db: Session, account: Account, amount: float):
    account.balance += amount
    db.add(account)
    return account

# UPDATED: Removed db.commit() to allow atomic transactions in routes
def create_transaction(db: Session, transaction: Transaction):
    db.add(transaction)
    return transaction