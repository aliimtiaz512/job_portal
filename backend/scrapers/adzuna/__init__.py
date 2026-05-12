import json
import os
import time
import datetime
import logging
import requests
from dotenv import load_dotenv

from models import AdzunaJob, ScraperRun, Session, init_db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATUS_FILE = "/tmp/scraper_status_adzuna.json"

RESULTS_PER_PAGE = 50
MAX_PAGES = 20  # 20 × 50 = up to 1 000 results

scraper_status = {
    "running": False,
    "progress": "",
    "total": 0,
    "scraped": 0,
    "errors": [],
    "done": False,
    "elapsed_seconds": 0,
    "daily_runs": 0,
    "daily_date": "",
}

_start_time: float = 0.0


def _sync_status() -> None:
    if _start_time > 0:
        scraper_status["elapsed_seconds"] = int(time.time() - _start_time)
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(scraper_status, f)
    except Exception:
        pass


def _save_adzuna_job(data: dict) -> bool:
    session = Session()
    try:
        if session.query(AdzunaJob).filter_by(job_url=data["job_url"]).first():
            return False
        session.add(AdzunaJob(**data))
        session.commit()
        logger.info(f"Saved: {data['job_title']} @ {data['company_name']}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"DB error: {e}")
        return False
    finally:
        session.close()


def _save_scraper_run(
    keyword: str,
    started_at: str,
    pages_scraped: int,
    jobs_found: int,
    jobs_saved: int,
    error_count: int,
    run_status: str,
) -> None:
    session = Session()
    try:
        finished_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        duration = int(time.time() - _start_time)
        session.add(ScraperRun(
            keyword=keyword,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration,
            pages_scraped=pages_scraped,
            jobs_found=jobs_found,
            jobs_saved=jobs_saved,
            error_count=error_count,
            run_status=run_status,
            scraper="adzuna",
        ))
        session.commit()
        logger.info(f"Run record saved: {run_status}, {jobs_saved} jobs in {duration}s")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save run record: {e}")
    finally:
        session.close()


def run_adzuna_scraper(
    keyword: str = "Software Engineer",
    location: str = "",
    max_days_old: str = "",
    contract_type: str = "",
) -> None:
    global _start_time
    _start_time = time.time()

    today = datetime.date.today().isoformat()
    try:
        with open(STATUS_FILE) as f:
            prev = json.load(f)
        daily_runs = (prev.get("daily_runs", 0) + 1) if prev.get("daily_date") == today else 1
    except Exception:
        daily_runs = 1

    scraper_status.update({
        "running": True, "progress": "Starting Adzuna API fetch...",
        "total": 0, "scraped": 0, "errors": [], "done": False,
        "elapsed_seconds": 0,
        "daily_runs": daily_runs,
        "daily_date": today,
    })
    _sync_status()

    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")

    if not app_id or not app_key or app_id == "your_adzuna_app_id_here":
        scraper_status["progress"] = "Error: ADZUNA_APP_ID / ADZUNA_APP_KEY not configured in .env"
        scraper_status["errors"].append("Missing Adzuna API credentials.")
        scraper_status["running"] = False
        scraper_status["done"] = True
        _sync_status()
        return

    started_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    init_db()

    pages_scraped = 0
    jobs_found = 0
    jobs_saved = 0
    run_failed = False
    all_jobs: list[dict] = []

    try:
        for page in range(1, MAX_PAGES + 1):
            scraper_status["progress"] = f"Fetching Adzuna page {page}..."
            _sync_status()

            params: dict = {
                "app_id": app_id,
                "app_key": app_key,
                "what": keyword,
                "results_per_page": RESULTS_PER_PAGE,
            }
            if location:
                params["where"] = location
            if max_days_old:
                params["max_days_old"] = max_days_old
            if contract_type:
                params["contract_type"] = contract_type

            try:
                resp = requests.get(
                    f"https://api.adzuna.com/v1/api/jobs/us/search/{page}",
                    params=params,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                err_msg = f"Page {page} request failed: {e}"
                scraper_status["errors"].append(err_msg)
                logger.error(err_msg)
                run_failed = True
                break

            results = data.get("results", [])
            total_count = data.get("count", 0)

            if page == 1:
                scraper_status["total"] = total_count
                _sync_status()

            if not results:
                logger.info(f"Page {page}: no results — stopping pagination.")
                break

            for job in results:
                title = job.get("title", "").strip()
                company = (job.get("company") or {}).get("display_name", "").strip()
                url = job.get("redirect_url", "").strip()
                if not title or not url:
                    continue
                all_jobs.append({
                    "job_title": title,
                    "company_name": company or "N/A",
                    "job_url": url,
                })

            jobs_found = len(all_jobs)
            pages_scraped = page
            logger.info(f"Page {page}: +{len(results)} results | cumulative: {jobs_found}")

            if len(results) < RESULTS_PER_PAGE:
                logger.info("Last page reached (partial results).")
                break

        if not all_jobs:
            scraper_status["progress"] = "No jobs found. Try a different keyword or filters."
        else:
            for i, job_data in enumerate(all_jobs, 1):
                scraper_status["progress"] = f"Saving job {i}/{len(all_jobs)}..."
                try:
                    if _save_adzuna_job(job_data):
                        jobs_saved += 1
                        scraper_status["scraped"] = jobs_saved
                except Exception as e:
                    scraper_status["errors"].append(str(e))
                _sync_status()

            scraper_status["progress"] = f"Done! Saved {jobs_saved} Adzuna jobs."

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        scraper_status["progress"] = f"Error: {e}"
        scraper_status["errors"].append(str(e))
        run_failed = True
    finally:
        error_count = len(scraper_status["errors"])
        if run_failed:
            final_status = "failed"
        elif error_count > 0:
            final_status = "partial"
        else:
            final_status = "success"

        _save_scraper_run(
            keyword=keyword,
            started_at=started_at,
            pages_scraped=pages_scraped,
            jobs_found=jobs_found,
            jobs_saved=jobs_saved,
            error_count=error_count,
            run_status=final_status,
        )

        scraper_status["running"] = False
        scraper_status["done"] = True
        _sync_status()
