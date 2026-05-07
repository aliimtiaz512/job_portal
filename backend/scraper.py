# Backward-compatibility shim — LinkedIn scraper logic lives in scrapers/linkedin.py.
# app.py and run_scraper.py import from this module; the re-export keeps them working.
from scrapers.linkedin import (  # noqa: F401
    STATUS_FILE,
    scraper_status,
    run_scraper,
    build_driver,
    linkedin_login,
    navigate_to_jobs,
    collect_job_cards,
    save_job,
    save_scraper_run,
    human_delay,
)
