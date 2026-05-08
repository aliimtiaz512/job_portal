import re
import json
import time
import random
import logging
import datetime
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from models import StartupJob, ScraperRun, Session, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATUS_FILE = "/tmp/scraper_status_startupjobs.json"

# Maps frontend values → URL query param fragments
_TYPE_PARAMS = {
    "full-time":  "fulltime=true",
    "part-time":  "parttime=true",
    "contractor": "contractor=true",
    "internship": "internship=true",
}

_TIME_PARAMS = {
    "1":  "posted_within=1",
    "7":  "posted_within=7",
    "30": "posted_within=30",
}

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


def _sync_status():
    if _start_time > 0:
        scraper_status["elapsed_seconds"] = int(time.time() - _start_time)
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(scraper_status, f)
    except Exception:
        pass


def human_delay(min_sec=1.5, max_sec=3.5):
    time.sleep(random.uniform(min_sec, max_sec))


# ── Driver ────────────────────────────────────────────────────────────────────

def _build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    options.page_load_strategy = "eager"
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


# ── URL builder ───────────────────────────────────────────────────────────────

def _build_url(keyword: str, job_type: str, salary: str, time_filter: str, page: int = 1) -> str:
    params = [
        f"q={quote_plus(keyword)}",
        "l=United+States",
        "remote=true",
    ]
    if job_type and job_type in _TYPE_PARAMS:
        params.append(_TYPE_PARAMS[job_type])
    if salary:
        params.append(f"salary_min={salary}")
    if time_filter and time_filter in _TIME_PARAMS:
        params.append(_TIME_PARAMS[time_filter])
    if page > 1:
        params.append(f"page={page}")
    return "https://startup.jobs/?" + "&".join(params)


# ── Job extraction ────────────────────────────────────────────────────────────

# Ordered from most to least specific — first match wins
_CARD_SELECTORS = [
    "li[class*='job']",
    "div[class*='job-item']",
    "div[class*='job-card']",
    "article[class*='job']",
    "div[data-job-id]",
    "li[data-job-id]",
    "div.job",
    "li.job",
    # Broad fallback: anchor links pointing to job detail pages
]

_TITLE_SELECTORS = [
    "h2 a", "h3 a", "h4 a",
    "a.job-title", "a[class*='title']",
    ".job-title", ".position-title",
    "[class*='job-title']", "[class*='position']",
]

_COMPANY_SELECTORS = [
    ".company-name", ".company", "[class*='company-name']",
    "[class*='company']", ".employer", "[class*='employer']",
    "span.name", "[itemprop='hiringOrganization']",
]


def _find_text(parent, selectors: list) -> str:
    for sel in selectors:
        try:
            el = parent.find_element(By.CSS_SELECTOR, sel)
            text = el.text.strip()
            if text:
                return text
        except (NoSuchElementException, StaleElementReferenceException):
            pass
    return ""


def _find_href(parent, selectors: list) -> str:
    for sel in selectors:
        try:
            el = parent.find_element(By.CSS_SELECTOR, sel)
            href = el.get_attribute("href") or ""
            if href:
                return href
        except (NoSuchElementException, StaleElementReferenceException):
            pass
    return ""


def collect_page_jobs(driver, seen_urls: set, page: int) -> list:
    human_delay(3, 5)

    # Try each card selector strategy
    cards = []
    for sel in _CARD_SELECTORS:
        try:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) >= 2:          # at least 2 means we likely have a real list
                cards = found
                logger.info(f"Page {page}: using selector '{sel}', found {len(found)} cards.")
                break
        except Exception:
            continue

    # Ultimate fallback: scrape all job-path anchor tags directly
    if not cards:
        logger.warning(f"Page {page}: no card selector matched — falling back to anchor scan.")
        return _fallback_anchor_scan(driver, seen_urls)

    jobs = []
    for card in cards:
        try:
            # Job URL (prefer anchors inside title selectors, then any <a>)
            href = _find_href(card, _TITLE_SELECTORS + ["a"])
            if not href or href in seen_urls:
                continue

            # Normalise relative URLs
            if href.startswith("/"):
                href = "https://startup.jobs" + href

            # Job title
            title = _find_text(card, _TITLE_SELECTORS)
            if not title:
                # Try the anchor text we already located
                try:
                    title = card.find_element(By.CSS_SELECTOR, "a").text.strip()
                except Exception:
                    pass
            if not title:
                continue

            company = _find_text(card, _COMPANY_SELECTORS)

            seen_urls.add(href)
            jobs.append({
                "job_title":    title,
                "company_name": company or "N/A",
                "job_url":      href,
            })
        except StaleElementReferenceException:
            continue
        except Exception as exc:
            logger.debug(f"Card parse error: {exc}")
            continue

    logger.info(f"Page {page}: extracted {len(jobs)} new jobs.")
    return jobs


