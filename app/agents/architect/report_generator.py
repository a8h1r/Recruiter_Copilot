"""
Report Generator - The Architect Agent

This module generates the final candidate_report.json artifact containing:
1. Total score with breakdown
2. Reasoning summary
3. Verified skills with confidence levels
4. Validation flags
5. Raw data from all sources

Author: Recruiter Copilot
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ...config import settings


class ReportGenerator:
    """
    Generates structured JSON candidate reports.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Directory to save reports (defaults to settings.reports_dir)
        """
        self.output_dir = output_dir or settings.reports_dir
        self.output_dir.mkdir(exist_ok=True)
    
    def generate(
        self,
        candidate_id: str,
        analysis_id: str,
        github_data: Optional[Dict[str, Any]] = None,
        linkedin_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
        semantic_analysis: Optional[Dict[str, Any]] = None,
        validation_flags: Optional[List[Dict]] = None,
        score_breakdown: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive candidate report.
        
        Args:
            candidate_id: Unique candidate identifier
            analysis_id: Analysis run identifier
            github_data: GitHub profile data
            linkedin_data: LinkedIn profile data
            resume_data: Parsed resume data
            semantic_analysis: Gemini AI analysis
            validation_flags: Validation flags list
            score_breakdown: Score calculation results
            
        Returns:
            Complete candidate report dictionary
        """
        # Build the report
        report = {
            "meta": {
                "candidate_id": candidate_id,
                "analysis_id": analysis_id,
                "generated_at": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "engine": "Recruiter Copilot"
            },
            
            # Core results
            "total_score": score_breakdown.get("total_score", 0) if score_breakdown else 0,
            
            "reasoning_summary": self._generate_reasoning_summary(
                score_breakdown, semantic_analysis, validation_flags
            ),
            
            "verified_skills": self._extract_verified_skills(
                github_data, resume_data, semantic_analysis
            ),
            
            "flags": validation_flags or [],
            
            "detailed_breakdown": score_breakdown.get("breakdown", {}) if score_breakdown else {},
            
            "interpretation": score_breakdown.get("interpretation", {}) if score_breakdown else {},
            
            # Source summaries
            "github_summary": self._summarize_github(github_data),
            "linkedin_summary": self._summarize_linkedin(linkedin_data),
            "resume_summary": self._summarize_resume(resume_data),
            
            # AI insights
            "ai_analysis": self._format_ai_analysis(semantic_analysis),
            
            # Raw data (for debugging/audit)
            "raw_data": {
                "github": github_data,
                "linkedin": linkedin_data,
                "resume": resume_data
            }
        }
        
        return report
    
    def save_report(
        self,
        report: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """
        Save report to JSON file.
        
        Args:
            report: Report dictionary
            filename: Custom filename (optional)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            candidate_id = report.get("meta", {}).get("candidate_id", "unknown")
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"candidate_report_{candidate_id}_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        
        return output_path
    
    def _generate_reasoning_summary(
        self,
        score_breakdown: Optional[Dict],
        semantic_analysis: Optional[Dict],
        validation_flags: Optional[List[Dict]]
    ) -> str:
        """Generate a human-readable reasoning summary."""
        parts = []
        
        if score_breakdown:
            total = score_breakdown.get("total_score", 0)
            interpretation = score_breakdown.get("interpretation", {})
            rating = interpretation.get("rating", "UNKNOWN")
            
            parts.append(f"Candidate scored {total}/10 ({rating}).")
        
        if semantic_analysis:
            # Add AI summary
            ai_summary = semantic_analysis.get("summary", "")
            if ai_summary:
                parts.append(ai_summary)
            
            # Add key insights
            strengths = semantic_analysis.get("strengths", [])
            if strengths:
                parts.append(f"Key strengths include: {', '.join(strengths[:2])}.")
            
            concerns = semantic_analysis.get("concerns", [])
            if concerns:
                parts.append(f"Areas of concern: {', '.join(concerns[:2])}.")
        
        if validation_flags:
            high_flags = [f for f in validation_flags if f.get("severity") == "HIGH"]
            if high_flags:
                parts.append(f"⚠️ Found {len(high_flags)} critical discrepancy(ies) in claims.")
        
        return " ".join(parts) if parts else "Analysis completed. Please review individual sections."
    
    def _extract_verified_skills(
        self,
        github_data: Optional[Dict],
        resume_data: Optional[Dict],
        semantic_analysis: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Extract skills with verification from multiple sources."""
        verified_skills = []
        
        # Get skills from all sources
        resume_skills = set()
        if resume_data:
            for skill in resume_data.get("skill_keywords", []):
                resume_skills.add(skill["keyword"].lower())
        
        github_languages = set()
        if github_data:
            for lang in github_data.get("top_languages", []):
                if isinstance(lang, dict):
                    github_languages.add(lang["name"].lower())
                else:
                    github_languages.add(str(lang).lower())
        
        ai_matching = set()
        if semantic_analysis:
            for skill in semantic_analysis.get("key_matching_skills", []):
                ai_matching.add(skill.lower())
        
        # Calculate confidence for each resume skill
        for skill in resume_skills:
            evidence_sources = []
            confidence = 0.5  # Base confidence from resume
            
            # Check GitHub
            skill_normalized = skill.lower()
            if any(skill_normalized in gl.lower() for gl in github_languages):
                confidence += 0.3
                evidence_sources.append("GitHub repos")
            
            # Check AI matching
            if any(skill_normalized in am.lower() for am in ai_matching):
                confidence += 0.2
                evidence_sources.append("AI verified")
            
            evidence = f"Resume"
            if evidence_sources:
                evidence += f", {', '.join(evidence_sources)}"
            
            verified_skills.append({
                "skill": skill.title(),
                "confidence": round(min(1.0, confidence), 2),
                "evidence": evidence
            })
        
        # Sort by confidence
        verified_skills.sort(key=lambda x: x["confidence"], reverse=True)
        
        return verified_skills[:20]  # Top 20 skills
    
    def _summarize_github(self, github_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Create a summary of GitHub data."""
        if not github_data:
            return None
        
        return {
            "username": github_data.get("username"),
            "commits_12_months": github_data.get("commits_12_months", 0),
            "public_repos": github_data.get("public_repos", 0),
            "top_languages": [
                lang["name"] if isinstance(lang, dict) else lang
                for lang in github_data.get("top_languages", [])[:5]
            ],
            "readme_quality": github_data.get("readme_complexity_score", 0),
            "contribution_streak": github_data.get("contribution_streak", 0),
            "followers": github_data.get("followers", 0)
        }
    
    def _summarize_linkedin(self, linkedin_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Create a summary of LinkedIn data."""
        if not linkedin_data:
            return None
        
        if linkedin_data.get("status") == "scraping_failed":
            return {
                "status": "unavailable",
                "message": linkedin_data.get("message", "LinkedIn data not available")
            }
        
        return {
            "name": linkedin_data.get("name"),
            "headline": linkedin_data.get("headline"),
            "location": linkedin_data.get("location"),
            "experience_count": len(linkedin_data.get("experience", [])),
            "education_count": len(linkedin_data.get("education", [])),
            "skills_count": len(linkedin_data.get("skills", []))
        }
    
    def _summarize_resume(self, resume_data: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Create a summary of resume data."""
        if not resume_data:
            return None
        
        return {
            "name": resume_data.get("contact", {}).get("name"),
            "email": resume_data.get("contact", {}).get("email"),
            "total_experience_years": resume_data.get("total_years_experience", 0),
            "positions_held": len(resume_data.get("experience", [])),
            "skills_detected": len(resume_data.get("skill_keywords", [])),
            "certifications": len(resume_data.get("certifications", []))
        }
    
    def _format_ai_analysis(self, semantic_analysis: Optional[Dict]) -> Optional[Dict[str, Any]]:
        """Format AI analysis for the report."""
        if not semantic_analysis:
            return None
        
        return {
            "technical_match_score": semantic_analysis.get("technical_match_score"),
            "experience_relevance_score": semantic_analysis.get("experience_relevance_score"),
            "hiring_recommendation": semantic_analysis.get("hiring_recommendation"),
            "matching_skills": semantic_analysis.get("key_matching_skills", []),
            "missing_skills": semantic_analysis.get("missing_skills", []),
            "strengths": semantic_analysis.get("strengths", []),
            "concerns": semantic_analysis.get("concerns", [])
        }


# Test function
def test_generator():
    """Test the report generator."""
    generator = ReportGenerator()
    
    report = generator.generate(
        candidate_id="test-123",
        analysis_id="analysis-456",
        github_data={
            "username": "testuser",
            "commits_12_months": 234,
            "top_languages": [{"name": "Python"}, {"name": "JavaScript"}],
            "public_repos": 25,
            "readme_complexity_score": 7.5
        },
        resume_data={
            "contact": {"name": "Test User", "email": "test@example.com"},
            "total_years_experience": 5,
            "skill_keywords": [{"keyword": "python"}, {"keyword": "aws"}]
        },
        semantic_analysis={
            "technical_match_score": 8,
            "experience_relevance_score": 7,
            "key_matching_skills": ["Python", "AWS"],
            "hiring_recommendation": "YES",
            "strengths": ["Strong Python", "Cloud experience"],
            "concerns": ["Limited frontend"]
        },
        validation_flags=[],
        score_breakdown={
            "total_score": 7.5,
            "breakdown": {
                "technical_match": 8.0,
                "experience_depth": 7.0,
                "activity_score": 7.5,
                "credibility": 10.0
            },
            "interpretation": {
                "rating": "GOOD",
                "recommendation": "YES"
            }
        }
    )
    
    import json
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    test_generator()
