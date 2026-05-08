"""
Standalone entry point for the Dice scraper.
FastAPI launches this as a subprocess via subprocess.Popen.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from scrapers.dice import run_dice_scraper

if __name__ == "__main__":
    keyword         = sys.argv[1] if len(sys.argv) > 1 else "Software Engineer"
    date_posted     = sys.argv[2] if len(sys.argv) > 2 else ""
    employment_type = sys.argv[3] if len(sys.argv) > 3 else ""
    run_dice_scraper(keyword, date_posted, employment_type)
