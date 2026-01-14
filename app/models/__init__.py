"""
Pydantic models for request/response schemas.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class CandidateSubmission(BaseModel):
    """Request model for submitting a candidate for analysis."""
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    job_description: str = Field(..., description="Job description to match against")
    # Resume will be uploaded as a file separately


class AnalysisStatus(BaseModel):
    """Response model for analysis status."""
    analysis_id: str
    candidate_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class VerifiedSkill(BaseModel):
    """A verified skill with confidence score."""
    skill: str
    confidence: float = Field(..., ge=0, le=1)
    evidence: str


class Flag(BaseModel):
    """A validation flag (potential discrepancy)."""
    type: str
    severity: str  # LOW, MEDIUM, HIGH
    description: str
    evidence: dict


class DetailedBreakdown(BaseModel):
    """Scoring breakdown by category."""
    technical_match: float = Field(..., ge=0, le=10)
    experience_depth: float = Field(..., ge=0, le=10)
    activity_score: float = Field(..., ge=0, le=10)
    credibility: float = Field(..., ge=0, le=10)


class CandidateReport(BaseModel):
    """Full candidate analysis report."""
    candidate_id: str
    analysis_id: str
    total_score: float = Field(..., ge=0, le=10)
    reasoning_summary: str
    verified_skills: List[VerifiedSkill]
    flags: List[Flag]
    detailed_breakdown: DetailedBreakdown
    github_summary: Optional[dict] = None
    linkedin_summary: Optional[dict] = None
    resume_summary: Optional[dict] = None
    created_at: datetime
