from pydantic import BaseModel
from typing import Optional

class AccountCreate(BaseModel):
    account_type: str

class AccountResponse(BaseModel):
    id: int
    account_type: str
    balance: float
    status: str

    class Config:
        from_attributes = True

