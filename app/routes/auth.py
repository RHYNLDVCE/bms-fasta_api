from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud.admin import authenticate_admin
from app.utils.auth_admin import create_admin_access_token

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    admin = authenticate_admin(db, form_data.username, form_data.password)
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # UPDATED: Added "role": "admin" to the token payload
    token = create_admin_access_token({"sub": str(admin.id), "role": "admin"})
    
    return {"access_token": token, "token_type": "bearer"}