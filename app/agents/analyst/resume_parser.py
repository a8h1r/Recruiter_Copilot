"""
Resume Parser - The Analyst Agent

This module parses PDF resumes and extracts structured information:
1. Contact information (name, email, phone)
2. Work experience with dates and durations
3. Education history
4. Skills and technologies
5. Certifications and achievements

Uses PyMuPDF (fitz) for PDF text extraction.

Author: Recruiter Copilot
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import fitz  # PyMuPDF


class ResumeParser:
    """
    PDF resume parser that extracts structured candidate information.
    """
    
    # Common section headers (case-insensitive patterns)
    SECTION_PATTERNS = {
        "experience": r"(?i)(work\s*experience|professional\s*experience|employment|work\s*history|experience)",
        "education": r"(?i)(education|academic|qualifications|degrees)",
        "skills": r"(?i)(skills|technical\s*skills|technologies|competencies|expertise)",
        "certifications": r"(?i)(certifications?|certificates?|licenses?|credentials)",
        "projects": r"(?i)(projects|personal\s*projects|portfolio)",
        "summary": r"(?i)(summary|profile|objective|about\s*me)"
    }
    
    # Date patterns for experience parsing
    DATE_PATTERNS = [
        r"(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4}|present|current|now)",
        r"(\d{1,2}/\d{4})\s*[-–]\s*(\d{1,2}/\d{4}|present|current|now)",
        r"(\d{4})\s*[-–]\s*(\d{4}|present|current|now)"
    ]
    
    # Email pattern
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    
    # Phone pattern
    PHONE_PATTERN = r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}"
    
    # Common programming languages and frameworks
    TECH_KEYWORDS = [
        # Languages
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
        # Frontend
        "react", "angular", "vue", "svelte", "next.js", "nuxt", "html", "css",
        "sass", "tailwind", "bootstrap", "jquery",
        # Backend
        "node.js", "express", "fastapi", "django", "flask", "spring", "rails",
        ".net", "asp.net", "laravel", "nestjs",
        # Data
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "snowflake", "bigquery", "spark", "hadoop", "kafka",
        # Cloud
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
        "jenkins", "github actions", "ci/cd",
        # ML/AI
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "keras",
        "machine learning", "deep learning", "nlp", "computer vision"
    ]
    
    def __init__(self):
        """Initialize the resume parser."""
        pass
    
    def parse(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse a PDF resume and extract structured data.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing parsed resume data
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume not found: {pdf_path}")
        
        # Extract text from PDF
        text = self._extract_text(path)
        
        # Parse different sections
        result = {
            "file_path": str(path),
            "parsed_at": datetime.utcnow().isoformat(),
            "raw_text_length": len(text),
            "contact": self._extract_contact(text),
            "experience": self._extract_experience(text),
            "education": self._extract_education(text),
            "skills": self._extract_skills(text),
            "certifications": self._extract_certifications(text),
            "summary": self._extract_summary(text),
            "total_years_experience": 0,
            "skill_keywords": []
        }
        
        # Calculate total experience
        result["total_years_experience"] = self._calculate_total_experience(
            result["experience"]
        )
        
        # Extract skill keywords
        result["skill_keywords"] = self._extract_skill_keywords(text)
        
        return result
    
    def _extract_text(self, pdf_path: Path) -> str:
        """Extract all text from PDF."""
        text = ""
        
        try:
            with fitz.open(pdf_path) as doc:
                for page in doc:
                    text += page.get_text()
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {e}")
        
        return text
    
    def _extract_contact(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information."""
        contact = {
            "name": None,
            "email": None,
            "phone": None,
            "linkedin": None,
            "github": None,
            "location": None
        }
        
        # Extract email
        email_match = re.search(self.EMAIL_PATTERN, text)
        if email_match:
            contact["email"] = email_match.group()
        
        # Extract phone
        phone_match = re.search(self.PHONE_PATTERN, text)
        if phone_match:
            phone = phone_match.group()
            # Clean up phone number
            if len(re.sub(r"\D", "", phone)) >= 10:
                contact["phone"] = phone
        
        # Extract LinkedIn
        linkedin_match = re.search(r"linkedin\.com/in/([a-zA-Z0-9-]+)", text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = f"https://linkedin.com/in/{linkedin_match.group(1)}"
        
        # Extract GitHub
        github_match = re.search(r"github\.com/([a-zA-Z0-9-]+)", text, re.IGNORECASE)
        if github_match:
            contact["github"] = f"https://github.com/{github_match.group(1)}"
        
        # Try to extract name (usually first non-empty line)
        lines = text.strip().split("\n")
        for line in lines[:5]:
            line = line.strip()
            # Skip lines that look like contact info
            if line and not re.search(r"[@|www\.|http|\.com]", line):
                if len(line.split()) <= 4:  # Name is usually 2-4 words
                    contact["name"] = line
                    break
        
        return contact
    
    def _extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience entries."""
        experiences = []
        
        # Find experience section
        exp_section = self._extract_section(text, "experience")
        if not exp_section:
            return experiences
        
        # Split by potential job entries (look for date ranges)
        for pattern in self.DATE_PATTERNS:
            matches = list(re.finditer(pattern, exp_section, re.IGNORECASE))
            
            if matches:
                for i, match in enumerate(matches):
                    # Get text around each date match
                    start = max(0, match.start() - 200)
                    end = matches[i + 1].start() if i + 1 < len(matches) else match.end() + 500
                    
                    entry_text = exp_section[start:end]
                    
                    experience = {
                        "raw_text": entry_text[:300],
                        "dates": {
                            "start": match.group(1),
                            "end": match.group(2)
                        },
                        "duration_months": self._calculate_duration(
                            match.group(1), match.group(2)
                        ),
                        "title": None,
                        "company": None
                    }
                    
                    experiences.append(experience)
                
                break  # Stop after first matching pattern
        
        return experiences[:10]  # Limit to 10 entries
    
    def _extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education entries."""
        education = []
        
        edu_section = self._extract_section(text, "education")
        if not edu_section:
            return education
        
        # Common degree patterns
        degree_patterns = [
            r"(?i)(bachelor|master|phd|doctor|associate|b\.s\.|m\.s\.|b\.a\.|m\.a\.|mba)",
            r"(?i)(computer science|engineering|business|data science|information technology)"
        ]
        
        for pattern in degree_patterns:
            matches = re.findall(pattern, edu_section)
            for match in matches:
                education.append({
                    "degree_mention": match,
                    "section_text": edu_section[:500]
                })
        
        return education
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from skills section."""
        skills_section = self._extract_section(text, "skills")
        if not skills_section:
            return []
        
        # Split by common delimiters
        skills = re.split(r"[,|•|\n|;]", skills_section)
        
        # Clean up
        cleaned = []
        for skill in skills:
            skill = skill.strip()
            if skill and len(skill) > 1 and len(skill) < 50:
                cleaned.append(skill)
        
        return cleaned[:30]  # Limit to 30 skills
    
    def _extract_certifications(self, text: str) -> List[str]:
        """Extract certifications."""
        cert_section = self._extract_section(text, "certifications")
        if not cert_section:
            return []
        
        # Split by lines or bullets
        certs = re.split(r"[\n•]", cert_section)
        
        cleaned = []
        for cert in certs:
            cert = cert.strip()
            if cert and len(cert) > 5:
                cleaned.append(cert)
        
        return cleaned[:10]
    
    def _extract_summary(self, text: str) -> Optional[str]:
        """Extract summary/objective section."""
        summary = self._extract_section(text, "summary")
        if summary:
            return summary[:1000]  # Limit length
        return None
    
    def _extract_section(self, text: str, section_name: str) -> Optional[str]:
        """Extract a specific section from the resume."""
        pattern = self.SECTION_PATTERNS.get(section_name)
        if not pattern:
            return None
        
        # Find section header
        match = re.search(pattern, text)
        if not match:
            return None
        
        start = match.end()
        
        # Find next section header
        all_patterns = "|".join(self.SECTION_PATTERNS.values())
        next_section = re.search(all_patterns, text[start:])
        
        if next_section:
            end = start + next_section.start()
        else:
            end = min(start + 2000, len(text))  # Default section length
        
        return text[start:end].strip()
    
    def _extract_skill_keywords(self, text: str) -> List[Dict[str, Any]]:
        """Extract known technology keywords from entire resume."""
        keywords = []
        text_lower = text.lower()
        
        for keyword in self.TECH_KEYWORDS:
            # Use word boundaries for accurate matching
            pattern = r"\b" + re.escape(keyword) + r"\b"
            matches = re.findall(pattern, text_lower)
            
            if matches:
                keywords.append({
                    "keyword": keyword,
                    "count": len(matches)
                })
        
        # Sort by count
        keywords.sort(key=lambda x: x["count"], reverse=True)
        
        return keywords
    
    def _calculate_duration(self, start: str, end: str) -> int:
        """Calculate duration in months between two dates."""
        try:
            # Parse start date
            start_date = self._parse_date(start)
            
            # Parse end date
            if end.lower() in ["present", "current", "now"]:
                end_date = datetime.now()
            else:
                end_date = self._parse_date(end)
            
            # Calculate months
            months = (end_date.year - start_date.year) * 12
            months += (end_date.month - start_date.month)
            
            return max(0, months)
            
        except Exception:
            return 0
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats."""
        date_str = date_str.strip()
        
        # Try different formats
        formats = [
            "%B %Y",      # January 2024
            "%b %Y",      # Jan 2024
            "%m/%Y",      # 01/2024
            "%Y"          # 2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Default to current date if parsing fails
        return datetime.now()
    
    def _calculate_total_experience(self, experiences: List[Dict]) -> float:
        """Calculate total years of experience."""
        total_months = sum(exp.get("duration_months", 0) for exp in experiences)
        return round(total_months / 12, 1)


# Test function
def test_parser():
    """Test the resume parser with a sample PDF."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <path_to_resume.pdf>")
        return
    
    parser = ResumeParser()
    result = parser.parse(sys.argv[1])
    
    import json
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    test_parser()
