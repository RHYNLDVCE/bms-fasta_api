from app.core.database import SessionLocal
from app.models.admin import Admin
from app.utils.security import hash_password

def seed_initial_admin():
    db = SessionLocal()
    try:
        # Check if an admin already exists to avoid duplicates
        existing_admin = db.query(Admin).first()
        if existing_admin:
            print(f"Admin already exists (ID: {existing_admin.id}). Skipping seed.")
            return

        print("Creating initial super admin...")
        super_admin = Admin(
            username="admin",             # Default Username
            password=hash_password("admin123") # Default Password (CHANGE THIS!)
        )
        db.add(super_admin)
        db.commit()
        print("Successfully created admin.")
        print("Username: admin")
        print("Password: admin123")
        
    except Exception as e:
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_initial_admin()