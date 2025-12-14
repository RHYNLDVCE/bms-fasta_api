from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Import this
from app.core.database import Base, engine
from app.routes import admin, auth
from app.routes import customer
from app.routes import account

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Banking Management System")

# --- ADD THIS BLOCK ---
# Allow your UI to communicate with the backend
origins = [
    "http://localhost:3000",  # React / Next.js default
    "http://localhost:5173",  # Vite / Vue default
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Allows only these origins
    allow_credentials=True,
    allow_methods=["*"],         # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],         # Allows all headers
)
# ----------------------

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(account.router)