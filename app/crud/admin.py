from sqlalchemy.orm import Session
from app.models.admin import Admin
from app.schemas.admin import AdminCreate
from app.utils.security import hash_password
from app.utils.security import verify_password
def get_admin(db: Session, admin_id: int):
    return db.query(Admin).filter(Admin.id == admin_id).first()

def get_admin_by_username(db: Session, username: str):
    return db.query(Admin).filter(Admin.username == username).first()

def create_admin(db: Session, admin: AdminCreate):
    hashed_password = hash_password(admin.password)
    db_admin = Admin(
        username=admin.username,
        password=hashed_password
    )
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

def delete_admin(db: Session, admin_id: int):
    admin = get_admin(db, admin_id)
    if admin:
        db.delete(admin)
        db.commit()
        return True
    return False


def authenticate_admin(db: Session, username: str, password: str):
    db_admin = get_admin_by_username(db, username)
    if not db_admin:
        return None

    if not verify_password(password, db_admin.password):
        return None

    return db_admin