def _fallback_anchor_scan(driver, seen_urls: set) -> list:
    """Collect jobs from all <a> tags whose href looks like a job detail URL."""
    jobs = []
    try:
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/'], a[href*='startup.jobs/']")
        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
                if not href or href in seen_urls:
                    continue
                if href.startswith("/"):
                    href = "https://startup.jobs" + href
                title = a.text.strip()
                if not title or len(title) < 3:
                    continue
                seen_urls.add(href)
                jobs.append({
                    "job_title":    title,
                    "company_name": "N/A",
                    "job_url":      href,
                })
            except StaleElementReferenceException:
                continue
    except Exception as exc:
        logger.warning(f"Anchor fallback failed: {exc}")
    return jobs


# ── Pagination helper ─────────────────────────────────────────────────────────

def _has_next_page(driver) -> bool:
    """Return True if a visible Next-page control exists."""
    next_selectors = [
        "a[rel='next']",
        "a[aria-label='Next page']",
        "a[aria-label='Next']",
        ".pagination .next:not(.disabled) a",
        "nav[aria-label*='pagination'] a[href*='page=']",
        "button[aria-label='Next page']:not([disabled])",
    ]
    for sel in next_selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                return True
        except NoSuchElementException:
            pass
    return False


# ── Save ──────────────────────────────────────────────────────────────────────

def save_startup_job(data: dict):
    session = Session()
    try:
        if session.query(StartupJob).filter_by(job_url=data["job_url"]).first():
            return
        session.add(StartupJob(**data))
        session.commit()
        logger.info(f"Saved: {data['job_title']} @ {data['company_name']}")
    except Exception as e:
        session.rollback()
        logger.error(f"DB error: {e}")
    finally:
        session.close()


def _save_scraper_run(keyword, started_at, pages_scraped, jobs_found, jobs_saved, error_count, run_status):
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
            scraper="startupjobs",
        ))
        session.commit()
        logger.info(f"Run record saved: {run_status}, {jobs_saved} jobs in {duration}s")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save run record: {e}")
    finally:
        session.close()


# ── Main entry point ──────────────────────────────────────────────────────────

def run_startupjobs_scraper(
    keyword: str = "Software Engineer",
    job_type: str = "",
    salary: str = "",
    time_filter: str = "",
):
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
        "running": True, "progress": "Starting startup.jobs scraper...",
        "total": 0, "scraped": 0, "errors": [], "done": False,
        "elapsed_seconds": 0,
        "daily_runs": daily_runs,
        "daily_date": today,
    })
    _sync_status()

    started_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    init_db()
    driver = None

    MAX_PAGES = 40          # hard safety cap (~1000 jobs at 25/page)
    pages_scraped_count = 0
    run_failed = False
    all_jobs: list = []

    try:
        driver = _build_driver()
        seen_urls: set = set()

        for page in range(1, MAX_PAGES + 1):
            scraper_status["progress"] = f"Scraping startup.jobs page {page}..."
            _sync_status()

            url = _build_url(keyword, job_type, salary, time_filter, page)
            logger.info(f"Loading: {url}")
            driver.get(url)

            # Wait for any job-related element to appear
            try:
                WebDriverWait(driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/jobs/']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='job']")),
                        EC.presence_of_element_located((By.TAG_NAME, "article")),
                    )
                )
            except TimeoutException:
                logger.warning(f"Page {page}: timed out waiting for job elements.")
                break

            page_jobs = collect_page_jobs(driver, seen_urls, page)

            if not page_jobs:
                logger.info(f"Page {page}: no new jobs — stopping pagination.")
                break

            all_jobs.extend(page_jobs)
            pages_scraped_count += 1
            scraper_status["total"] = len(all_jobs)
            logger.info(f"Page {page}: +{len(page_jobs)} | cumulative: {len(all_jobs)}")
            _sync_status()

            if not _has_next_page(driver):
                logger.info("No next-page control found — last page reached.")
                break

            human_delay(2, 4)

        scraper_status["total"] = len(all_jobs)
        _sync_status()

        if not all_jobs:
            scraper_status["progress"] = "No jobs found. Try a different keyword or filters."
            return

        for i, job_data in enumerate(all_jobs, 1):
            scraper_status["progress"] = f"Saving job {i}/{len(all_jobs)}..."
            try:
                save_startup_job(job_data)
                scraper_status["scraped"] = i
            except Exception as e:
                scraper_status["errors"].append(str(e))
            _sync_status()

        scraper_status["progress"] = f"Done! Scraped {scraper_status['scraped']} startup jobs."

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        scraper_status["progress"] = f"Error: {e}"
        scraper_status["errors"].append(str(e))
        run_failed = True
    finally:
        error_count = len(scraper_status["errors"])
        if run_failed:
            run_status = "failed"
        elif error_count > 0:
            run_status = "partial"
        else:
            run_status = "success"

        _save_scraper_run(
            keyword=keyword,
            started_at=started_at,
            pages_scraped=pages_scraped_count,
            jobs_found=len(all_jobs),
            jobs_saved=scraper_status["scraped"],
            error_count=error_count,
            run_status=run_status,
        )

        if driver:
            driver.quit()
        scraper_status["running"] = False
        scraper_status["done"] = True
        _sync_status()
