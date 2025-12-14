from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal
from app.routes import admin, auth, customer, account
from app.models.admin import Admin
from app.utils.security import hash_password

# --- LIFESPAN MANAGER (Runs on Startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create Tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed the First Admin
    db = SessionLocal()
    try:
        # Check if any admin exists
        existing_admin = db.query(Admin).first()
        if not existing_admin:
            print("⚠️ No admin found. Seeding initial super admin...")
            super_admin = Admin(
                username="admin",             # DEFAULT USERNAME
                password=hash_password("admin123") # DEFAULT PASSWORD
            )
            db.add(super_admin)
            db.commit()
            print("✅ Admin created successfully: 'admin' / 'admin123'")
        else:
            print("✅ Admin already exists. Skipping seed.")
    except Exception as e:
        print(f"❌ Error seeding admin: {e}")
    finally:
        db.close()
    
    yield # The application runs here

# --- APP INITIALIZATION ---
app = FastAPI(title="Banking Management System", lifespan=lifespan)

# --- CORS SETTINGS (Allow Frontend) ---
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://your-frontend-url.onrender.com", # Add your deployed frontend URL here later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTERS ---
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(account.router)