"""
Standalone entry point for the LinkedIn scraper.
FastAPI launches this as a subprocess via subprocess.Popen so Chrome always
runs in a fresh Python interpreter with no inherited uvicorn threads.
"""
import sys
import os

# Add backend/ to path so models and other modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.linkedin import run_scraper

if __name__ == "__main__":
    keyword     = sys.argv[1] if len(sys.argv) > 1 else "AI ML"
    date_posted = sys.argv[2] if len(sys.argv) > 2 else ""
    salary      = sys.argv[3] if len(sys.argv) > 3 else ""
    run_scraper(keyword, date_posted, salary)
