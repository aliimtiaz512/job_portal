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

from models import ZipRecruiterJob, ScraperRun, Session, init_db

LOG_FILE    = "/tmp/ziprecruiter_scraper.log"
STATUS_FILE = "/tmp/scraper_status_ziprecruiter.json"
DEBUG_PORT  = 9222

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_fh = logging.FileHandler(LOG_FILE, mode="a")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_fh)

_DATE_PARAMS = {
    "": "",
    "anytime": "any",
    "30": "30",
    "10": "10",
    "5": "5",
    "1": "1",
}

_EMPLOYMENT_PARAMS = {
    "": "",
    "all": "",
    "fulltime": "full_time",
    "parttime": "part_time",
    "contract": "contract",
    "perdiem": "per_diem",
    "temporary": "temporary",
}

_EXPERIENCE_PARAMS = {
    "": "",
    "noexperience": "no_experience",
    "junior": "entry_level",
    "mid": "mid_level",
    "senior": "senior",
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


def human_delay(min_sec=2.0, max_sec=4.0):
    time.sleep(random.uniform(min_sec, max_sec))


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


def _build_url(keyword: str, date_posted: str, salary_min: str, employment_type: str, experience: str, page: int = 1) -> str:
    base_url = "https://www.ziprecruiter.com/jobs-search"
    params = [
        f"search={quote_plus(keyword)}",
        "location=United+States",
        "intsrc=zr.fe.jobs-landing",
    ]

    if date_posted and date_posted in _DATE_PARAMS and _DATE_PARAMS[date_posted]:
        params.append(f"posted={_DATE_PARAMS[date_posted]}")

    if salary_min:
        params.append(f"salary_min={salary_min}")
    else:
        params.append("salary_min=120")

    params.append("salary_max=300")

    if employment_type and employment_type in _EMPLOYMENT_PARAMS:
        emp = _EMPLOYMENT_PARAMS[employment_type]
        if emp:
            params.append(f"employment_type={emp}")

    if experience and experience in _EXPERIENCE_PARAMS:
        exp = _EXPERIENCE_PARAMS[experience]
        if exp:
            params.append(f"experience_level={exp}")

    params.append(f"page={page}")

    return base_url + "?" + "&".join(params)


def _scroll_to_load_jobs(driver, max_scrolls: int = 25):
    prev_count = 0
    stable = 0
    for i in range(max_scrolls):
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(1.2)
        count = driver.execute_script(
            "return document.querySelectorAll('button[type=\"button\"] h2, h2[class*=\"text\"]').length;"
        )

        # Check for "Load More" button and click it
        load_more = driver.execute_script("""
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent?.toLowerCase() || '';
                if (text.includes('load more') || text.includes('show more') || text.includes('see more')) {
                    return btn;
                }
            }
            return null;
        """)
        if load_more:
            try:
                driver.execute_script("arguments[0].click();", load_more)
                time.sleep(2)
                logger.info("Clicked Load More button")
            except:
                pass

        if count == prev_count:
            stable += 1
            if stable >= 3:
                break
        else:
            stable = 0
            prev_count = count
        logger.info(f"Scroll {i+1}: {count} job elements")

    logger.info(f"Scroll complete: {prev_count} job title elements.")


def _extract_jobs_via_js(driver) -> list:
    debug_info = driver.execute_script("""
        // Debug: count different element types
        const debug = {
            buttons: document.querySelectorAll('button').length,
            h2s: document.querySelectorAll('h2').length,
            jobLinks: document.querySelectorAll('a[href*="/job/"]').length,
            dataTestCompany: document.querySelectorAll('[data-testid*="company"]').length,
            jobCardCompany: document.querySelectorAll('[data-testid="job-card-company"]').length,
            flexCols: document.querySelectorAll('[class*="flex flex-col"]').length,
            sampleLinks: []
        };

        // Get sample of job links - use Array.from instead of slice
        const links = Array.from(document.querySelectorAll('a[href*="/job/"]')).slice(0, 3);
        links.forEach(a => {
            debug.sampleLinks.push({
                href: a.href,
                text: a.textContent?.substring(0, 50),
                parentClasses: a.parentElement?.className?.toString().substring(0, 100)
            });
        });

        return debug;
    """)
    logger.info(f"Debug info: {debug_info}")

    return driver.execute_script("""
        const results = [];
        const seen = new Set();

        // Debug: check counts
        const allButtons = document.querySelectorAll('button[type="button"]').length;
        const allH2s = document.querySelectorAll('h2').length;
        const allCompanyElements = document.querySelectorAll('[data-testid="job-card-company"]').length;
        console.log('Buttons:', allButtons, 'H2s:', allH2s, 'Companies:', allCompanyElements);

        // Method 1: Use all h2 elements that are inside job cards (not in header/footer)
        document.querySelectorAll('h2').forEach(h2 => {
            const title = h2.textContent?.trim() || '';
            if (!title || title.length < 5) return;

            // Skip non-job h2s - these are header/nav/marketing elements
            const skipPatterns = [
                'job scraper', 'ziprecruiter', 'we found', 'open positions',
                'rating', 'review', 'salary', 'search', 'home', 'about',
                'sign in', 'sign up', 'login', 'register', 'help',
                'privacy', 'terms', 'cookie', 'contact', 'description',
                'qualification', 'responsibility', 'benefit'
            ];
            const lowerTitle = title.toLowerCase();
            if (skipPatterns.some(p => lowerTitle.includes(p))) return;

            // Skip very short titles or titles that are just numbers/dates
            if (title.length < 10 || /^\\d+$/.test(title)) return;

            // Find the closest container with company info
            let cardContainer = h2;
            for (let i = 0; i < 8; i++) {
                if (!cardContainer.parentElement) break;
                cardContainer = cardContainer.parentElement;
                // Check if this container has company info
                if (cardContainer.querySelector && cardContainer.querySelector('[data-testid="job-card-company"]')) break;
            }

            // Look for company
            let company = '';
            let jobUrl = '';

            const companyEl = cardContainer?.querySelector('[data-testid="job-card-company"]');
            if (companyEl) {
                company = companyEl.textContent?.trim() || companyEl.innerText?.trim() || '';
                jobUrl = companyEl.href || '';
            }

            // Alternative: find /co/ link
            if (!company) {
                const allLinks = cardContainer?.querySelectorAll('a') || [];
                for (const link of allLinks) {
                    const href = link.getAttribute('href') || '';
                    if (href.includes('/co/')) {
                        company = link.textContent?.trim() || link.innerText?.trim() || '';
                        jobUrl = link.href || '';
                        break;
                    }
                }
            }

            // Generate unique ID
            const jobId = title.toLowerCase().replace(/\\s+/g, '-').substring(0, 40);
            if (seen.has(jobId)) return;
            seen.add(jobId);

            // Build URL
            let finalUrl = jobUrl;
            if (finalUrl && finalUrl.includes('/co/')) {
                finalUrl = 'https://www.ziprecruiter.com' + finalUrl;
            } else {
                finalUrl = `https://www.ziprecruiter.com/jobs-search?search=${encodeURIComponent(title)}&location=United+States`;
            }

            results.push({
                job_id: jobId,
                title: title,
                company: company || 'N/A',
                url: finalUrl
            });
        });

        console.log('Found', results.length, 'jobs from h2 extraction');
        return results;
    """) or []


def collect_page_jobs(driver, seen_ids: set, page: int) -> list:
    human_delay(2, 4)
    _scroll_to_load_jobs(driver)

    raw = _extract_jobs_via_js(driver)
    if raw:
        logger.info(f"Page {page}: JS extraction found {len(raw)} total job elements.")
        jobs = []
        for item in raw:
            job_id = item.get("job_id", "")
            if not job_id or job_id in seen_ids:
                continue
            title = (item.get("title") or "").strip()
            if not title:
                continue
            company = (item.get("company") or "").strip()
            job_url = (item.get("url") or "").strip()
            seen_ids.add(job_id)
            jobs.append({
                "job_title": title,
                "company_name": company or "N/A",
                "job_url": job_url,
            })
            logger.debug(f"Found job: {title} @ {company}")
        logger.info(f"Page {page}: {len(jobs)} new jobs after dedup.")
        return jobs

    logger.warning(f"Page {page}: JS extraction returned nothing.")
    html_sample = driver.execute_script("return document.body.innerHTML.substring(0, 2000);")
    logger.warning(f"Page {page} HTML sample: {html_sample[:500]}")
    return []


def _has_next_page(driver) -> bool:
    css_selectors = [
        "a[data-testid='pagination-next']",
        "button[data-testid='pagination-next']",
        "a[aria-label*='next']",
        "button[aria-label*='next']",
        "a[class*='next']",
        "button[class*='next']",
        "a[href*='page=']",
        "button:has-text('Next')",
        "a:has-text('Next')",
        "button:has-text('Show more')",
        "button:has-text('Load more')",
        "[class*='load-more']",
        "button[type='button'][class*='show']",
    ]
    for sel in css_selectors:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if any(e.is_displayed() for e in els):
                logger.info(f"_has_next_page: matched '{sel}'")
                return True
        except Exception:
            pass

    page_count = driver.execute_script("""
        return document.querySelectorAll('[class*="pagination"], nav[role="navigation"]').length;
    """)
    if page_count > 0:
        logger.info("_has_next_page: found pagination container")
        return True

    return False


def save_ziprecruiter_job(data: dict):
    session = Session()
    try:
        if session.query(ZipRecruiterJob).filter_by(job_url=data["job_url"]).first():
            return
        session.add(ZipRecruiterJob(**data))
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
            scraper="ziprecruiter",
        ))
        session.commit()
        logger.info(f"Run record saved: {run_status}, {jobs_saved} jobs in {duration}s")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save run record: {e}")
    finally:
        session.close()


