"""
Agents package - Contains all AI agents for the Recruiter Copilot.

Modules:
- github_scraper: Playwright-based GitHub profile scraper
- linkedin_scraper: LinkedIn profile scraper with cookie injection
- resume_analyzer: Modular resume analysis with multiple strategies
- researcher/: Research subpackage (deprecated location)
- analyst/: Analysis subpackage (resume parser, validator, gemini client)
- architect/: Report generation subpackage (scorer, report generator)
"""
from .github_scraper import GitHubScraper
from .linkedin_scraper import LinkedInScraper
from .resume_analyzer import ResumeAnalyzer

__all__ = [
    "GitHubScraper",
    "LinkedInScraper",
    "ResumeAnalyzer"
]
