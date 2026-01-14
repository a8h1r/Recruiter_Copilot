"""
SQLite database setup and models for Recruiter Copilot.
Uses SQLAlchemy for ORM with async support.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

# Create SQLite engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Candidate(Base):
    """Candidate profile model."""
    __tablename__ = "candidates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    github_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    resume_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalysisRun(Base):
    """Analysis run tracking model."""
    __tablename__ = "analysis_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String(36), nullable=False)
    job_description = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class Report(Base):
    """Generated report model."""
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_run_id = Column(String(36), nullable=False)
    candidate_id = Column(String(36), nullable=False)
    total_score = Column(Float, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    verified_skills = Column(JSON, nullable=True)
    flags = Column(JSON, nullable=True)
    detailed_breakdown = Column(JSON, nullable=True)
    github_data = Column(JSON, nullable=True)
    linkedin_data = Column(JSON, nullable=True)
    resume_data = Column(JSON, nullable=True)
    full_report = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
