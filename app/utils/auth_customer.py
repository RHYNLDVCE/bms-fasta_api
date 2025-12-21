from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.customer import Customer
from app.crud.customer import get_customer_by_id
from app.core.config import settings
# --- NEW: Use shared token generator ---
from app.utils.jwt import create_access_token as create_customer_access_token

# OAuth2 scheme for customer login
customer_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/customers/login", scheme_name="CustomerOAuth2")

# Dependency to get current logged-in customer
def get_current_customer(token: str = Depends(customer_oauth2_scheme), db: Session = Depends(get_db)) -> Customer:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        customer_id: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        if customer_id is None or role != "customer":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    customer = get_customer_by_id(db, int(customer_id))
    if customer is None:
        raise credentials_exception
    return customer