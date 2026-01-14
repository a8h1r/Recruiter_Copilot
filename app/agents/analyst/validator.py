"""
Validator - The Analyst Agent ("Bullshit Detector")

This module cross-validates data from different sources to identify:
1. Experience claims that exceed framework/technology age
2. Inconsistencies between resume and online presence
3. Gaps or discrepancies in work history
4. Inflated skill claims vs. actual GitHub activity

Author: Recruiter Copilot
"""
from datetime import datetime
from typing import Dict, List, Optional, Any


class Validator:
    """
    Cross-validates candidate data from resume, GitHub, and LinkedIn.
    Flags potential discrepancies and inconsistencies.
    """
    
    # Framework/technology release dates (approximate)
    TECH_RELEASE_DATES = {
        # Frontend
        "react": 2013,
        "react native": 2015,
        "vue": 2014,
        "vue.js": 2014,
        "angular": 2016,  # Angular 2+
        "svelte": 2016,
        "next.js": 2016,
        "tailwind": 2017,
        "tailwindcss": 2017,
        
        # Backend
        "fastapi": 2018,
        "nestjs": 2017,
        "deno": 2018,
        
        # Cloud/DevOps
        "kubernetes": 2014,
        "terraform": 2014,
        "github actions": 2019,
        "docker": 2013,
        "aws lambda": 2014,
        
        # Data/ML
        "pytorch": 2016,
        "tensorflow": 2015,
        "gpt": 2018,
        "langchain": 2022,
        "openai api": 2020,
        "llm": 2020,
        
        # Languages
        "rust": 2010,
        "go": 2009,
        "golang": 2009,
        "kotlin": 2011,
        "swift": 2014,
        "typescript": 2012,
        
        # Databases
        "snowflake": 2014,
        "cockroachdb": 2015,
        "planetscale": 2018,
    }
    
    # Severity levels
    SEVERITY_LOW = "LOW"
    SEVERITY_MEDIUM = "MEDIUM"
    SEVERITY_HIGH = "HIGH"
    
    def __init__(self):
        """Initialize the validator."""
        self.current_year = datetime.now().year
    
    def validate(
        self,
        resume_data: Optional[Dict[str, Any]] = None,
        github_data: Optional[Dict[str, Any]] = None,
        linkedin_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Validate candidate data across all sources.
        
        Args:
            resume_data: Parsed resume data
            github_data: Scraped GitHub data
            linkedin_data: Scraped LinkedIn data
            
        Returns:
            List of validation flags with severity and descriptions
        """
        flags = []
        
        if resume_data:
            # Check experience claims vs technology age
            flags.extend(self._validate_experience_claims(resume_data))
            
            # Check for inflated experience durations
            flags.extend(self._validate_experience_timeline(resume_data))
        
        if resume_data and github_data:
            # Cross-validate skills vs GitHub activity
            flags.extend(self._validate_skills_vs_github(resume_data, github_data))
            
            # Check for claimed vs actual activity
            flags.extend(self._validate_activity_level(resume_data, github_data))
        
        if resume_data and linkedin_data:
            # Cross-validate resume vs LinkedIn
            flags.extend(self._validate_resume_vs_linkedin(resume_data, linkedin_data))
        
        return flags
    
    def _validate_experience_claims(self, resume_data: Dict) -> List[Dict]:
        """Validate experience claims against technology release dates."""
        flags = []
        
        skill_keywords = resume_data.get("skill_keywords", [])
        raw_text = resume_data.get("summary", "") or ""
        
        # Look for "X years of experience in Y" patterns in full text
        import re
        
        # Combine all text for analysis
        full_text = raw_text.lower()
        for exp in resume_data.get("experience", []):
            full_text += " " + str(exp.get("raw_text", "")).lower()
        
        # Pattern: "X years of experience with/in TECHNOLOGY"
        patterns = [
            r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:experience\s+)?(?:with|in|using)\s+([a-zA-Z\s\.\-]+)",
            r"([a-zA-Z\s\.\-]+)\s+expert\s+with\s+(\d+)\+?\s*years?",
            r"(\d+)\+?\s*years?\s+([a-zA-Z\s\.\-]+)\s+(?:developer|engineer|developer)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, full_text)
            
            for match in matches:
                # Determine which group is years and which is tech
                if match[0].isdigit():
                    years = int(match[0])
                    tech = match[1].strip().lower()
                else:
                    tech = match[0].strip().lower()
                    years = int(match[1])
                
                # Check against known release dates
                for known_tech, release_year in self.TECH_RELEASE_DATES.items():
                    if known_tech in tech:
                        max_possible_years = self.current_year - release_year
                        
                        if years > max_possible_years + 1:  # Add 1 year buffer
                            flags.append({
                                "type": "EXPERIENCE_MISMATCH",
                                "severity": self.SEVERITY_HIGH,
                                "description": f"Claims {years} years experience with {known_tech}, but it was released in {release_year} ({max_possible_years} years ago)",
                                "evidence": {
                                    "claimed_years": years,
                                    "max_possible_years": max_possible_years,
                                    "technology": known_tech,
                                    "release_year": release_year
                                }
                            })
                        break
        
        return flags
    
    def _validate_experience_timeline(self, resume_data: Dict) -> List[Dict]:
        """Check for overlapping or impossible experience timelines."""
        flags = []
        
        experiences = resume_data.get("experience", [])
        total_years = resume_data.get("total_years_experience", 0)
        
        # Flag if total experience seems unreasonably high without context
        if total_years > 30:
            flags.append({
                "type": "EXCESSIVE_EXPERIENCE",
                "severity": self.SEVERITY_MEDIUM,
                "description": f"Total experience claimed is {total_years} years, which is unusually high",
                "evidence": {
                    "total_years": total_years
                }
            })
        
        # Check for overlapping positions (simplified check)
        # This would need more sophisticated date parsing in production
        
        return flags
    
    def _validate_skills_vs_github(
        self, 
        resume_data: Dict, 
        github_data: Dict
    ) -> List[Dict]:
        """Cross-validate claimed skills against GitHub activity."""
        flags = []
        
        # Get claimed skills from resume
        claimed_skills = set()
        for skill in resume_data.get("skill_keywords", []):
            claimed_skills.add(skill["keyword"].lower())
        
        # Get languages from GitHub
        github_languages = set()
        for lang in github_data.get("top_languages", []):
            if isinstance(lang, dict):
                github_languages.add(lang["name"].lower())
            else:
                github_languages.add(str(lang).lower())
        
        # Check for major skill claims not backed by GitHub
        major_language_claims = {"python", "javascript", "java", "go", "rust", "typescript", "c++"}
        
        for skill in claimed_skills:
            if skill in major_language_claims:
                # Normalize for comparison
                skill_variants = {skill, skill.replace("++", "pp")}
                
                if not any(s in github_languages for s in skill_variants):
                    # Check if they have any repos at all
                    if github_data.get("public_repos", 0) > 5:
                        flags.append({
                            "type": "SKILL_NOT_VERIFIED",
                            "severity": self.SEVERITY_MEDIUM,
                            "description": f"Claims {skill.upper()} expertise on resume, but no {skill.upper()} repos found on GitHub",
                            "evidence": {
                                "claimed_skill": skill,
                                "github_languages": list(github_languages)
                            }
                        })
        
        return flags
    
    def _validate_activity_level(
        self,
        resume_data: Dict,
        github_data: Dict
    ) -> List[Dict]:
        """Validate claimed developer experience vs GitHub activity."""
        flags = []
        
        total_years = resume_data.get("total_years_experience", 0)
        commits = github_data.get("commits_12_months", 0)
        public_repos = github_data.get("public_repos", 0)
        
        # Senior developers claiming many years but minimal GitHub presence
        if total_years >= 5:
            if commits < 50 and public_repos < 5:
                flags.append({
                    "type": "LOW_GITHUB_ACTIVITY",
                    "severity": self.SEVERITY_LOW,
                    "description": f"Claims {total_years} years experience but has minimal GitHub activity ({commits} commits, {public_repos} repos in last year)",
                    "evidence": {
                        "years_experience": total_years,
                        "github_commits_12m": commits,
                        "github_repos": public_repos
                    }
                })
        
        return flags
    
    def _validate_resume_vs_linkedin(
        self,
        resume_data: Dict,
        linkedin_data: Dict
    ) -> List[Dict]:
        """Cross-validate resume against LinkedIn profile."""
        flags = []
        
        # Skip if LinkedIn scraping failed
        if linkedin_data.get("status") == "scraping_failed":
            return flags
        
        # Compare job titles (simplified)
        resume_experience = resume_data.get("experience", [])
        linkedin_experience = linkedin_data.get("experience", [])
        
        # Check for major title discrepancies
        # This is a simplified check - production would need fuzzy matching
        
        resume_titles = set()
        for exp in resume_experience:
            if exp.get("title"):
                resume_titles.add(exp["title"].lower())
        
        linkedin_titles = set()
        for exp in linkedin_experience:
            if exp.get("title"):
                linkedin_titles.add(exp["title"].lower())
        
        # If both have data but no overlap, flag it
        if resume_titles and linkedin_titles:
            overlap = resume_titles.intersection(linkedin_titles)
            if not overlap and len(resume_titles) > 2 and len(linkedin_titles) > 2:
                flags.append({
                    "type": "TITLE_MISMATCH",
                    "severity": self.SEVERITY_MEDIUM,
                    "description": "Job titles on resume don't match LinkedIn profile",
                    "evidence": {
                        "resume_titles": list(resume_titles)[:3],
                        "linkedin_titles": list(linkedin_titles)[:3]
                    }
                })
        
        return flags
    
    def get_credibility_score(self, flags: List[Dict]) -> float:
        """
        Calculate credibility score based on flags.
        
        Returns:
            Score from 0-10 (10 = fully credible)
        """
        if not flags:
            return 10.0
        
        deductions = 0
        
        for flag in flags:
            severity = flag.get("severity", self.SEVERITY_LOW)
            
            if severity == self.SEVERITY_HIGH:
                deductions += 3
            elif severity == self.SEVERITY_MEDIUM:
                deductions += 1.5
            else:
                deductions += 0.5
        
        score = max(0, 10 - deductions)
        return round(score, 1)


# Test function
def test_validator():
    """Test the validator with sample data."""
    validator = Validator()
    
    # Sample data with a deliberate BS claim
    resume_data = {
        "skill_keywords": [
            {"keyword": "react native", "count": 5},
            {"keyword": "python", "count": 10}
        ],
        "summary": "Senior developer with 8 years of experience in React Native and 5 years with FastAPI",
        "experience": [
            {"duration_months": 96, "raw_text": "8 years React Native"}
        ],
        "total_years_experience": 8
    }
    
    github_data = {
        "commits_12_months": 234,
        "top_languages": [{"name": "Python", "percentage": 80}],
        "public_repos": 15
    }
    
    flags = validator.validate(
        resume_data=resume_data,
        github_data=github_data
    )
    
    import json
    print(json.dumps(flags, indent=2))
    print(f"\nCredibility Score: {validator.get_credibility_score(flags)}/10")


if __name__ == "__main__":
    test_validator()
