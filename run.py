# Windows-compatible server launcher
# Run this instead of: uvicorn app.main:app --reload
# Usage: python run.py

import sys
import asyncio

# CRITICAL: Set Windows event loop policy BEFORE any other imports
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Recruiter Copilot Server...")
    print("📝 Docs: http://localhost:8000/docs")
    print("❤️  Health: http://localhost:8000/health")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=0.5
    )
