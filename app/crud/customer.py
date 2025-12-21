from sqlalchemy.orm import Session
from sqlalchemy import or_ # <--- Import this
from app.models.customer import Customer
from app.models.account import Account # <--- Import Account for joining

def create_customer(db: Session, customer: Customer):
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

def get_customer_by_email(db: Session, email: str):
    return db.query(Customer).filter(Customer.email == email).first()

def get_customer_by_id(db: Session, customer_id: int):
    return db.query(Customer).filter(Customer.id == customer_id).first()

def delete_customer(db: Session, customer_id: int):
    customer = get_customer_by_id(db, customer_id)
    if customer:
        db.delete(customer)
        db.commit()
        return True
    return False

# --- NEW: Server-Side Search Logic ---
def search_customers(db: Session, query: str):
    search_term = f"%{query}%"
    return db.query(Customer).outerjoin(Customer.accounts).filter(
        or_(
            Customer.first_name.ilike(search_term),
            Customer.last_name.ilike(search_term),
            Customer.email.ilike(search_term),
            Account.account_number.ilike(search_term)
        )
    ).distinct().all() # .distinct() prevents duplicates if multiple accounts match