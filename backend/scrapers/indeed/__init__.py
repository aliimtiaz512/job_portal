import json
import time
import random
import logging
import datetime
import urllib.request
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException
)

from models import IndeedJob, ScraperRun, Session, init_db

LOG_FILE    = "/tmp/indeed_scraper.log"
STATUS_FILE = "/tmp/scraper_status_indeed.json"
DEBUG_PORT  = 9222

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Always write to a log file so diagnostics survive even when stderr=DEVNULL
_fh = logging.FileHandler(LOG_FILE, mode="a")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_fh)

# ── Filter param maps ─────────────────────────────────────────────────────────

_JOB_TYPE_PARAMS = {
    "fulltime":   "jt=fulltime",
    "parttime":   "jt=parttime",
    "contract":   "jt=contract",
    "internship": "jt=internship",
    "temporary":  "jt=temporary",
}

_DATE_PARAMS = {
    "1":  "fromage=1",
    "3":  "fromage=3",
    "7":  "fromage=7",
    "14": "fromage=14",
}

# ── Status ────────────────────────────────────────────────────────────────────

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
    """Connect to user's already-open Chrome (remote debugging port 9222)."""
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
        logger.warning(f"Could not attach to Chrome: {e}")
        return None, False


def _start_headless_chrome():
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
    logger.info("Started headless Chrome.")
    return driver, False


def build_driver():
    driver, attached = _attach_existing_chrome()
    if driver:
        return driver, True
    logger.info("No Chrome on port %d — starting headless.", DEBUG_PORT)
    return _start_headless_chrome()


# ── URL builder ───────────────────────────────────────────────────────────────

def _build_url(keyword: str, pay: str, job_type: str, date_posted: str, start: int = 0) -> str:
    params = [
        f"q={quote_plus(keyword)}",
        "l=United+States",
        # Remote filter — Indeed's encoded attribute for "Work from home"
        "sc=0kf%3Aattr%280XZKC%29%3B",
    ]
    if job_type and job_type in _JOB_TYPE_PARAMS:
        params.append(_JOB_TYPE_PARAMS[job_type])
    if date_posted and date_posted in _DATE_PARAMS:
        params.append(_DATE_PARAMS[date_posted])
    if pay:
        params.append(f"salary={pay}")
    if start:
        params.append(f"start={start}")
    return "https://www.indeed.com/jobs?" + "&".join(params)


# ── Job extraction ────────────────────────────────────────────────────────────

# Container selectors tried in priority order
_CARD_SELECTORS = [
    "li[data-jk]",                       # most stable — each card has a data-jk job ID
    "div[data-jk]",
    "div.job_seen_beacon",
    "td.resultContent",
    "div[class*='jobCard']",
    "div[class*='result']",
]

# Title selectors (within a card)
_TITLE_SELECTORS = [
    "h2[class*='jobTitle'] a span",
    "h2[class*='jobTitle'] a",
    "h2 a[data-jk] span",
    "h2 a span[id]",
    "a[data-jk] span",
    "[class*='jobTitle'] span",
    "[class*='jobTitle'] a",
]

# Company selectors (within a card)
_COMPANY_SELECTORS = [
    "[data-testid='company-name']",
    "span[class*='companyName']",
    "[class*='companyName']",
    "[class*='company'] span",
    ".companyInfo span",
    "span[class*='employer']",
]


def _card_job_id(card) -> str:
    """Extract Indeed job ID (data-jk) from a card element."""
    jk = card.get_attribute("data-jk") or ""
    if jk:
        return jk
    # Try child anchor
    try:
        a = card.find_element(By.CSS_SELECTOR, "a[data-jk]")
        return a.get_attribute("data-jk") or ""
    except NoSuchElementException:
        return ""