def run_ziprecruiter_scraper(
    keyword:          str = "Software Engineer",
    date_posted:     str = "",
    salary_min:      str = "120",
    employment_type: str = "",
    experience:      str = "",
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
        "running": True, "progress": "Starting ZipRecruiter scraper...",
        "total": 0, "scraped": 0, "errors": [], "done": False,
        "elapsed_seconds": 0,
        "daily_runs": daily_runs,
        "daily_date": today,
    })
    _sync_status()

    started_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    init_db()
    driver, is_attached = None, False

    MAX_PAGES = 50

    pages_scraped_count = 0
    run_failed          = False
    all_jobs: list      = []

    try:
        driver, is_attached = build_driver()

        seen_ids: set = set()

        for page_num in range(1, MAX_PAGES + 1):
            scraper_status["progress"] = f"Scraping ZipRecruiter page {page_num}..."
            _sync_status()

            url = _build_url(keyword, date_posted, salary_min, employment_type, experience, page=page_num)
            logger.info(f"Loading: {url}")
            driver.get(url)

            try:
                WebDriverWait(driver, 25).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/job/']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='job-card']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                    )
                )
            except TimeoutException:
                logger.warning(f"Page {page_num}: content wait timed out — trying extraction anyway.")
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

            human_delay(2, 4)

        scraper_status["total"] = len(all_jobs)
        _sync_status()

        if not all_jobs:
            scraper_status["progress"] = "No jobs found. Try different keyword or filters."
            return

        for i, job_data in enumerate(all_jobs, 1):
            scraper_status["progress"] = f"Saving job {i}/{len(all_jobs)}..."
            try:
                save_ziprecruiter_job(job_data)
                scraper_status["scraped"] = i
            except Exception as e:
                scraper_status["errors"].append(str(e))
            _sync_status()

        scraper_status["progress"] = f"Done! Scraped {scraper_status['scraped']} ZipRecruiter jobs."

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