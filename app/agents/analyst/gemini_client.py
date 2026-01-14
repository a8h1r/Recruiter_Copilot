"""
Gemini AI Client - The Analyst Agent

This module integrates Google's Gemini 3 Pro for semantic analysis:
1. Resume vs Job Description matching
2. Skill relevance scoring beyond keywords
3. Experience depth assessment
4. Overall candidate assessment

Author: Recruiter Copilot
"""
import asyncio
from typing import Dict, List, Optional, Any
import google.generativeai as genai

from ...config import settings


class GeminiAnalyzer:
    """
    Gemini AI integration for semantic candidate analysis.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini analyzer.
        
        Args:
            api_key: Gemini API key (uses config if not provided)
        """
        self.api_key = api_key or settings.gemini_api_key
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None
            print("Warning: Gemini API key not configured")
    
    async def analyze(
        self,
        resume_data: Optional[Dict[str, Any]] = None,
        github_data: Optional[Dict[str, Any]] = None,
        job_description: str = ""
    ) -> Dict[str, Any]:
        """
        Perform semantic analysis of candidate against job description.
        
        Args:
            resume_data: Parsed resume data
            github_data: GitHub profile data
            job_description: Target job description
            
        Returns:
            Semantic analysis results with scores and insights
        """
        if not self.model:
            return self._get_fallback_analysis()
        
        try:
            # Build context for Gemini
            context = self._build_analysis_context(
                resume_data, github_data, job_description
            )
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(context)
            
            # Call Gemini API
            response = await asyncio.to_thread(
                self._generate_response, prompt
            )
            
            # Parse response
            analysis = self._parse_gemini_response(response)
            
            return analysis
            
        except Exception as e:
            print(f"Gemini analysis failed: {e}")
            return self._get_fallback_analysis()
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response from Gemini (sync wrapper)."""
        response = self.model.generate_content(prompt)
        return response.text
    
    def _build_analysis_context(
        self,
        resume_data: Optional[Dict],
        github_data: Optional[Dict],
        job_description: str
    ) -> Dict[str, Any]:
        """Build context dictionary for analysis."""
        context = {
            "job_description": job_description[:3000],  # Limit length
            "resume": {},
            "github": {}
        }
        
        if resume_data:
            context["resume"] = {
                "contact": resume_data.get("contact", {}),
                "total_years_experience": resume_data.get("total_years_experience", 0),
                "skills": [s["keyword"] for s in resume_data.get("skill_keywords", [])[:20]],
                "summary": resume_data.get("summary", "")[:500],
                "experience_count": len(resume_data.get("experience", []))
            }
        
        if github_data:
            context["github"] = {
                "username": github_data.get("username"),
                "commits_12_months": github_data.get("commits_12_months", 0),
                "top_languages": github_data.get("top_languages", [])[:5],
                "public_repos": github_data.get("public_repos", 0),
                "readme_complexity": github_data.get("readme_complexity_score", 0)
            }
        
        return context
    
    def _create_analysis_prompt(self, context: Dict) -> str:
        """Create the analysis prompt for Gemini."""
        prompt = """You are an expert technical recruiter AI. Analyze this candidate against the job description and provide a structured assessment.

## Job Description
{job_description}

## Candidate Resume Summary
- Total Experience: {total_years} years
- Key Skills: {skills}
- Professional Summary: {summary}

## GitHub Activity
- Username: {github_username}
- Commits (last 12 months): {commits}
- Top Languages: {languages}
- Public Repos: {repos}
- README Quality Score: {readme_score}/10

## Your Task
Provide a JSON response with the following structure:
{{
    "technical_match_score": <1-10 score for skills alignment>,
    "experience_relevance_score": <1-10 score for experience relevance>,
    "key_matching_skills": [<list of 3-5 skills that match the JD>],
    "missing_skills": [<list of important skills missing for this role>],
    "strengths": [<2-3 candidate strengths>],
    "concerns": [<1-2 potential concerns>],
    "hiring_recommendation": "<STRONG_YES|YES|MAYBE|NO|STRONG_NO>",
    "summary": "<2-3 sentence overall assessment>"
}}

