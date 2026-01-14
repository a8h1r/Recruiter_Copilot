"""
Candidate analysis API endpoints.
"""
import uuid
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db, Candidate, AnalysisRun, Report
from ..models import CandidateReport, AnalysisStatus
from ..config import settings
# Updated imports - scrapers now at agents root level
from ..agents.github_scraper import GitHubScraper
from ..agents.linkedin_scraper import LinkedInScraper
from ..agents.resume_analyzer import ResumeAnalyzer
from ..agents.analyst.resume_parser import ResumeParser
from ..agents.analyst.validator import Validator
from ..agents.analyst.gemini_client import GeminiAnalyzer
from ..agents.architect.scorer import Scorer
from ..agents.architect.report_generator import ReportGenerator
from ..snowflake_db import get_snowflake_db

router = APIRouter()

# Check if Snowflake is configured
SNOWFLAKE_ENABLED = bool(os.getenv("SNOWFLAKE_PASSWORD", ""))


async def run_analysis_pipeline(
    analysis_id: str,
    candidate_id: str,
    github_url: Optional[str],
    linkedin_url: Optional[str],
    resume_path: Optional[str],
    job_description: str,
    db: Session
):
    """
    Background task to run the full analysis pipeline.
    """
    try:
        # Update status to running
        analysis = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
        analysis.status = "running"
        db.commit()
        
        # Initialize agents
        github_scraper = GitHubScraper()
        resume_parser = ResumeParser()
        validator = Validator()
        gemini_analyzer = GeminiAnalyzer()
        scorer = Scorer()
        report_generator = ReportGenerator()
        
        # Step 1: The Researcher - Gather data
        github_data = None
        if github_url:
            try:
                github_data = await github_scraper.scrape(github_url)
            except Exception as e:
                print(f"GitHub scraping failed: {e}")
        
        # LinkedIn scraping (with fallback to skip)
        linkedin_data = None
        # LinkedIn scraping is complex and may fail - skip for now
        
        # Step 2: Parse resume
        resume_data = None
        if resume_path and Path(resume_path).exists():
            try:
                resume_data = resume_parser.parse(resume_path)
            except Exception as e:
                print(f"Resume parsing failed: {e}")
        
        # Step 3: The Analyst - Validate and analyze
        validation_flags = validator.validate(
            resume_data=resume_data,
            github_data=github_data,
            linkedin_data=linkedin_data
        )
        
        # Gemini semantic analysis
        semantic_analysis = await gemini_analyzer.analyze(
            resume_data=resume_data,
            github_data=github_data,
            job_description=job_description
        )
        
        # Step 4: The Architect - Generate score and report
        score_breakdown = scorer.calculate_score(
            github_data=github_data,
            resume_data=resume_data,
            semantic_analysis=semantic_analysis,
            validation_flags=validation_flags
        )
        
        # Generate final report
        full_report = report_generator.generate(
            candidate_id=candidate_id,
            analysis_id=analysis_id,
            github_data=github_data,
            linkedin_data=linkedin_data,
            resume_data=resume_data,
            semantic_analysis=semantic_analysis,
            validation_flags=validation_flags,
            score_breakdown=score_breakdown
        )
        
        # Save report to database
        report = Report(
            id=str(uuid.uuid4()),
            analysis_run_id=analysis_id,
            candidate_id=candidate_id,
            total_score=full_report["total_score"],
            reasoning_summary=full_report["reasoning_summary"],
            verified_skills=full_report["verified_skills"],
            flags=full_report["flags"],
            detailed_breakdown=full_report["detailed_breakdown"],
            github_data=github_data,
            linkedin_data=linkedin_data,
            resume_data=resume_data,
            full_report=full_report
        )
        db.add(report)
        
        # Save report as JSON file
        report_path = settings.reports_dir / f"candidate_report_{candidate_id}.json"
        with open(report_path, "w") as f:
            json.dump(full_report, f, indent=2, default=str)
        
        # ===== SNOWFLAKE CLOUD INTEGRATION =====
        if SNOWFLAKE_ENABLED:
            try:
                snowflake_db = get_snowflake_db()
                
                # Extract candidate name and email from resume
                candidate_name = None
                candidate_email = None
                resume_text = None
                
                if resume_data:
                    contact = resume_data.get("contact", {})
                    candidate_name = contact.get("name")
                    candidate_email = contact.get("email")
                    # Get resume summary text
                    resume_text = resume_data.get("summary", "")
                
                # Save to Snowflake
                snowflake_db.save_candidate(
                    candidate_id=candidate_id,
                    name=candidate_name,
                    email=candidate_email,
                    resume_text=resume_text,
                    github_url=github_url,
                    linkedin_url=linkedin_url,
                    total_score=full_report["total_score"],
                    reasoning_summary=full_report["reasoning_summary"],
                    verified_skills=full_report["verified_skills"],
                    flags=full_report["flags"],
                    detailed_breakdown=full_report["detailed_breakdown"],
                    full_report=full_report
                )
                print(f"✅ Candidate {candidate_id} saved to Snowflake")
                
            except Exception as e:
                print(f"⚠️ Snowflake save failed (non-blocking): {e}")
        # =========================================
        
        # Update analysis status
        analysis.status = "completed"
        analysis.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        # Update status to failed
        analysis = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_id).first()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.completed_at = datetime.utcnow()
            db.commit()
        raise