def _card_title(card) -> str:
    for sel in _TITLE_SELECTORS:
        try:
            text = card.find_element(By.CSS_SELECTOR, sel).text.strip()
            if text:
                return text
        except (NoSuchElementException, StaleElementReferenceException):
            pass
    # Last resort: any visible text from the h2
    try:
        return card.find_element(By.TAG_NAME, "h2").text.strip()
    except Exception:
        return ""


def _card_company(card) -> str:
    for sel in _COMPANY_SELECTORS:
        try:
            text = card.find_element(By.CSS_SELECTOR, sel).text.strip()
            if text:
                return text
        except (NoSuchElementException, StaleElementReferenceException):
            pass
    return ""


def _scroll_to_load_jobs(driver, max_scrolls: int = 20):
    """Smooth incremental scroll to trigger Indeed's intersection-observer lazy rendering.

    Instant scrollTo(bottom) skips the observers — scrollBy with smooth behavior
    fires them properly so all job cards render before we read the DOM.
    """
    prev_count = 0
    stable = 0
    for _ in range(max_scrolls):
        driver.execute_script("""
            const c = document.querySelector('#mosaic-provider-jobcards') ||
                      document.querySelector('#resultsCol') ||
                      document.querySelector('.jobsearch-ResultsList');
            if (c) {
                c.scrollBy({ top: 500, behavior: 'smooth' });
            } else {
                window.scrollBy({ top: 500, behavior: 'smooth' });
            }
        """)
        time.sleep(2.0)  # wait for smooth scroll + lazy render cycle
        count = driver.execute_script(
            "return document.querySelectorAll('[data-jk], a[href*=\"jk=\"]').length;"
        )
        if count == prev_count:
            stable += 1
            if stable >= 3:
                break
        else:
            stable = 0
            prev_count = count
    logger.info(f"Scroll stabilised at {prev_count} job elements.")


def _extract_jobs_via_js(driver) -> list:
    """Extract jobs using two strategies: [data-jk] attrs first, href jk= params second."""
    return driver.execute_script("""
        const results = [];
        const seen = new Set();

        function getTitle(card) {
            if (!card) return '';
            const el =
                card.querySelector('h2[class*="jobTitle"] a span') ||
                card.querySelector('h2 a span[title]') ||
                card.querySelector('h2 a span') ||
                card.querySelector('[class*="jobTitle"] span') ||
                card.querySelector('h2 span') ||
                card.querySelector('h2 a') ||
                card.querySelector('h2');
            return el ? el.textContent.trim() : '';
        }

        function getCompany(card) {
            if (!card) return '';
            const el =
                card.querySelector('[data-testid="company-name"]') ||
                card.querySelector('[class*="companyName"]') ||
                card.querySelector('.companyInfo');
            return el ? el.textContent.trim() : '';
        }

        // Strategy 1: elements with data-jk attribute
        document.querySelectorAll('[data-jk]').forEach(el => {
            const jk = el.getAttribute('data-jk');
            if (!jk || seen.has(jk)) return;
            seen.add(jk);
            const card = el.closest('li') || el.closest('.job_seen_beacon') || el.parentElement;
            const title = getTitle(card) || el.textContent.trim();
            const company = getCompany(card);
            if (title) results.push({ jk, title, company });
        });

        // Strategy 2: anchor hrefs containing ?jk= or &jk= (catches any DOM structure)
        document.querySelectorAll('a[href*="jk="]').forEach(a => {
            const href = a.getAttribute('href') || '';
            const m = href.match(/[?&]jk=([a-zA-Z0-9]+)/);
            if (!m) return;
            const jk = m[1];
            if (seen.has(jk)) return;
            seen.add(jk);
            const title = (a.getAttribute('title') || a.textContent || '').trim();
            const card = a.closest('li') || a.closest('[class*="result"]') || a.parentElement;
            const company = getCompany(card);
            if (title) results.push({ jk, title, company });
        });

        return results;
    """) or []


