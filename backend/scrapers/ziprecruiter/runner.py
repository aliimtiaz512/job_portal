"""
Standalone entry point for the ZipRecruiter scraper.
FastAPI launches this as a subprocess via subprocess.Popen.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.ziprecruiter import run_ziprecruiter_scraper

if __name__ == "__main__":
    keyword          = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    date_posted      = sys.argv[2] if len(sys.argv) > 2 else ""
    salary_min       = sys.argv[3] if len(sys.argv) > 3 else ""
    employment_type  = sys.argv[4] if len(sys.argv) > 4 else ""
    experience      = sys.argv[5] if len(sys.argv) > 5 else ""
    run_ziprecruiter_scraper(keyword, date_posted, salary_min, employment_type, experience)