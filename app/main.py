# Windows async compatibility fix - MUST be at the very top
import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

"""
FastAPI application entry point for Recruiter Copilot.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import candidates


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: Initialize database
    init_db()
    print(f"🚀 {settings.app_name} started!")
    print(f"📁 Reports directory: {settings.reports_dir}")
    yield
    # Shutdown
    print(f"👋 {settings.app_name} shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Autonomous agentic recruitment engine that analyzes candidates",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(candidates.router, prefix="/api/candidates", tags=["candidates"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs",
        "health": "/health"
    }
