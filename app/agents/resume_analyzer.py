"""
Resume Analyzer - Modular Resume Analysis with Multiple Strategies

This module provides flexible resume analysis with:
1. default_scan(): Standard keyword/skill extraction using Gemini Flash
2. custom_scan(): Placeholder for company-specific ranking rules

Author: Recruiter Copilot
"""
import asyncio
from typing import Dict, List, Optional, Any
import google.generativeai as genai

from ..config import settings


class ResumeAnalyzer:
    """
    Modular resume analyzer supporting multiple scanning strategies.
    
    Strategies:
    - "standard": Uses Gemini Flash for fast keyword extraction
    - "custom": Allows companies to pass their own ranking rules
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the resume analyzer.
        
        Args:
            api_key: Gemini API key (uses config if not provided)
        """
        self.api_key = api_key or settings.gemini_api_key
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use Gemini Flash for faster processing
            self.flash_model = genai.GenerativeModel("gemini-1.5-flash-latest")
            self.pro_model = genai.GenerativeModel("gemini-1.5-pro-latest")
        else:
            self.flash_model = None
            self.pro_model = None
            print("Warning: Gemini API key not configured")
    
    async def default_scan(
        self,
        resume_text: str,
        job_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Standard resume scan using Gemini Flash.
        
        Extracts:
        - Key skills and technologies
        - Years of experience estimates
        - Education level
        - Job title matches
        - Overall fit score
        
        Args:
            resume_text: Extracted text from resume
            job_description: Optional job description for matching
            
        Returns:
            Dictionary with extracted data and scores
        """
        if not self.flash_model:
            return self._get_fallback_result()
        
        try:
            prompt = self._build_default_prompt(resume_text, job_description)
            
            response = await asyncio.to_thread(
                self._generate_flash_response, prompt
            )
            
            return self._parse_scan_response(response)
            
        except Exception as e:
            print(f"Default scan failed: {e}")
            return self._get_fallback_result()
    
    async def custom_scan(
        self,
        resume_text: str,
        criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Custom resume scan with company-specific ranking rules.
        
        This is a placeholder for companies to define their own
        evaluation criteria and weighting.
        
        Args:
            resume_text: Extracted text from resume
            criteria: Dictionary containing:
                - required_skills: List of must-have skills
                - preferred_skills: List of nice-to-have skills
                - experience_weight: Weight for experience (0-1)
                - skill_weight: Weight for skills (0-1)
                - education_weight: Weight for education (0-1)
                - custom_questions: List of custom evaluation questions
                - scoring_rubric: Custom scoring rules
                
        Returns:
            Dictionary with custom evaluation results
        """
        if not self.pro_model:
            return self._get_fallback_result()
        
        try:
            prompt = self._build_custom_prompt(resume_text, criteria)
            
            response = await asyncio.to_thread(
                self._generate_pro_response, prompt
            )
            
            result = self._parse_scan_response(response)
            result["scan_type"] = "custom"
            result["criteria_used"] = criteria
            
            return result
            
        except Exception as e:
            print(f"Custom scan failed: {e}")
            return self._get_fallback_result()
    
    def _generate_flash_response(self, prompt: str) -> str:
        """Generate response using Gemini Flash (sync)."""
        response = self.flash_model.generate_content(prompt)
        return response.text
    
    def _generate_pro_response(self, prompt: str) -> str:
        """Generate response using Gemini Pro (sync)."""
        response = self.pro_model.generate_content(prompt)
        return response.text
    
    def _build_default_prompt(
        self,
        resume_text: str,
        job_description: Optional[str]
    ) -> str:
        """Build prompt for default scanning."""
        jd_section = ""
        if job_description:
            jd_section = f"""
## Target Job Description
{job_description[:2000]}
"""
        
        return f"""Analyze this resume and extract structured information.

## Resume Content
{resume_text[:5000]}
{jd_section}

## Your Task
Return a JSON response with:
{{
    "extracted_skills": [<list of technical skills found>],
    "experience_years": <estimated total years of experience>,
    "education_level": "<high_school|bachelors|masters|phd|other>",
    "current_role": "<most recent job title>",
    "industries": [<industries worked in>],
    "skill_match_score": <0-10 if JD provided, else null>,
    "key_achievements": [<top 3 achievements>],
    "languages": [<programming languages>],
    "frameworks": [<frameworks and libraries>],
    "certifications": [<professional certifications>],
    "summary": "<2-3 sentence candidate summary>"
}}

Be objective and extract only factual information from the resume."""
    
    def _build_custom_prompt(
        self,
        resume_text: str,
        criteria: Dict[str, Any]
    ) -> str:
        """Build prompt for custom scanning with company criteria."""
        required_skills = criteria.get("required_skills", [])
        preferred_skills = criteria.get("preferred_skills", [])
        custom_questions = criteria.get("custom_questions", [])
        
        questions_section = ""
        if custom_questions:
            questions_section = "\n".join([
                f"- {q}" for q in custom_questions
            ])
            questions_section = f"""
## Custom Evaluation Questions
{questions_section}
"""
        
        return f"""Evaluate this resume against specific company criteria.

## Resume Content
{resume_text[:5000]}

## Required Skills (must-have)
{', '.join(required_skills) if required_skills else 'None specified'}

## Preferred Skills (nice-to-have)
{', '.join(preferred_skills) if preferred_skills else 'None specified'}
{questions_section}

## Your Task
Return a JSON response with:
{{
    "required_skills_found": [<which required skills were found>],
    "required_skills_missing": [<which required skills are missing>],
    "preferred_skills_found": [<which preferred skills were found>],
    "required_match_percentage": <0-100>,
    "preferred_match_percentage": <0-100>,
    "custom_answers": {{<answers to custom questions>}},
    "overall_fit_score": <0-10>,
    "recommendation": "<STRONG_FIT|GOOD_FIT|PARTIAL_FIT|NOT_FIT>",
    "gaps": [<skill or experience gaps identified>],
    "strengths": [<candidate strengths for this role>]
}}

Be thorough and objective in your evaluation."""
    
    def _parse_scan_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into structured data."""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                parsed["scan_type"] = "ai_analyzed"
                parsed["raw_response"] = response
                return parsed
            except json.JSONDecodeError:
                pass
        
        # Fallback if JSON parsing fails
        return {
            "scan_type": "parse_failed",
            "raw_response": response,
            "extracted_skills": [],
            "summary": response[:500] if response else "Analysis failed"
        }
    
    def _get_fallback_result(self) -> Dict[str, Any]:
        """Return fallback result when AI is unavailable."""
        return {
            "scan_type": "fallback",
            "extracted_skills": [],
            "experience_years": None,
            "education_level": None,
            "skill_match_score": None,
            "summary": "AI analysis unavailable. Manual review required.",
            "status": "fallback"
        }


# Example usage
async def test_analyzer():
    """Test the resume analyzer."""
    analyzer = ResumeAnalyzer()
    
    sample_resume = """
    John Doe
    Senior Software Engineer
    
    Experience:
    - Senior Software Engineer at TechCorp (2020-Present)
      - Led development of microservices using Python and FastAPI
      - Implemented CI/CD pipelines with GitHub Actions
    
    - Software Engineer at StartupXYZ (2018-2020)
      - Built React frontend applications
      - Worked with PostgreSQL and Redis
    
    Education:
    - BS in Computer Science, MIT, 2018
    
    Skills: Python, JavaScript, React, FastAPI, Docker, AWS, PostgreSQL
    """
    
    result = await analyzer.default_scan(
        resume_text=sample_resume,
        job_description="Looking for a Senior Python Developer with FastAPI experience"
    )
    
    import json
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(test_analyzer())
