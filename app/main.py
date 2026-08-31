import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.models import *  # Ensure all ORM models are registered
from app.api.v1 import api_router
from app.routers.pages import router as pages_router

# Create database tables
Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"--- {settings.PROJECT_NAME} Started Successfully ---")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full-stack real-money online gaming platform featuring double-entry integer wallet ledger, manual UPI verification desk, and provably fair game engines.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & Uploads mounts
os.makedirs("static", exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include API and Pages routers
app.include_router(api_router, prefix="/api")
app.include_router(pages_router)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}


