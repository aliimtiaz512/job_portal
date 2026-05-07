"""
Standalone entry point for the scraper.
FastAPI launches this as a subprocess via subprocess.Popen so Chrome always
runs in a fresh Python interpreter with no inherited uvicorn threads.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from scraper import run_scraper

if __name__ == "__main__":
    keyword     = sys.argv[1] if len(sys.argv) > 1 else "AI ML"
    date_posted = sys.argv[2] if len(sys.argv) > 2 else ""
    salary      = sys.argv[3] if len(sys.argv) > 3 else ""
    run_scraper(keyword, date_posted, salary)