def _diagnose_page(driver, page: int):
    """Log what the page actually contains so we can spot DOM changes or bot-blocks."""
    try:
        title   = driver.title
        url     = driver.current_url
        snippet = driver.execute_script(
            "return document.body ? document.body.innerText.substring(0, 400) : 'no body';"
        )
        dj_count = driver.execute_script(
            "return document.querySelectorAll('[data-jk]').length;"
        )
        jk_href  = driver.execute_script(
            "return document.querySelectorAll('a[href*=\"jk=\"]').length;"
        )
        logger.warning(
            f"[DIAG page {page}] title={title!r} url={url}\n"
            f"  [data-jk]={dj_count}  a[href*=jk]={jk_href}\n"
            f"  body_snippet={snippet!r}"
        )
    except Exception as exc:
        logger.warning(f"[DIAG page {page}] failed: {exc}")


def collect_page_jobs(driver, seen_ids: set, page: int) -> list:
    human_delay(2, 4)
    _scroll_to_load_jobs(driver)

    # Primary: JS extraction (avoids stale element refs, works with any DOM structure)
    raw = _extract_jobs_via_js(driver)
    if raw:
        logger.info(f"Page {page}: JS extraction found {len(raw)} total job elements.")
        jobs = []
        for item in raw:
            job_id = item.get("jk", "")
            if not job_id or job_id in seen_ids:
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue
            company = (item.get("company") or "").strip()
            seen_ids.add(job_id)
            jobs.append({
                "job_title":    title,
                "company_name": company or "N/A",
                "job_url":      f"https://www.indeed.com/viewjob?jk={job_id}",
            })
        logger.info(f"Page {page}: {len(jobs)} new jobs after dedup.")
        if len(jobs) < 5:
            _diagnose_page(driver, page)
        return jobs

    # If JS returned nothing at all, log the page state before trying Selenium
    _diagnose_page(driver, page)

    # Fallback: Selenium CSS selector loop
    logger.warning(f"Page {page}: JS extraction returned nothing — falling back to Selenium selectors.")
    cards = []
    for sel in _CARD_SELECTORS:
        try:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(found) >= 2:
                cards = found
                logger.info(f"Page {page}: fallback selector '{sel}' → {len(found)} cards.")
                break
        except Exception:
            continue

    if not cards:
        logger.warning(f"Page {page}: no card selector matched.")
        return []

    jobs = []
    for card in cards:
        try:
            job_id = _card_job_id(card)
            if not job_id or job_id in seen_ids:
                continue
            title = _card_title(card)
            if not title:
                continue
            company = _card_company(card)
            seen_ids.add(job_id)
            jobs.append({
                "job_title":    title,
                "company_name": company or "N/A",
                "job_url":      f"https://www.indeed.com/viewjob?jk={job_id}",
            })
        except StaleElementReferenceException:
            continue
        except Exception as exc:
            logger.debug(f"Card parse error: {exc}")
            continue

    logger.info(f"Page {page}: extracted {len(jobs)} new jobs (fallback).")
    return jobs


# ── Pagination ────────────────────────────────────────────────────────────────

def _has_next_page(driver) -> bool:
    """Return True if an enabled Next-page link is present anywhere on the page."""
    css_selectors = [
        # Current Indeed testid (most reliable)
        "[data-testid='pagination-page-next']",
        "a[data-testid='pagination-page-next']",
        # Aria-label variants
        "a[aria-label='Next Page']",
        "a[aria-label='Next page']",
        "a[aria-label='Next']",
        # Class-based
        "a.np",
        "a.pn",
        # Navigation container with start= links
        "nav[role='navigation'] a[href*='start=']",
        "div[class*='pagination'] a[href*='start=']",
        # Any link containing start= (broad fallback)
        "a[href*='start=']",
    ]
    for sel in css_selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if any(e.is_displayed() for e in els):
                logger.info(f"_has_next_page: matched '{sel}'")
                return True
        except Exception:
            pass
    # XPath text fallbacks
    try:
        els = driver.find_elements(
            By.XPATH,
            "//a[contains(translate(normalize-space(.), 'NEXT', 'next'), 'next')]"
        )
        if any(e.is_displayed() for e in els):
            return True
    except Exception:
        pass
    logger.info("_has_next_page: no next-page indicator found.")
    return False


