"""
Standalone entry point for the Indeed scraper.
FastAPI launches this as a subprocess via subprocess.Popen.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.indeed import run_indeed_scraper

if __name__ == "__main__":
    keyword     = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    pay         = sys.argv[2] if len(sys.argv) > 2 else ""
    job_type    = sys.argv[3] if len(sys.argv) > 3 else ""
    date_posted = sys.argv[4] if len(sys.argv) > 4 else ""
    run_indeed_scraper(keyword, pay, job_type, date_posted)
