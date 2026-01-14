"""
Configuration settings for Recruiter Copilot.
Loads environment variables and provides typed configuration.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./recruiter_copilot.db")
    
    # Testing
    test_github_username: str = os.getenv("TEST_GITHUB_USERNAME", "SagnikSaha01")
    
    # Application
    app_name: str = "Recruiter Copilot"
    debug: bool = True
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent
    reports_dir: Path = base_dir / "reports"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


# Global settings instance
settings = Settings()

# Ensure reports directory exists
settings.reports_dir.mkdir(exist_ok=True)