# ── Save ──────────────────────────────────────────────────────────────────────

def save_indeed_job(data: dict):
    session = Session()
    try:
        if session.query(IndeedJob).filter_by(job_url=data["job_url"]).first():
            return
        session.add(IndeedJob(**data))
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
        duration    = int(time.time() - _start_time)
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
            scraper="indeed",
        ))
        session.commit()
        logger.info(f"Run record saved: {run_status}, {jobs_saved} jobs in {duration}s")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save run record: {e}")
    finally:
        session.close()


# ── Main entry point ──────────────────────────────────────────────────────────

def run_indeed_scraper(
    keyword:     str = "Software Engineer",
    pay:         str = "",
    job_type:    str = "",
    date_posted: str = "",
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
        "running": True, "progress": "Starting Indeed scraper...",
        "total": 0, "scraped": 0, "errors": [], "done": False,
        "elapsed_seconds": 0,
        "daily_runs": daily_runs,
        "daily_date": today,
    })
    _sync_status()

    started_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    init_db()
    driver, is_attached = None, False

    PAGE_SIZE  = 10     # Indeed shows ~10 results per page
    MAX_PAGES  = 100    # safety cap (~1000 jobs)

    pages_scraped_count = 0
    run_failed          = False
    all_jobs: list      = []

    try:
        driver, is_attached = build_driver()

        seen_ids: set = set()
        start = 0

        for page_num in range(1, MAX_PAGES + 1):
            scraper_status["progress"] = f"Scraping Indeed page {page_num}..."
            _sync_status()

            url = _build_url(keyword, pay, job_type, date_posted, start=start)
            logger.info(f"Loading: {url}")
            driver.get(url)

            # Wait for page content — broad selectors so a DOM change doesn't kill the loop
            try:
                WebDriverWait(driver, 25).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-jk]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-jk]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='jk=']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.job_seen_beacon")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "td.resultContent")),
                        EC.presence_of_element_located((By.ID, "mosaic-provider-jobcards")),
                        EC.presence_of_element_located((By.ID, "resultsCol")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".jobsearch-ResultsList")),
                    )
                )
            except TimeoutException:
                # Log what landed instead of silently stopping
                logger.warning(f"Page {page_num}: content wait timed out — trying extraction anyway.")
                _diagnose_page(driver, page_num)
                # Only stop if we've never found a single job (indicates hard block)
                if not all_jobs:
                    break

            page_jobs = collect_page_jobs(driver, seen_ids, page_num)

            if not page_jobs:
                logger.info(f"Page {page_num}: no new jobs — stopping.")
                break

            all_jobs.extend(page_jobs)
            pages_scraped_count += 1
            scraper_status["total"] = len(all_jobs)
            logger.info(f"Page {page_num}: +{len(page_jobs)} | cumulative: {len(all_jobs)}")
            _sync_status()

            if not _has_next_page(driver):
                logger.info("No Next button found — last page reached.")
                break

            start += PAGE_SIZE
            human_delay(2, 4)

        scraper_status["total"] = len(all_jobs)
        _sync_status()

        if not all_jobs:
            scraper_status["progress"] = "No jobs found. Try different keyword or filters."
            return

        for i, job_data in enumerate(all_jobs, 1):
            scraper_status["progress"] = f"Saving job {i}/{len(all_jobs)}..."
            try:
                save_indeed_job(job_data)
                scraper_status["scraped"] = i
            except Exception as e:
                scraper_status["errors"].append(str(e))
            _sync_status()

        scraper_status["progress"] = f"Done! Scraped {scraper_status['scraped']} Indeed jobs."

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

        if driver and not is_attached:
            driver.quit()
        scraper_status["running"] = False
        scraper_status["done"]    = True
        _sync_status()
