"""
Scorer - The Architect Agent

This module calculates the final Technical Alignment Score (1-10) based on:
1. Technical Match (40%): Skills alignment with job description
2. Experience Depth (25%): Verified experience duration and relevance
3. Activity Score (20%): GitHub contribution quality and consistency
4. Credibility (15%): Absence of validation flags

Author: Recruiter Copilot
"""
from typing import Dict, List, Optional, Any


class Scorer:
    """
    Calculates the comprehensive Technical Alignment Score.
    
    Scoring weights:
    - Technical Match: 40%
    - Experience Depth: 25%
    - Activity Score: 20%
    - Credibility: 15%
    """
    
    # Scoring weights
    WEIGHTS = {
        "technical_match": 0.40,
        "experience_depth": 0.25,
        "activity_score": 0.20,
        "credibility": 0.15
    }
    
    # Activity benchmarks
    ACTIVITY_BENCHMARKS = {
        "commits_excellent": 500,   # 500+ commits = 10/10
        "commits_good": 200,        # 200+ commits = 8/10
        "commits_fair": 50,         # 50+ commits = 6/10
        "repos_excellent": 30,      # 30+ repos = 10/10
        "repos_good": 15,           # 15+ repos = 8/10
        "repos_fair": 5             # 5+ repos = 6/10
    }
    
    def __init__(self):
        """Initialize the scorer."""
        pass
    
    def calculate_score(
        self,
        github_data: Optional[Dict[str, Any]] = None,
        resume_data: Optional[Dict[str, Any]] = None,
        semantic_analysis: Optional[Dict[str, Any]] = None,
        validation_flags: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Calculate the comprehensive alignment score.
        
        Args:
            github_data: Scraped GitHub profile data
            resume_data: Parsed resume data
            semantic_analysis: Gemini AI analysis results
            validation_flags: List of validation flags from Validator
            
        Returns:
            Dictionary with total score and detailed breakdown
        """
        # Calculate individual scores
        technical_score = self._calculate_technical_match(
            resume_data, semantic_analysis
        )
        
        experience_score = self._calculate_experience_depth(
            resume_data, semantic_analysis
        )
        
        activity_score = self._calculate_activity_score(github_data)
        
        credibility_score = self._calculate_credibility(validation_flags)
        
        # Calculate weighted total
        total_score = (
            technical_score * self.WEIGHTS["technical_match"] +
            experience_score * self.WEIGHTS["experience_depth"] +
            activity_score * self.WEIGHTS["activity_score"] +
            credibility_score * self.WEIGHTS["credibility"]
        )
        
        # Round to 1 decimal
        total_score = round(total_score, 1)
        
        return {
            "total_score": total_score,
            "breakdown": {
                "technical_match": round(technical_score, 1),
                "experience_depth": round(experience_score, 1),
                "activity_score": round(activity_score, 1),
                "credibility": round(credibility_score, 1)
            },
            "weights": self.WEIGHTS,
            "interpretation": self._interpret_score(total_score)
        }
    
    def _calculate_technical_match(
        self,
        resume_data: Optional[Dict],
        semantic_analysis: Optional[Dict]
    ) -> float:
        """
        Calculate technical skills match score.
        
        Based on:
        - Gemini's technical_match_score (if available)
        - Number of matching skill keywords
        """
        score = 5.0  # Default neutral score
        
        if semantic_analysis:
            # Use Gemini's assessment as primary signal
            ai_score = semantic_analysis.get("technical_match_score", 5)
            score = float(ai_score)
            
            # Adjust based on matching skills
            matching_skills = semantic_analysis.get("key_matching_skills", [])
            missing_skills = semantic_analysis.get("missing_skills", [])
            
            # Bonus for many matching skills
            if len(matching_skills) >= 5:
                score += 0.5
            elif len(matching_skills) >= 3:
                score += 0.25
            
            # Penalty for critical missing skills
            if len(missing_skills) >= 4:
                score -= 1.0
            elif len(missing_skills) >= 2:
                score -= 0.5
        
        elif resume_data:
            # Fallback: count skill keywords
            skill_keywords = resume_data.get("skill_keywords", [])
            
            if len(skill_keywords) >= 15:
                score = 8.0
            elif len(skill_keywords) >= 10:
                score = 7.0
            elif len(skill_keywords) >= 5:
                score = 6.0
            else:
                score = 5.0
        
        return max(0, min(10, score))
    
    def _calculate_experience_depth(
        self,
        resume_data: Optional[Dict],
        semantic_analysis: Optional[Dict]
    ) -> float:
        """
        Calculate experience depth score.
        
        Based on:
        - Years of experience
        - AI's experience relevance assessment
        - Number of positions held
        """
        score = 5.0
        
        if resume_data:
            years = resume_data.get("total_years_experience", 0)
            
            # Years-based scoring
            if years >= 10:
                score = 9.0
            elif years >= 7:
                score = 8.0
            elif years >= 5:
                score = 7.0
            elif years >= 3:
                score = 6.0
            elif years >= 1:
                score = 5.0
            else:
                score = 4.0
            
            # Adjust for number of positions (career progression)
            experience_count = len(resume_data.get("experience", []))
            if experience_count >= 4:
                score += 0.5
        
        if semantic_analysis:
            # Incorporate AI assessment
            ai_relevance = semantic_analysis.get("experience_relevance_score", 5)
            # Blend with years-based score
            score = (score + float(ai_relevance)) / 2
        
        return max(0, min(10, score))
    
    def _calculate_activity_score(self, github_data: Optional[Dict]) -> float:
        """
        Calculate GitHub activity score.
        
        Based on:
        - Commits in last 12 months
        - Number of public repositories
        - README quality
        - Contribution streak
        """
        if not github_data:
            return 5.0  # Neutral if no GitHub data
        
        # Commits score (max 4 points)
        commits = github_data.get("commits_12_months", 0)
        if commits >= self.ACTIVITY_BENCHMARKS["commits_excellent"]:
            commits_score = 4.0
        elif commits >= self.ACTIVITY_BENCHMARKS["commits_good"]:
            commits_score = 3.0
        elif commits >= self.ACTIVITY_BENCHMARKS["commits_fair"]:
            commits_score = 2.0
        else:
            commits_score = 1.0
        
        # Repos score (max 3 points)
        repos = github_data.get("public_repos", 0)
        if repos >= self.ACTIVITY_BENCHMARKS["repos_excellent"]:
            repos_score = 3.0
        elif repos >= self.ACTIVITY_BENCHMARKS["repos_good"]:
            repos_score = 2.0
        elif repos >= self.ACTIVITY_BENCHMARKS["repos_fair"]:
            repos_score = 1.5
        else:
            repos_score = 1.0
        
        # README quality (max 2 points)
        readme_score = github_data.get("readme_complexity_score", 5) / 5
        
        # Streak bonus (max 1 point)
        streak = github_data.get("contribution_streak", 0)
        streak_score = min(1.0, streak / 30)  # 30+ day streak = 1 point
        
        total = commits_score + repos_score + readme_score + streak_score
        
        return max(0, min(10, total))
    
    def _calculate_credibility(
        self,
        validation_flags: Optional[List[Dict]]
    ) -> float:
        """
        Calculate credibility score based on validation flags.
        
        Starts at 10 and deducts points for each flag.
        """
        score = 10.0
        
        if not validation_flags:
            return score
        
        for flag in validation_flags:
            severity = flag.get("severity", "LOW")
            
            if severity == "HIGH":
                score -= 3.0
            elif severity == "MEDIUM":
                score -= 1.5
            else:  # LOW
                score -= 0.5
        
        return max(0, min(10, score))
    
    def _interpret_score(self, score: float) -> Dict[str, str]:
        """
        Provide human-readable interpretation of the score.
        """
        if score >= 8.5:
            return {
                "rating": "EXCELLENT",
                "recommendation": "STRONG_YES",
                "description": "Outstanding candidate with strong technical alignment"
            }
        elif score >= 7.0:
            return {
                "rating": "GOOD",
                "recommendation": "YES",
                "description": "Well-qualified candidate worth interviewing"
            }
        elif score >= 5.5:
            return {
                "rating": "FAIR",
                "recommendation": "MAYBE",
                "description": "Candidate has potential but may lack some requirements"
            }
        elif score >= 4.0:
            return {
                "rating": "BELOW_AVERAGE",
                "recommendation": "PROBABLY_NO",
                "description": "Significant gaps in qualifications for this role"
            }
        else:
            return {
                "rating": "POOR",
                "recommendation": "NO",
                "description": "Candidate does not meet minimum requirements"
            }
    
    def explain_score(
        self,
        score_breakdown: Dict[str, Any],
        semantic_analysis: Optional[Dict] = None,
        validation_flags: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a natural language explanation of the score.
        """
        total = score_breakdown.get("total_score", 0)
        breakdown = score_breakdown.get("breakdown", {})
        interpretation = score_breakdown.get("interpretation", {})
        
        parts = [
            f"**Overall Score: {total}/10 ({interpretation.get('rating', 'N/A')})**",
            "",
            "**Score Breakdown:**",
            f"- Technical Match: {breakdown.get('technical_match', 0)}/10 (weight: 40%)",
            f"- Experience Depth: {breakdown.get('experience_depth', 0)}/10 (weight: 25%)",
            f"- Activity Score: {breakdown.get('activity_score', 0)}/10 (weight: 20%)",
            f"- Credibility: {breakdown.get('credibility', 0)}/10 (weight: 15%)",
            ""
        ]
        
        # Add AI insights if available
        if semantic_analysis:
            strengths = semantic_analysis.get("strengths", [])
            concerns = semantic_analysis.get("concerns", [])
            
            if strengths:
                parts.append("**Strengths:**")
                for s in strengths:
                    parts.append(f"- {s}")
                parts.append("")
            
            if concerns:
                parts.append("**Concerns:**")
                for c in concerns:
                    parts.append(f"- {c}")
                parts.append("")
        
        # Add flags if present
        if validation_flags:
            high_flags = [f for f in validation_flags if f.get("severity") == "HIGH"]
            if high_flags:
                parts.append("**⚠️ Critical Flags:**")
                for flag in high_flags:
                    parts.append(f"- {flag.get('description', 'Unknown issue')}")
                parts.append("")
        
        parts.append(f"**Recommendation:** {interpretation.get('recommendation', 'MANUAL_REVIEW')}")
        parts.append(f"_{interpretation.get('description', '')}_")
        
        return "\n".join(parts)


# Test function
def test_scorer():
    """Test the scorer with sample data."""
    scorer = Scorer()
    
    result = scorer.calculate_score(
        github_data={
            "commits_12_months": 234,
            "public_repos": 25,
            "readme_complexity_score": 7.5,
            "contribution_streak": 15
        },
        resume_data={
            "total_years_experience": 5,
            "experience": [1, 2, 3],  # 3 positions
            "skill_keywords": [{"keyword": k} for k in ["python", "aws", "docker"]]
        },
        semantic_analysis={
            "technical_match_score": 8,
            "experience_relevance_score": 7,
            "key_matching_skills": ["Python", "AWS", "Docker"],
            "missing_skills": ["Kubernetes"],
            "strengths": ["Strong Python background"],
            "concerns": []
        },
        validation_flags=[]
    )
    
    import json
    print(json.dumps(result, indent=2))
    print("\n" + scorer.explain_score(result))


if __name__ == "__main__":
    test_scorer()
