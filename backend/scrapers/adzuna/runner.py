"""
Standalone entry point for the Adzuna API scraper.
FastAPI launches this as a subprocess via subprocess.Popen.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.adzuna import run_adzuna_scraper

if __name__ == "__main__":
    keyword      = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    max_days_old = sys.argv[2] if len(sys.argv) > 2 else ""
    run_adzuna_scraper(keyword, max_days_old)