@router.post("/analyze")
async def analyze_candidate(
    background_tasks: BackgroundTasks,
    job_description: str = Form(..., description="Job description to match against"),
    resume: UploadFile = File(..., description="Resume PDF file"),
    github_url: Optional[str] = Form(None, description="GitHub profile URL"),
    linkedin_url: Optional[str] = Form(None, description="LinkedIn profile URL"),
    scoring_mode: str = Form("standard", description="Scoring mode: 'standard' or 'custom'"),
    custom_criteria: Optional[str] = Form(None, description="JSON string with custom ranking rules"),
    db: Session = Depends(get_db)
):
    """
    Submit a candidate for analysis.
    
    Upload a Resume PDF and provide a Job Description to analyze the candidate.
    
    - **resume**: PDF file upload (required)
    - **job_description**: Target job description (required)
    - **github_url**: GitHub profile URL (optional)
    - **linkedin_url**: LinkedIn profile URL (optional)
    - **scoring_mode**: "standard" (default) or "custom"
    - **custom_criteria**: JSON with custom ranking rules (for custom mode)
    
    Returns analysis ID to track progress.
    """
    # Create candidate record
    candidate_id = str(uuid.uuid4())
    candidate = Candidate(
        id=candidate_id,
        github_url=github_url,
        linkedin_url=linkedin_url
    )
    db.add(candidate)
    
    # Save resume if provided
    resume_path = None
    if resume:
        resume_dir = settings.base_dir / "uploads"
        resume_dir.mkdir(exist_ok=True)
        resume_path = str(resume_dir / f"{candidate_id}_{resume.filename}")
        with open(resume_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        candidate.resume_path = resume_path
    
    # Create analysis run
    analysis_id = str(uuid.uuid4())
    analysis = AnalysisRun(
        id=analysis_id,
        candidate_id=candidate_id,
        job_description=job_description,
        status="pending"
    )
    db.add(analysis)
    db.commit()
    
    # Queue background analysis
    background_tasks.add_task(
        run_analysis_pipeline,
        analysis_id=analysis_id,
        candidate_id=candidate_id,
        github_url=github_url,
        linkedin_url=linkedin_url,
        resume_path=resume_path,
        job_description=job_description,
        db=db
    )
    
    return {
        "message": "Analysis started",
        "analysis_id": analysis_id,
        "candidate_id": candidate_id,
        "status": "pending"
    }


@router.get("/{candidate_id}/status")
async def get_analysis_status(
    candidate_id: str,
    db: Session = Depends(get_db)
):
    """Get the status of a candidate's analysis."""
    analysis = db.query(AnalysisRun).filter(
        AnalysisRun.candidate_id == candidate_id
    ).order_by(AnalysisRun.started_at.desc()).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return AnalysisStatus(
        analysis_id=analysis.id,
        candidate_id=candidate_id,
        status=analysis.status,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        error_message=analysis.error_message
    )


@router.get("/{candidate_id}/report")
async def get_candidate_report(
    candidate_id: str,
    db: Session = Depends(get_db)
):
    """Get the generated report for a candidate."""
    report = db.query(Report).filter(
        Report.candidate_id == candidate_id
    ).order_by(Report.created_at.desc()).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report.full_report
