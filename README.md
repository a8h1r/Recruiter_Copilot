# Recruiter Copilot

An autonomous agentic recruitment engine that analyzes candidates through Resume (PDF), LinkedIn URL, and GitHub URL to generate a structured 1-10 "Technical Alignment Score" based on a provided Job Description.

## 🚀 Features

- **The Researcher**: Scrapes GitHub/LinkedIn for real activity data
- **The Analyst**: Cross-validates resume claims against online presence
- **The Architect**: Generates structured scoring reports

## 📦 Installation

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## 🔧 Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./recruiter_copilot.db
```

## 🏃 Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/candidates/analyze` | POST | Submit candidate for analysis |
| `/api/candidates/{id}/report` | GET | Get generated report |
| `/api/candidates/{id}/status` | GET | Check analysis status |
| `/health` | GET | Health check |

## 📁 Project Structure

```
recruiter-copilot/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # SQLite models
│   ├── agents/
│   │   ├── researcher/      # GitHub/LinkedIn scrapers
│   │   ├── analyst/         # Resume parser & validator
│   │   └── architect/       # Report generator & scorer
│   └── routers/             # API endpoints
├── reports/                  # Generated candidate reports
└── requirements.txt
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Test with visible browser
pytest tests/test_github_scraper.py --headed
```
