import os
import re
import json
import time
import random
import logging
import datetime
import urllib.request
from urllib.parse import quote_plus
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from models import Job, ScraperRun, Session, init_db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
DEBUG_PORT        = 9222
STATUS_FILE       = "/tmp/scraper_status_linkedin.json"

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

def _attach_existing_chrome():
    try:
        urllib.request.urlopen(
            f"http://localhost:{DEBUG_PORT}/json/version", timeout=2
        )
    except Exception:
        return None, False

    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        driver = webdriver.Chrome(options=options)
        logger.info("Attached to existing Chrome browser.")
        return driver, True
    except Exception as e:
        logger.warning(f"Found Chrome debug port but could not attach: {e}")
        return None, False


def _start_headless_chrome():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--blink-settings=imagesEnabled=false")
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
    logger.info("Started new headless Chrome.")
    return driver, False


def build_driver():
    driver, attached = _attach_existing_chrome()
    if driver:
        return driver, True
    logger.info("No existing Chrome on port %d — starting headless.", DEBUG_PORT)
    return _start_headless_chrome()


# ── Field fill ────────────────────────────────────────────────────────────────

def _fill_field(driver, element, text: str):
    driver.execute_script(
        "var s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;"
        "s.call(arguments[0], arguments[1]);"
        "arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));"
        "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
        element, text,
    )
    if element.get_attribute("value") != text:
        element.click()
        element.clear()
        element.send_keys(text)


# ── Login ─────────────────────────────────────────────────────────────────────

def _already_logged_in(driver) -> bool:
    try:
        driver.get("https://www.linkedin.com/feed/")
        WebDriverWait(driver, 7).until(
            EC.any_of(
                EC.presence_of_element_located((By.CLASS_NAME, "global-nav")),
                EC.url_contains("/feed"),
            )
        )
        return "linkedin.com" in driver.current_url and "login" not in driver.current_url
    except Exception:
        return False


def linkedin_login(driver):
    scraper_status["progress"] = "Checking LinkedIn session..."
    _sync_status()

    if _already_logged_in(driver):
        logger.info("LinkedIn session active — skipping login.")
        scraper_status["progress"] = "Already logged in. Starting search..."
        _sync_status()
        human_delay(1, 2)
        return

    logger.info("Not logged in — performing login.")
    scraper_status["progress"] = "Logging in to LinkedIn..."
    _sync_status()

    driver.get("https://www.linkedin.com/login")
    wait = WebDriverWait(driver, 25)

    email_field = wait.until(EC.element_to_be_clickable((By.ID, "username")))
    human_delay(1, 2)
    _fill_field(driver, email_field, LINKEDIN_EMAIL)
    human_delay(0.8, 1.5)

    password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
    _fill_field(driver, password_field, LINKEDIN_PASSWORD)
    human_delay(0.5, 1.2)

    try:
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except NoSuchElementException:
        password_field.send_keys(Keys.RETURN)

    try:
        wait.until(
            EC.any_of(
                EC.url_contains("feed"),
                EC.url_contains("checkpoint"),
                EC.presence_of_element_located((By.CLASS_NAME, "global-nav")),
            )
        )
        logger.info("Login successful.")
    except TimeoutException:
        raise RuntimeError("Login failed — check credentials or CAPTCHA.")

    human_delay(2, 4)


# ── Job search ────────────────────────────────────────────────────────────────

def navigate_to_jobs(driver, keyword: str, date_posted: str = "", salary_range: str = "", start: int = 0):
    scraper_status["progress"] = f"Searching LinkedIn for '{keyword}'..."
    _sync_status()

    params = [f"keywords={quote_plus(keyword)}", "location=United+States", "f_WT=2"]
    if date_posted:
        params.append(f"f_TPR={date_posted}")
    if salary_range:
        params.append(f"f_SB2={salary_range}")
    params.append(f"start={start}")

    driver.get("https://www.linkedin.com/jobs/search/?" + "&".join(params))
    human_delay(3, 5)


def _scroll_to_load_all(driver, max_scrolls: int = 20, stable_rounds: int = 3):
    """Smooth incremental scroll until <code> tag count stabilizes.

    LinkedIn lazy-loads Voyager API JSON into <code> tags as the user scrolls.
    scrollBy with smooth behavior fires intersection observers correctly —
    instant scrollTo(bottom) skips them and only 2-5 initial jobs ever load.
    """
    prev_count = 0
    stable = 0
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollBy({ top: 600, behavior: 'smooth' });")
        time.sleep(2.0)
        count = driver.execute_script("return document.querySelectorAll('code').length;")
        if count == prev_count:
            stable += 1
            if stable >= stable_rounds:
                break
        else:
            stable = 0
            prev_count = count
    logger.info(f"Scroll stabilised at {prev_count} code tags.")


