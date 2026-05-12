"""
Standalone entry point for the Adzuna API scraper.
FastAPI launches this as a subprocess via subprocess.Popen.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.adzuna import run_adzuna_scraper

if __name__ == "__main__":
    keyword       = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    location      = sys.argv[2] if len(sys.argv) > 2 else ""
    max_days_old  = sys.argv[3] if len(sys.argv) > 3 else ""
    contract_type = sys.argv[4] if len(sys.argv) > 4 else ""
    run_adzuna_scraper(keyword, location, max_days_old, contract_type)
