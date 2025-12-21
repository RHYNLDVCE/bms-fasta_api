from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.admin import Admin
from app.core.config import settings
# --- NEW: Use shared token generator ---
from app.utils.jwt import create_access_token as create_admin_access_token

# OAuth2 scheme for admin login
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login", scheme_name="AdminOAuth2")

# Dependency to get current logged-in admin
def get_current_admin(token: str = Depends(admin_oauth2_scheme), db: Session = Depends(get_db)) -> Admin:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        admin_id: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        
        if admin_id is None or role != "admin":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    admin = db.query(Admin).filter(Admin.id == int(admin_id)).first()
    if admin is None:
        raise credentials_exception
    return admin