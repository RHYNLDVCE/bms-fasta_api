from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.customer import CustomerCreate, CustomerResponse, TokenResponse
from app.models.customer import Customer
from app.crud.customer import create_customer, get_customer_by_email
from app.utils.security import hash_password, verify_password
# --- UPDATED IMPORT: Added get_current_customer ---
from app.utils.auth_customer import create_customer_access_token, get_current_customer

router = APIRouter(prefix="/customers", tags=["Customers"])

# --- Register new customer ---
@router.post("/register", response_model=CustomerResponse)
def register_customer(payload: CustomerCreate, db: Session = Depends(get_db)):

    existing = get_customer_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    customer = Customer(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone_number=payload.phone_number,
        password_hash=hash_password(payload.password),
    )

    return create_customer(db, customer)


# --- Login customer (OAuth2 password flow compatible) ---
@router.post("/login", response_model=TokenResponse)
def login_customer(
    username: str = Form(...),  # Swagger OAuth2 expects 'username'
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Treat username as email
    customer = get_customer_by_email(db, username)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(password, customer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_customer_access_token({
        "sub": str(customer.id),
        "role": "customer"
    })

    return TokenResponse(access_token=access_token)

# --- NEW: Get Current User Profile ---
@router.get("/me", response_model=CustomerResponse)
def read_users_me(current_user: Customer = Depends(get_current_customer)):
    return current_user