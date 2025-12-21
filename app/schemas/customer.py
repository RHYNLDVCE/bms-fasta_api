from pydantic import BaseModel, EmailStr
from typing import List, Optional

# --- NEW: Minimal Account Schema ---
# We define this locally to avoid circular imports between customer.py and account.py
class AccountSummary(BaseModel):
    id: int
    account_type: str
    balance: float
    status: str

    class Config:
        from_attributes = True

class CustomerCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    password: str

class CustomerResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    status: str
    # --- NEW: Include list of accounts in the response ---
    accounts: List[AccountSummary] = [] 

    class Config:
        from_attributes = True

class CustomerLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"