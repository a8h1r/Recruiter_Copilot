"""
Standalone GitHub Scraper Test - No module dependencies
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout


class GitHubScraper:
    """Playwright-based GitHub profile scraper."""
    
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser: Optional[Browser] = None
    
    async def scrape(self, github_url: str) -> Dict[str, Any]:
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo
            )
            
            try:
                page = await self.browser.new_page()
                await page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                
                username = self._extract_username(github_url)
                await page.goto(f"https://github.com/{username}", wait_until="networkidle")
                
                if await page.query_selector("img[alt='404']"):
                    raise ValueError(f"GitHub profile not found: {username}")
                
                profile_data = await self._scrape_profile_overview(page, username)
                contribution_data = await self._scrape_contributions(page, username)
                language_data = await self._scrape_languages(page, username)
                pinned_repos = await self._scrape_pinned_repos(page)
                readme_score = await self._analyze_readme_complexity(page, username, pinned_repos)
                
                result = {
                    "username": username,
                    "scraped_at": datetime.utcnow().isoformat(),
                    **profile_data,
                    **contribution_data,
                    "top_languages": language_data[:3],
                    "all_languages": language_data,
                    "readme_complexity_score": readme_score,
                    "pinned_repos": pinned_repos
                }
                
                return result
                
            finally:
                await self.browser.close()
    
    def _extract_username(self, github_url: str) -> str:
        url = github_url.strip().rstrip("/")
        url = re.sub(r"^https?://", "", url)
        url = re.sub(r"^www\.", "", url)
        if url.startswith("github.com/"):
            parts = url.replace("github.com/", "").split("/")
            return parts[0]
        return url
    
    async def _scrape_profile_overview(self, page: Page, username: str) -> Dict[str, Any]:
        data = {"name": None, "bio": None, "location": None, "company": None, 
                "public_repos": 0, "followers": 0, "following": 0}
        
        try:
            name_elem = await page.query_selector("span.p-name")
            if name_elem:
                data["name"] = await name_elem.inner_text()
            
            bio_elem = await page.query_selector("div.p-note")
            if bio_elem:
                data["bio"] = await bio_elem.inner_text()
            
            nav_items = await page.query_selector_all("a.UnderlineNav-item")
            for item in nav_items:
                text = await item.inner_text()
                if "Repositories" in text:
                    match = re.search(r"(\d+)", text)
                    if match:
                        data["public_repos"] = int(match.group(1))
            
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
        data = {"commits_12_months": 0, "contribution_streak": 0}
        
        try:
            contrib_elem = await page.query_selector("h2.f4.text-normal.mb-2")
            if contrib_elem:
                text = await contrib_elem.inner_text()
                match = re.search(r"([\d,]+)\s+contributions?", text)
                if match:
                    data["commits_12_months"] = int(match.group(1).replace(",", ""))
            
            cells = await page.query_selector_all("td.ContributionCalendar-day")
            streak = 0
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
        languages = []
        
        try:
            await page.goto(f"https://github.com/{username}?tab=repositories", wait_until="networkidle")
            
            language_counts = {}
            repo_items = await page.query_selector_all("li[itemprop='owns']")
            
            for repo in repo_items:
                lang_elem = await repo.query_selector("[itemprop='programmingLanguage']")
                if lang_elem:
                    lang = await lang_elem.inner_text()
                    language_counts[lang] = language_counts.get(lang, 0) + 1
            
            sorted_langs = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
            total_repos = sum(count for _, count in sorted_langs)
            
            for lang, count in sorted_langs:
                percentage = round((count / total_repos) * 100, 1) if total_repos > 0 else 0
                languages.append({"name": lang, "repo_count": count, "percentage": percentage})
            
            await page.goto(f"https://github.com/{username}", wait_until="networkidle")
            
        except Exception as e:
            print(f"Warning: Error scraping languages: {e}")
        
        return languages
    
    async def _scrape_pinned_repos(self, page: Page) -> List[Dict[str, Any]]:
        pinned = []
        
        try:
            pinned_items = await page.query_selector_all("div.pinned-item-list-item-content")
            
            for item in pinned_items:
                repo_data = {}
                
                name_elem = await item.query_selector("span.repo")
                if name_elem:
                    repo_data["name"] = await name_elem.inner_text()
                
                desc_elem = await item.query_selector("p.pinned-item-desc")
                if desc_elem:
                    repo_data["description"] = await desc_elem.inner_text()
                
                lang_elem = await item.query_selector("[itemprop='programmingLanguage']")
                if lang_elem:
                    repo_data["language"] = await lang_elem.inner_text()
                
                if repo_data.get("name"):
                    pinned.append(repo_data)
                    
        except Exception as e:
            print(f"Warning: Error scraping pinned repos: {e}")
        
        return pinned
    
    async def _analyze_readme_complexity(self, page: Page, username: str, pinned_repos: List[Dict]) -> float:
        if not pinned_repos:
            return 5.0
        
        total_score = 0
        repos_analyzed = 0
        
        try:
            for repo in pinned_repos[:2]:
                repo_name = repo.get("name")
                if not repo_name:
                    continue
                
                try:
                    await page.goto(f"https://github.com/{username}/{repo_name}", 
                                  wait_until="networkidle", timeout=10000)
                    
                    readme_score = 0
                    readme_elem = await page.query_selector("article.markdown-body")
                    
                    if readme_elem:
                        readme_score += 2
                        readme_text = await readme_elem.inner_text()
                        
                        if len(readme_text) > 500:
                            readme_score += 2
                        
                        images = await readme_elem.query_selector_all("img")
                        if len(images) > 0:
                            readme_score += 2
                        
                        code_blocks = await readme_elem.query_selector_all("pre")
                        if len(code_blocks) > 0:
                            readme_score += 2
                        
                        readme_lower = readme_text.lower()
                        if any(s in readme_lower for s in ["installation", "usage", "getting started"]):
                            readme_score += 2
                    
                    total_score += min(readme_score, 10)
                    repos_analyzed += 1
                    
                except PlaywrightTimeout:
                    continue
            
            await page.goto(f"https://github.com/{username}", wait_until="networkidle")
            
        except Exception as e:
            print(f"Warning: Error in README analysis: {e}")
        
        return round(total_score / repos_analyzed, 1) if repos_analyzed > 0 else 5.0
    
    def _parse_count(self, text: str) -> int:
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


async def main():
    print("=" * 60)
    print("🔍 Recruiter Copilot - GitHub Scraper Test")
    print("=" * 60)
    print()
    print("Target: https://github.com/SagnikSaha01")
    print()
    
    scraper = GitHubScraper(headless=True, slow_mo=100)
    
    print("🚀 Starting scraper...")
    result = await scraper.scrape("https://github.com/SagnikSaha01")
    
    print()
    print("✅ Scraping Complete!")
    print("=" * 60)
    print()
    
    print(f"👤 Username: {result.get('username')}")
    print(f"📛 Name: {result.get('name')}")
    print(f"📊 Commits (12 months): {result.get('commits_12_months', 0)}")
    print(f"📁 Public Repos: {result.get('public_repos', 0)}")
    print(f"👥 Followers: {result.get('followers', 0)}")
    
    print()
    print("🔥 Top Languages:")
    for i, lang in enumerate(result.get('top_languages', [])[:3], 1):
        print(f"   {i}. {lang['name']} ({lang.get('percentage', 0)}%)")
    
    print()
    print(f"📖 README Quality Score: {result.get('readme_complexity_score', 0)}/10")
    print(f"🔥 Contribution Streak: {result.get('contribution_streak', 0)} days")
    
    if result.get('pinned_repos'):
        print()
        print("📌 Pinned Repositories:")
        for repo in result.get('pinned_repos', [])[:3]:
            desc = repo.get('description', 'No description')
            if desc and len(desc) > 50:
                desc = desc[:50] + "..."
            print(f"   - {repo.get('name')}: {desc}")
    
    # Save result
    import os
    os.makedirs("reports", exist_ok=True)
    with open("reports/github_scrape_result.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print()
    print("💾 Full result saved to: reports/github_scrape_result.json")
    print()
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