def collect_job_cards(driver, seen_ids: set = None):
    if seen_ids is None:
        seen_ids = set()

    _scroll_to_load_all(driver)

    code_texts: list = driver.execute_script(
        "return Array.from(document.querySelectorAll('code')).map(c => c.textContent);"
    ) or []

    results = []
    total_count = None

    for raw in code_texts:
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue

        if total_count is None:
            paging = (data.get("data") or {}).get("paging") or {}
            if paging.get("total"):
                total_count = int(paging["total"])

        for item in data.get("included", []):
            urn = item.get("preDashNormalizedJobPostingUrn", "")
            if not urn:
                continue

            m = re.search(r":(\d+)$", urn)
            if not m:
                continue
            job_id = m.group(1)
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            if item.get("blurred"):
                logger.info(f"Skipping blurred/closed job: {job_id}")
                continue

            job_title = (item.get("jobPostingTitle") or "").strip()
            company_name = ((item.get("primaryDescription") or {}).get("text") or "").strip()

            if not job_title:
                continue

            results.append({
                "job_title": job_title,
                "company_name": company_name or "N/A",
                "job_url": f"https://www.linkedin.com/jobs/view/{job_id}",
            })

    # DOM fallback: read visible job card anchor links directly.
    # Catches cases where LinkedIn's JSON key names changed but links still work.
    dom_jobs = driver.execute_script("""
        const out = [];
        const seen = new Set();
        document.querySelectorAll('a[href*="/jobs/view/"]').forEach(a => {
            const href = a.getAttribute('href') || '';
            const m = href.match(/\\/jobs\\/view\\/(\\d+)/);
            if (!m) return;
            const jid = m[1];
            if (seen.has(jid)) return;
            seen.add(jid);
            const card = a.closest('li') || a.closest('[data-job-id]') || a.parentElement;
            const titleEl = card ? (
                card.querySelector('[class*="job-card-list__title"]') ||
                card.querySelector('[class*="job-card__title"]') ||
                card.querySelector('[aria-label]') ||
                card.querySelector('h3') || card.querySelector('h2') || a
            ) : a;
            const title = (
                titleEl.getAttribute('aria-label') || titleEl.textContent || ''
            ).trim();
            const companyEl = card ? (
                card.querySelector('[class*="job-card-container__company-name"]') ||
                card.querySelector('[class*="subtitle"]')
            ) : null;
            const company = companyEl ? companyEl.textContent.trim() : '';
            if (title) out.push({ jid, title, company });
        });
        return out;
    """) or []

    for item in dom_jobs:
        jid = item.get("jid", "")
        if not jid or jid in seen_ids:
            continue
        title = (item.get("title") or "").strip()
        if not title:
            continue
        seen_ids.add(jid)
        results.append({
            "job_title":    title,
            "company_name": (item.get("company") or "N/A").strip() or "N/A",
            "job_url":      f"https://www.linkedin.com/jobs/view/{jid}",
        })

    logger.info(f"Found {len(results)} new jobs on this page (total reported: {total_count}).")
    return results, total_count


# ── Save ──────────────────────────────────────────────────────────────────────

def save_job(data):
    session = Session()
    try:
        if session.query(Job).filter_by(job_url=data["job_url"]).first():
            return
        session.add(Job(**data))
        session.commit()
        logger.info(f"Saved: {data['job_title']} @ {data['company_name']}")
    except Exception as e:
        session.rollback()
        logger.error(f"DB error: {e}")
    finally:
        session.close()


def save_scraper_run(keyword, started_at, pages_scraped, jobs_found, jobs_saved, error_count, run_status):
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
            scraper="linkedin",
        ))
        session.commit()
        logger.info(f"Run record saved: {run_status}, {jobs_saved} jobs in {duration}s")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save run record: {e}")
    finally:
        session.close()


# ── Main entry point ──────────────────────────────────────────────────────────

def run_scraper(keyword: str = "AI ML jobs", date_posted: str = "", salary_range: str = ""):
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
        "running": True, "progress": "Starting...",
        "total": 0, "scraped": 0, "errors": [], "done": False,
        "elapsed_seconds": 0,
        "daily_runs": daily_runs,
        "daily_date": today,
    })
    _sync_status()

    started_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    init_db()
    driver, is_attached = None, False

    PAGE_SIZE = 25
    MAX_RESULTS = 1000

    pages_scraped_count = 0
    run_failed = False
    all_jobs: list = []

    try:
        driver, is_attached = build_driver()
        linkedin_login(driver)

        seen_ids: set = set()
        start = 0
        page_num = 1
        total_available = None

        while True:
            scraper_status["progress"] = f"Scraping page {page_num} (start={start})..."
            _sync_status()

            navigate_to_jobs(driver, keyword, date_posted, salary_range, start=start)
            page_jobs, page_total = collect_job_cards(driver, seen_ids)

            if total_available is None and page_total:
                total_available = min(page_total, MAX_RESULTS)
                logger.info(f"LinkedIn reports {page_total} total results (capped at {total_available}).")

            if not page_jobs:
                logger.info("No new jobs returned — all pages exhausted.")
                break

            all_jobs.extend(page_jobs)
            pages_scraped_count += 1
            scraper_status["total"] = len(all_jobs)
            logger.info(f"Page {page_num}: +{len(page_jobs)} jobs | cumulative: {len(all_jobs)}")
            _sync_status()

            start += PAGE_SIZE
            page_num += 1

            if total_available is not None and start >= total_available:
                logger.info("Reached end of available results.")
                break

            human_delay(2, 4)

        scraper_status["total"] = len(all_jobs)
        _sync_status()

        if not all_jobs:
            scraper_status["progress"] = "No jobs found. Check login or search filters."
            return

        for i, job_data in enumerate(all_jobs, 1):
            scraper_status["progress"] = f"Saving job {i}/{len(all_jobs)}..."
            try:
                save_job(job_data)
                scraper_status["scraped"] = i
            except Exception as e:
                scraper_status["errors"].append(str(e))
            _sync_status()

        scraper_status["progress"] = f"Done! Scraped {scraper_status['scraped']} jobs."

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

        save_scraper_run(
            keyword=keyword,
            started_at=started_at,
            pages_scraped=pages_scraped_count,
            jobs_found=len(all_jobs),
            jobs_saved=scraper_status["scraped"],
            error_count=error_count,
            run_status=run_status,
        )

        if driver and not is_attached:
            driver.quit()
        scraper_status["running"] = False
        scraper_status["done"] = True
        _sync_status()
