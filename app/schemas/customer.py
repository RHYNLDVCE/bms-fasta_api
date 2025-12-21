from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime # <--- Added Import

# --- NEW: Minimal Account Schema ---
# We define this locally to avoid circular imports between customer.py and account.py
class AccountSummary(BaseModel):
    id: int
    account_number: str # <--- Added this so it shows in the Admin Dashboard
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
    created_at: datetime # <--- Added this (Fixes "Invalid Date")
    
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