Be objective and focus on factual evidence from the provided data. If data is missing, note that in your assessment."""

        # Format the prompt
        resume = context.get("resume", {})
        github = context.get("github", {})
        
        formatted = prompt.format(
            job_description=context.get("job_description", "Not provided"),
            total_years=resume.get("total_years_experience", "Unknown"),
            skills=", ".join(resume.get("skills", ["Not provided"])),
            summary=resume.get("summary", "Not provided"),
            github_username=github.get("username", "Not provided"),
            commits=github.get("commits_12_months", "Unknown"),
            languages=", ".join([
                l["name"] if isinstance(l, dict) else str(l) 
                for l in github.get("top_languages", ["Not provided"])
            ]),
            repos=github.get("public_repos", "Unknown"),
            readme_score=github.get("readme_complexity", "Unknown")
        )
        
        return formatted
    
    def _parse_gemini_response(self, response: str) -> Dict[str, Any]:
        """Parse Gemini's response into structured data."""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                
                # Ensure required fields
                return {
                    "technical_match_score": parsed.get("technical_match_score", 5),
                    "experience_relevance_score": parsed.get("experience_relevance_score", 5),
                    "key_matching_skills": parsed.get("key_matching_skills", []),
                    "missing_skills": parsed.get("missing_skills", []),
                    "strengths": parsed.get("strengths", []),
                    "concerns": parsed.get("concerns", []),
                    "hiring_recommendation": parsed.get("hiring_recommendation", "MAYBE"),
                    "summary": parsed.get("summary", "Analysis completed"),
                    "raw_response": response
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: return raw response with default scores
        return {
            "technical_match_score": 5,
            "experience_relevance_score": 5,
            "key_matching_skills": [],
            "missing_skills": [],
            "strengths": [],
            "concerns": [],
            "hiring_recommendation": "MAYBE",
            "summary": response[:500] if response else "Analysis could not be completed",
            "raw_response": response
        }
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Return fallback analysis when Gemini is unavailable."""
        return {
            "technical_match_score": 5,
            "experience_relevance_score": 5,
            "key_matching_skills": [],
            "missing_skills": [],
            "strengths": ["Unable to perform AI analysis"],
            "concerns": ["Gemini API not available"],
            "hiring_recommendation": "MANUAL_REVIEW",
            "summary": "AI analysis unavailable. Please review candidate manually.",
            "status": "fallback"
        }
    
    async def quick_skill_match(
        self,
        skills: List[str],
        job_description: str
    ) -> Dict[str, float]:
        """
        Quick semantic matching of skills against job description.
        
        Returns dict mapping each skill to a relevance score (0-1).
        """
        if not self.model or not skills:
            return {skill: 0.5 for skill in skills}
        
        try:
            prompt = f"""Rate how relevant each skill is for this job (0-1 scale):

Job Description (excerpt):
{job_description[:1000]}

Skills to rate:
{', '.join(skills)}

Return JSON: {{"skill_name": <0-1 score>, ...}}"""
            
            response = await asyncio.to_thread(
                self._generate_response, prompt
            )
            
            # Parse response
            import json
            import re
            
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            print(f"Quick skill match failed: {e}")
        
        return {skill: 0.5 for skill in skills}


# Test function
async def test_analyzer():
    """Test the Gemini analyzer."""
    analyzer = GeminiAnalyzer()
    
    result = await analyzer.analyze(
        resume_data={
            "skill_keywords": [
                {"keyword": "python"},
                {"keyword": "fastapi"},
                {"keyword": "aws"}
            ],
            "total_years_experience": 5,
            "summary": "Backend developer with experience in Python APIs"
        },
        github_data={
            "username": "testuser",
            "commits_12_months": 200,
            "top_languages": [{"name": "Python"}],
            "public_repos": 20
        },
        job_description="Looking for a Senior Python Backend Developer with FastAPI experience"
    )
    
    import json
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(test_analyzer())
