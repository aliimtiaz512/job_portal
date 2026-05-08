"""
Standalone entry point for the startup.jobs scraper.
FastAPI launches this as a subprocess via subprocess.Popen.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.startupjobs import run_startupjobs_scraper

if __name__ == "__main__":
    keyword     = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    job_type    = sys.argv[2] if len(sys.argv) > 2 else ""
    salary      = sys.argv[3] if len(sys.argv) > 3 else ""
    time_filter = sys.argv[4] if len(sys.argv) > 4 else ""
    run_startupjobs_scraper(keyword, job_type, salary, time_filter)
