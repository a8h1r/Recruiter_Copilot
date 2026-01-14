"""
GitHub Scraper - The Researcher Agent

This module uses Playwright to navigate to a GitHub profile and extract:
1. Commit history from the last 12 months (contribution graph)
2. Top 3 most used programming languages
3. README complexity analysis from pinned/popular repositories
4. Repository statistics (stars, forks, activity)

Author: Recruiter Copilot
"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout


class GitHubScraper:
    """
    Playwright-based GitHub profile scraper.
    
    Extracts comprehensive developer activity data from public GitHub profiles.
    """
    
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        """
        Initialize the GitHub scraper.
        
        Args:
            headless: Run browser in headless mode (default True)
            slow_mo: Slow down operations by specified milliseconds (for debugging)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
    
    async def scrape(self, github_url: str) -> Dict[str, Any]:
        """
        Scrape a GitHub profile and extract developer data.
        
        Args:
            github_url: Full GitHub profile URL (e.g., https://github.com/username)
        
        Returns:
            Dictionary containing:
            - username: GitHub username
            - commits_12_months: Total contributions in last 12 months
            - top_languages: List of top 3 languages
            - readme_complexity_score: 0-10 score based on README quality
            - public_repos: Number of public repositories
            - followers: Follower count
            - following: Following count
            - contribution_streak: Current contribution streak
            - pinned_repos: List of pinned repository data
            - recent_activity: Recent commit/PR activity
        """
        async with async_playwright() as p:
            # Launch browser
            self.browser = await p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            
            try:
                page = await self.browser.new_page()
                
                # Set a realistic user agent
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                
                # Extract username from URL
                username = self._extract_username(github_url)
                
                # Navigate to profile
                await page.goto(f"https://github.com/{username}", wait_until="networkidle")
                
                # Check if profile exists
                if await page.query_selector("img[alt='404']"):
                    raise ValueError(f"GitHub profile not found: {username}")
                
                # Gather all data
                profile_data = await self._scrape_profile_overview(page, username)
                contribution_data = await self._scrape_contributions(page, username)
                language_data = await self._scrape_languages(page, username)
                pinned_repos = await self._scrape_pinned_repos(page)
                readme_score = await self._analyze_readme_complexity(page, username, pinned_repos)
                
                # Combine all data
                result = {
                    "username": username,
                    "scraped_at": datetime.utcnow().isoformat(),
                    **profile_data,
                    **contribution_data,
                    "top_languages": language_data[:3],  # Top 3
                    "all_languages": language_data,
                    "readme_complexity_score": readme_score,
                    "pinned_repos": pinned_repos
                }
                
                return result
                
            finally:
                await self.browser.close()
    
    def _extract_username(self, github_url: str) -> str:
        """Extract username from GitHub URL."""
        # Handle various URL formats
        url = github_url.strip().rstrip("/")
        
        # Remove protocol and www
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        
        # Extract username
        if url.startswith("github.com/"):
            parts = url.replace("github.com/", "").split("/")
            return parts[0]
        
        # Assume it's just the username
        return url
    
    async def _scrape_profile_overview(self, page: Page, username: str) -> Dict[str, Any]:
        """Scrape basic profile information."""
        data = {
            "name": None,
            "bio": None,
            "location": None,
            "company": None,
            "website": None,
            "public_repos": 0,
            "followers": 0,
            "following": 0
        }
        
        try:
            # Name
            name_elem = await page.query_selector("span.p-name")
            if name_elem:
                data["name"] = await name_elem.inner_text()
            
            # Bio
            bio_elem = await page.query_selector("div.p-note")
            if bio_elem:
                data["bio"] = await bio_elem.inner_text()
            
            # Location
            location_elem = await page.query_selector("li[itemprop='homeLocation'] span")
            if location_elem:
                data["location"] = await location_elem.inner_text()
            
            # Company
            company_elem = await page.query_selector("li[itemprop='worksFor'] span")
            if company_elem:
                data["company"] = await company_elem.inner_text()
            
            # Stats (repos, followers, following)
            nav_items = await page.query_selector_all("a.UnderlineNav-item")
            for item in nav_items:
                text = await item.inner_text()
                if "Repositories" in text:
                    match = re.search(r"(\d+)", text)
                    if match:
                        data["public_repos"] = int(match.group(1))
            
            # Followers/Following from the sidebar
            followers_elem = await page.query_selector("a[href$='?tab=followers'] span")
            if followers_elem:
                text = await followers_elem.inner_text()
                data["followers"] = self._parse_count(text)
            
            following_elem = await page.query_selector("a[href$='?tab=following'] span")
            if following_elem:
                text = await following_elem.inner_text()
                data["following"] = self._parse_count(text)
                
        except Exception as e:
            print(f"Warning: Error scraping profile overview: {e}")
        
        return data
    
    async def _scrape_contributions(self, page: Page, username: str) -> Dict[str, Any]:
        """Scrape contribution graph data."""
        data = {
            "commits_12_months": 0,
            "contribution_streak": 0,
            "contributions_by_month": []
        }
        
        try:
            # Look for contribution count text
            contrib_elem = await page.query_selector("h2.f4.text-normal.mb-2")
            if contrib_elem:
                text = await contrib_elem.inner_text()
                match = re.search(r"([\d,]+)\s+contributions?", text)
                if match:
                    data["commits_12_months"] = int(match.group(1).replace(",", ""))
            
            # Get contribution graph cells for streak calculation
            cells = await page.query_selector_all("td.ContributionCalendar-day")
            
            # Calculate current streak
            streak = 0
            today = datetime.now().date()
            
            for cell in reversed(cells):
                level = await cell.get_attribute("data-level")
                if level and int(level) > 0:
                    streak += 1
                else:
                    break
            
            data["contribution_streak"] = streak
            
        except Exception as e:
            print(f"Warning: Error scraping contributions: {e}")
        
        return data
    
    async def _scrape_languages(self, page: Page, username: str) -> List[Dict[str, Any]]:
        """Scrape language statistics from repositories tab."""
        languages = []
        
        try:
            # Navigate to repositories tab
            await page.goto(f"https://github.com/{username}?tab=repositories", wait_until="networkidle")
            
            # Collect languages from all visible repos
            language_counts = {}
            
            repo_items = await page.query_selector_all("li[itemprop='owns']")
            
            for repo in repo_items:
                lang_elem = await repo.query_selector("[itemprop='programmingLanguage']")
                if lang_elem:
                    lang = await lang_elem.inner_text()
                    language_counts[lang] = language_counts.get(lang, 0) + 1
            
            # Sort by count and format
            sorted_langs = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
            total_repos = sum(count for _, count in sorted_langs)
            
            for lang, count in sorted_langs:
                percentage = round((count / total_repos) * 100, 1) if total_repos > 0 else 0
                languages.append({
                    "name": lang,
                    "repo_count": count,
                    "percentage": percentage
                })
            
            # Go back to main profile
            await page.goto(f"https://github.com/{username}", wait_until="networkidle")
            
        except Exception as e:
            print(f"Warning: Error scraping languages: {e}")
        
        return languages
    
    async def _scrape_pinned_repos(self, page: Page) -> List[Dict[str, Any]]:
        """Scrape pinned repository information."""
        pinned = []
        
        try:
            pinned_items = await page.query_selector_all("div.pinned-item-list-item-content")
            
            for item in pinned_items:
                repo_data = {}
                
                # Repo name
                name_elem = await item.query_selector("span.repo")
                if name_elem:
                    repo_data["name"] = await name_elem.inner_text()
                
                # Description
                desc_elem = await item.query_selector("p.pinned-item-desc")
                if desc_elem:
                    repo_data["description"] = await desc_elem.inner_text()
                
                # Language
                lang_elem = await item.query_selector("[itemprop='programmingLanguage']")
                if lang_elem:
                    repo_data["language"] = await lang_elem.inner_text()
                
                # Stars
                star_elem = await item.query_selector("a[href*='/stargazers']")
                if star_elem:
                    text = await star_elem.inner_text()
                    repo_data["stars"] = self._parse_count(text)
                
                # Forks
                fork_elem = await item.query_selector("a[href*='/forks']")
                if fork_elem:
                    text = await fork_elem.inner_text()
                    repo_data["forks"] = self._parse_count(text)
                
                if repo_data.get("name"):
                    pinned.append(repo_data)
                    
        except Exception as e:
            print(f"Warning: Error scraping pinned repos: {e}")
        
        return pinned
    
    async def _analyze_readme_complexity(
        self, 
        page: Page, 
        username: str, 
        pinned_repos: List[Dict]
    ) -> float:
        """
        Analyze README complexity across repositories.
        
        Scoring factors:
        - Has README (2 points)
        - README length > 500 chars (2 points)
        - Has images/badges (2 points)
        - Has code examples (2 points)
        - Has installation/usage sections (2 points)
        
        Returns score 0-10
        """
        total_score = 0
        repos_analyzed = 0
        
        try:
            # Analyze up to 3 pinned repos
            repos_to_check = pinned_repos[:3] if pinned_repos else []
            
            for repo in repos_to_check:
                repo_name = repo.get("name")
                if not repo_name:
                    continue
                
                try:
                    await page.goto(
                        f"https://github.com/{username}/{repo_name}",
                        wait_until="networkidle",
                        timeout=10000
                    )
                    
                    readme_score = 0
                    
                    # Check for README
                    readme_elem = await page.query_selector("article.markdown-body")
                    if readme_elem:
                        readme_score += 2  # Has README
                        
                        readme_text = await readme_elem.inner_text()
                        
                        # Length check
                        if len(readme_text) > 500:
                            readme_score += 2
                        
                        # Check for images
                        images = await readme_elem.query_selector_all("img")
                        if len(images) > 0:
                            readme_score += 2
                        
                        # Check for code blocks
                        code_blocks = await readme_elem.query_selector_all("pre")
                        if len(code_blocks) > 0:
                            readme_score += 2
                        
                        # Check for common sections
                        readme_lower = readme_text.lower()
                        if any(section in readme_lower for section in ["installation", "usage", "getting started", "how to use"]):
                            readme_score += 2
                    
                    total_score += min(readme_score, 10)
                    repos_analyzed += 1
                    
                except PlaywrightTimeout:
                    continue
                except Exception as e:
                    print(f"Warning: Error analyzing README for {repo_name}: {e}")
                    continue
            
            # Navigate back to profile
            await page.goto(f"https://github.com/{username}", wait_until="networkidle")
            
        except Exception as e:
            print(f"Warning: Error in README analysis: {e}")
        
        # Return average score
        if repos_analyzed > 0:
            return round(total_score / repos_analyzed, 1)
        return 0.0
    
    def _parse_count(self, text: str) -> int:
        """Parse count from text like '1.2k' or '500'."""
        if not text:
            return 0
        
        text = text.strip().lower()
        
        try:
            if "k" in text:
                return int(float(text.replace("k", "")) * 1000)
            elif "m" in text:
                return int(float(text.replace("m", "")) * 1000000)
            else:
                return int(re.sub(r"[^\d]", "", text) or 0)
        except ValueError:
            return 0


# Standalone test function
async def test_scraper():
    """Test the GitHub scraper."""
    scraper = GitHubScraper(headless=False, slow_mo=500)
    result = await scraper.scrape("https://github.com/SagnikSaha01")
    
    import json
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(test_scraper())
