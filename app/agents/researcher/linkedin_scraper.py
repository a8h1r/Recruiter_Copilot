"""
LinkedIn Scraper - The Researcher Agent

This module uses Playwright with manual cookie injection to scrape LinkedIn profiles.
LinkedIn has aggressive anti-bot measures, so this scraper:
1. Requires manual login cookies from an active session
2. Uses stealth techniques to avoid detection
3. Falls back gracefully if blocked

IMPORTANT: LinkedIn scraping may violate their ToS. Use responsibly.

Author: Recruiter Copilot
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page


class LinkedInScraper:
    """
    Playwright-based LinkedIn profile scraper with cookie injection.
    
    Requires cookies from an authenticated LinkedIn session.
    """
    
    COOKIES_FILE = Path(__file__).parent.parent.parent.parent / "linkedin_cookies.json"
    
    def __init__(self, headless: bool = True, slow_mo: int = 100):
        """
        Initialize the LinkedIn scraper.
        
        Args:
            headless: Run browser in headless mode
            slow_mo: Slow down operations by milliseconds
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
        self.cookies_loaded = False
    
    async def scrape(self, linkedin_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a LinkedIn profile.
        
        Args:
            linkedin_url: Full LinkedIn profile URL
        
        Returns:
            Dictionary with profile data or None if blocked/failed
        """
        if not self._cookies_exist():
            print("LinkedIn cookies not found. Please export cookies first.")
            print(f"Expected location: {self.COOKIES_FILE}")
            return self._get_fallback_response(linkedin_url)
        
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            
            try:
                context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                
                # Load cookies
                await self._load_cookies(context)
                
                page = await context.new_page()
                
                # Navigate to profile
                await page.goto(linkedin_url, wait_until="networkidle", timeout=30000)
                
                # Check if we're logged in and can see the profile
                if await self._is_blocked(page):
                    print("LinkedIn blocked access or session expired.")
                    return self._get_fallback_response(linkedin_url)
                
                # Extract profile data
                data = await self._extract_profile_data(page)
                data["linkedin_url"] = linkedin_url
                data["scraped_at"] = datetime.utcnow().isoformat()
                
                return data
                
            except Exception as e:
                print(f"LinkedIn scraping failed: {e}")
                return self._get_fallback_response(linkedin_url)
            finally:
                await self.browser.close()
    
    def _cookies_exist(self) -> bool:
        """Check if cookies file exists."""
        return self.COOKIES_FILE.exists()
    
    async def _load_cookies(self, context) -> None:
        """Load cookies from file into browser context."""
        try:
            with open(self.COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            
            # Format cookies for Playwright
            formatted_cookies = []
            for cookie in cookies:
                formatted = {
                    "name": cookie.get("name"),
                    "value": cookie.get("value"),
                    "domain": cookie.get("domain", ".linkedin.com"),
                    "path": cookie.get("path", "/"),
                }
                if cookie.get("expires"):
                    formatted["expires"] = cookie["expires"]
                formatted_cookies.append(formatted)
            
            await context.add_cookies(formatted_cookies)
            self.cookies_loaded = True
            
        except Exception as e:
            print(f"Failed to load cookies: {e}")
    
    async def _is_blocked(self, page: Page) -> bool:
        """Check if we're blocked or logged out."""
        # Check for login wall
        login_form = await page.query_selector("form.login-form")
        if login_form:
            return True
        
        # Check for auth wall
        auth_wall = await page.query_selector("div.authwall-join-form")
        if auth_wall:
            return True
        
        # Check for challenge page
        challenge = await page.query_selector("div#captcha-challenge")
        if challenge:
            return True
        
        return False
    
    async def _extract_profile_data(self, page: Page) -> Dict[str, Any]:
        """Extract all available profile data."""
        data = {
            "name": None,
            "headline": None,
            "location": None,
            "about": None,
            "experience": [],
            "education": [],
            "skills": [],
            "certifications": []
        }
        
        try:
            # Name
            name_elem = await page.query_selector("h1.text-heading-xlarge")
            if name_elem:
                data["name"] = await name_elem.inner_text()
            
            # Headline
            headline_elem = await page.query_selector("div.text-body-medium")
            if headline_elem:
                data["headline"] = await headline_elem.inner_text()
            
            # Location
            location_elem = await page.query_selector("span.text-body-small.inline")
            if location_elem:
                data["location"] = await location_elem.inner_text()
            
            # About section
            about_section = await page.query_selector("section.pv-about-section")
            if about_section:
                about_text = await about_section.query_selector("div.inline-show-more-text")
                if about_text:
                    data["about"] = await about_text.inner_text()
            
            # Experience
            data["experience"] = await self._extract_experience(page)
            
            # Education
            data["education"] = await self._extract_education(page)
            
            # Skills
            data["skills"] = await self._extract_skills(page)
            
        except Exception as e:
            print(f"Error extracting LinkedIn data: {e}")
        
        return data
    
    async def _extract_experience(self, page: Page) -> List[Dict[str, Any]]:
        """Extract work experience."""
        experiences = []
        
        try:
            exp_section = await page.query_selector("section#experience")
            if not exp_section:
                return experiences
            
            exp_items = await exp_section.query_selector_all("li.artdeco-list__item")
            
            for item in exp_items[:5]:  # Limit to 5 most recent
                exp = {}
                
                # Title
                title_elem = await item.query_selector("span[aria-hidden='true']")
                if title_elem:
                    exp["title"] = await title_elem.inner_text()
                
                # Company
                company_elem = await item.query_selector("span.t-14.t-normal")
                if company_elem:
                    exp["company"] = await company_elem.inner_text()
                
                # Duration
                duration_elem = await item.query_selector("span.t-14.t-normal.t-black--light")
                if duration_elem:
                    exp["duration"] = await duration_elem.inner_text()
                
                if exp.get("title"):
                    experiences.append(exp)
                    
        except Exception as e:
            print(f"Error extracting experience: {e}")
        
        return experiences
    
    async def _extract_education(self, page: Page) -> List[Dict[str, Any]]:
        """Extract education history."""
        education = []
        
        try:
            edu_section = await page.query_selector("section#education")
            if not edu_section:
                return education
            
            edu_items = await edu_section.query_selector_all("li.artdeco-list__item")
            
            for item in edu_items[:3]:
                edu = {}
                
                # School
                school_elem = await item.query_selector("span[aria-hidden='true']")
                if school_elem:
                    edu["school"] = await school_elem.inner_text()
                
                # Degree
                degree_elem = await item.query_selector("span.t-14.t-normal")
                if degree_elem:
                    edu["degree"] = await degree_elem.inner_text()
                
                if edu.get("school"):
                    education.append(edu)
                    
        except Exception as e:
            print(f"Error extracting education: {e}")
        
        return education
    
    async def _extract_skills(self, page: Page) -> List[str]:
        """Extract skills list."""
        skills = []
        
        try:
            skills_section = await page.query_selector("section#skills")
            if not skills_section:
                return skills
            
            skill_items = await skills_section.query_selector_all("span[aria-hidden='true']")
            
            for item in skill_items[:20]:  # Limit to 20 skills
                skill_text = await item.inner_text()
                if skill_text and len(skill_text) < 50:  # Filter out non-skill text
                    skills.append(skill_text.strip())
                    
        except Exception as e:
            print(f"Error extracting skills: {e}")
        
        return list(set(skills))  # Remove duplicates
    
    def _get_fallback_response(self, linkedin_url: str) -> Dict[str, Any]:
        """Return a fallback response when scraping fails."""
        return {
            "linkedin_url": linkedin_url,
            "status": "scraping_failed",
            "message": "LinkedIn scraping was blocked or cookies expired. Please update cookies or skip LinkedIn analysis.",
            "scraped_at": datetime.utcnow().isoformat()
        }
    
    @classmethod
    def export_cookies_instructions(cls) -> str:
        """Return instructions for exporting LinkedIn cookies."""
        return """
        To export LinkedIn cookies:
        
        1. Install a browser extension like "EditThisCookie" or "Cookie Editor"
        2. Log into LinkedIn in your browser
        3. Click the cookie extension and export cookies as JSON
        4. Save the JSON file to: {path}
        
        Required cookies:
        - li_at (session cookie)
        - JSESSIONID
        - bcookie
        
        The cookies will expire after some time and need to be refreshed.
        """.format(path=cls.COOKIES_FILE)


if __name__ == "__main__":
    print(LinkedInScraper.export_cookies_instructions())
