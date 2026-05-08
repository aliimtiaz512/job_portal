import json
import math
import os
import re
import time
import random
import logging
import datetime
import urllib.request
from urllib.parse import quote_plus, quote
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from models import DiceJob, ScraperRun, Session, init_db

load_dotenv()

LOG_FILE    = "/tmp/dice_scraper.log"
STATUS_FILE = "/tmp/scraper_status_dice.json"
DEBUG_PORT  = 9222

DICE_EMAIL    = os.getenv("DICE_EMAIL")
DICE_PASSWORD = os.getenv("DICE_PASSWORD")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_fh = logging.FileHandler(LOG_FILE, mode="a")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_fh)

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
        urllib.request.urlopen(f"http://localhost:{DEBUG_PORT}/json/version", timeout=2)
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
        driver.get("https://www.dice.com/")
        time.sleep(3)
        if "accounts.dice.com" in driver.current_url:
            return False
        found = driver.execute_script("""
            const checks = [
                '[data-cy="user-menu"]', '[data-cy="logout"]',
                '[data-cy="nav-seeker-home"]', '[class*="userMenu"]',
                '[class*="user-menu"]', 'button[aria-label*="profile" i]',
                'button[aria-label*="account" i]',
            ];
            return checks.some(s => !!document.querySelector(s));
        """)
        return bool(found)
    except Exception:
        return False


def dice_login(driver):
    scraper_status["progress"] = "Checking Dice session..."
    _sync_status()

    if _already_logged_in(driver):
        logger.info("Dice session active — skipping login.")
        scraper_status["progress"] = "Already logged in."
        _sync_status()
        human_delay(1, 2)
        return

    logger.info("Not logged in — performing Dice login.")
    scraper_status["progress"] = "Logging in to Dice..."
    _sync_status()

    driver.get("https://www.dice.com/")
    wait = WebDriverWait(driver, 25)
    human_delay(2, 3)

    # Click Login / Register button
    login_selectors = [
        "[data-cy='login-register-button']",
        "[data-cy='login-link']",
        "a[href*='/dashboard/login']",
        "a[href*='login'][class*='btn']",
        "a[href*='login']",
    ]
    clicked = False
    for sel in login_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed():
                btn.click()
                clicked = True
                logger.info(f"Clicked login button: {sel}")
                break
        except NoSuchElementException:
            continue

    if not clicked:
        logger.info("Login button not found — navigating directly.")
        driver.get("https://www.dice.com/dashboard/login")

    human_delay(2, 4)
    logger.info(f"Post-click URL: {driver.current_url}")

    # ── Email step ────────────────────────────────────────────────────────────
    try:
        email_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "input[type='email'], input[name='email'], #email"
        )))
        _fill_field(driver, email_field, DICE_EMAIL)
        human_delay(0.8, 1.5)

        submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "button[type='submit'], [data-cy='continue-btn'], [data-cy='submit-btn']"
        )))
        submit.click()
        logger.info("Submitted email.")
        human_delay(2, 3)
    except TimeoutException as exc:
        raise RuntimeError(f"Dice login – email step failed: {exc}")

    # ── Password step ─────────────────────────────────────────────────────────
    try:
        pw_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "input[type='password'], input[name='password'], #password"
        )))
        _fill_field(driver, pw_field, DICE_PASSWORD)
        human_delay(0.8, 1.5)

        signin = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
            "button[type='submit'], [data-cy='sign-in-btn'], [data-cy='submit-btn']"
        )))
        signin.click()
        logger.info("Submitted password.")
    except TimeoutException as exc:
        raise RuntimeError(f"Dice login – password step failed: {exc}")

    # ── Wait for dashboard ────────────────────────────────────────────────────
    try:
        wait.until(EC.any_of(
            EC.url_contains("dice.com/dashboard"),
            EC.url_contains("dice.com/jobs"),
            EC.url_contains("dice.com/home"),
            EC.presence_of_element_located((By.CSS_SELECTOR,
                "[data-cy='user-menu'], [data-cy='nav-seeker-home'], nav"
            )),
        ))
        logger.info("Dice login successful.")
    except TimeoutException:
        curr = driver.current_url
        if "accounts.dice.com" in curr or "login" in curr:
            raise RuntimeError("Dice login failed — check credentials or CAPTCHA.")
        logger.warning(f"Login wait timed out but URL is {curr!r} — proceeding.")

    human_delay(2, 4)


# ── URL builder ───────────────────────────────────────────────────────────────

def _build_url(keyword: str, date_posted: str, employment_type: str, page: int = 1) -> str:
    params = [
        f"q={quote_plus(keyword)}",
        "location=United+States",
        "latitude=37.09024",
        "longitude=-95.71289",
        "countryCode=US",
        "locationPrecision=Country",
        "radius=30",
        "radiusUnit=mi",
        f"page={page}",
        "pageSize=20",
        "filters.workplaceTypes=Remote",
    ]
    if date_posted:
        params.append(f"filters.postedDate={date_posted}")
    if employment_type:
        params.append(f"filters.employmentType={quote(employment_type, safe='')}")
    return "https://www.dice.com/jobs?" + "&".join(params)


# ── Job extraction ────────────────────────────────────────────────────────────

def _get_total_jobs(driver) -> int | None:
    try:
        text = driver.execute_script("""
            const selectors = [
                '[data-testid="search-result-count"]',
                '[data-testid="results-count"]',
                '[data-cy="results-count"]',
                'h6[class*="count"]',
                'span[class*="count"]',
            ];
            for (const s of selectors) {
                const el = document.querySelector(s);
                if (el && el.textContent.trim()) return el.textContent.trim();
            }
            // Generic text scan for "NNN Jobs" or "NNN Results"
            for (const el of document.querySelectorAll('h6, h5, p, span, div')) {
                const t = el.textContent.trim();
                if (/^[\\d,]+\\s*(jobs?|results?)/i.test(t) && t.length < 60) return t;
                if (/[\\d,]+\\s*(jobs?|results?)/i.test(t) && t.length < 60) return t;
            }
            return null;
        """)
        if text:
            m = re.search(r"([\d,]+)", str(text))
            if m:
                return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    return None


def _extract_jobs_js(driver) -> list:
    """
    Extract job cards using the confirmed Dice DOM structure:

    Title:
      <a data-testid="job-search-job-detail-link"
         aria-label="AI/ML Engineer"
         href="https://www.dice.com/job-detail/<uuid>">AI/ML Engineer</a>

    Company:
      <a href="/company-profile/<uuid>?companyname=...">   ← NO aria-label
        <p class="mb-0 line-clamp-2 ...">Skywaves MP LLC</p>
      </a>
      (the logo sibling link has aria-label="Company Logo" and is excluded)

    Strategy: for each title link, walk up the DOM until we reach the first
    ancestor that also contains the company <p> — that ancestor is the card.
    """
    return driver.execute_script("""
        const results = [];
        const seen    = new Set();

        // CSS selector that matches only the company-name link (not the logo link)
        const COMPANY_SEL =
            'a[href*="/company-profile/"]:not([aria-label="Company Logo"]) p';

        function jobId(href) {
            const m = (href || '').match(/job-detail\\/([^?#\\/]+)/);
            return m ? m[1] : '';
        }

        function findCard(titleEl) {
            // Walk up from the title <a> until we hit a node that
            // also contains the company <p>.  Stop before <body>.
            let node = titleEl.parentElement;
            while (node && node.tagName !== 'BODY') {
                if (node.querySelector(COMPANY_SEL)) return node;
                node = node.parentElement;
            }
            return null;
        }

        function companyName(card) {
            if (!card) return '';
            const p = card.querySelector(COMPANY_SEL);
            return p ? p.textContent.trim() : '';
        }

        // ── Primary: data-testid confirmed in Dice DOM ────────────────────────
        document.querySelectorAll(
            'a[data-testid="job-search-job-detail-link"]'
        ).forEach(titleEl => {
            const href  = titleEl.getAttribute('href') || '';
            const jid   = jobId(href);
            if (!jid || seen.has(jid)) return;

            // aria-label holds the clean title (e.g. "AI/ML Engineer")
            const title = (
                titleEl.getAttribute('aria-label') || titleEl.textContent || ''
            ).trim();
            if (!title) return;

            const card = findCard(titleEl);
            const url  = href.startsWith('http') ? href : 'https://www.dice.com' + href;

            seen.add(jid);
            results.push({ title, company: companyName(card), url, jid });
        });

        // ── Fallback: generic job-detail href (survives data-testid renames) ──
        if (!results.length) {
            document.querySelectorAll('a[href*="/job-detail/"]').forEach(a => {
                const href  = a.getAttribute('href') || '';
                const jid   = jobId(href);
                if (!jid || seen.has(jid)) return;

                const title = (
                    a.getAttribute('aria-label') || a.textContent || ''
                ).trim();
                if (!title || title.length > 200) return;

                const card = findCard(a);
                const url  = href.startsWith('http') ? href : 'https://www.dice.com' + href;

                seen.add(jid);
                results.push({ title, company: companyName(card), url, jid });
            });
        }

        return results;
    """) or []


def _collect_page(driver, seen_ids: set, page: int) -> list:
    # Smooth scroll to trigger lazy rendering
    for _ in range(4):
        driver.execute_script("window.scrollBy({ top: 600, behavior: 'smooth' });")
        time.sleep(1.2)

    raw = _extract_jobs_js(driver)
    jobs = []
    for item in raw:
        jid   = (item.get("jid") or "").strip()
        title = (item.get("title") or "").strip()
        url   = (item.get("url") or "").strip()
        if not jid or jid in seen_ids or not title or "dice.com" not in url:
            continue
        seen_ids.add(jid)
        jobs.append({
            "job_title":    title,
            "company_name": (item.get("company") or "N/A").strip() or "N/A",
            "job_url":      url,
        })

    logger.info(f"Page {page}: {len(jobs)} new jobs.")
    return jobs


# ── Pagination ────────────────────────────────────────────────────────────────

def _has_next_page(driver) -> bool:
    try:
        return bool(driver.execute_script("""
            const sels = [
                '[data-testid="pagination-next"]',
                '[data-cy="pagination-next"]',
                '[data-testid="right-arrow-nav"]',
                '[aria-label="Next Page"]',
                '[aria-label="Next page"]',
                '[aria-label="Next"]',
                'button[class*="next"]:not([disabled])',
                'a[class*="next"]:not([disabled])',
            ];
            return sels.some(s => {
                const el = document.querySelector(s);
                return el && !el.disabled && !el.hasAttribute('disabled')
                           && el.offsetParent !== null;
            });
        """))
    except Exception:
        return False


# ── Persist ───────────────────────────────────────────────────────────────────

def _save_job(data: dict):
    session = Session()
    try:
        if session.query(DiceJob).filter_by(job_url=data["job_url"]).first():
            return
        session.add(DiceJob(**data))
        session.commit()
        logger.info(f"Saved: {data['job_title']} @ {data['company_name']}")
    except Exception as e:
        session.rollback()
        logger.error(f"DB error: {e}")
    finally:
        session.close()


def _save_run(keyword, started_at, pages, found, saved, errors, status):
    session = Session()
    try:
        session.add(ScraperRun(
            keyword=keyword,
            started_at=started_at,
            finished_at=datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            duration_seconds=int(time.time() - _start_time),
            pages_scraped=pages,
            jobs_found=found,
            jobs_saved=saved,
            error_count=errors,
            run_status=status,
            scraper="dice",
        ))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to save run: {e}")
    finally:
        session.close()


# ── Main entry point ──────────────────────────────────────────────────────────

def run_dice_scraper(
    keyword:         str = "Software Engineer",
    date_posted:     str = "",
    employment_type: str = "",
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
        "running": True, "progress": "Starting Dice scraper...",
        "total": 0, "scraped": 0, "errors": [], "done": False,
        "elapsed_seconds": 0, "daily_runs": daily_runs, "daily_date": today,
    })
    _sync_status()

    started_at = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    init_db()
    driver, is_attached = None, False

    PAGE_SIZE = 20
    MAX_PAGES = 50

    pages_scraped = 0
    run_failed    = False
    all_jobs: list = []

    try:
        driver, is_attached = build_driver()
        dice_login(driver)

        seen_ids: set = set()
        total_pages = MAX_PAGES

        for page_num in range(1, MAX_PAGES + 1):
            scraper_status["progress"] = f"Scraping Dice page {page_num}..."
            _sync_status()

            url = _build_url(keyword, date_posted, employment_type, page=page_num)
            logger.info(f"Loading: {url}")
            driver.get(url)

            try:
                WebDriverWait(driver, 25).until(EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        'a[data-testid="job-search-job-detail-link"]')),
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        'a[href*="/job-detail/"]')),
                ))
            except TimeoutException:
                logger.warning(f"Page {page_num}: timeout waiting for job cards.")
                if not all_jobs:
                    break

            # Determine total pages from first load
            if page_num == 1:
                total = _get_total_jobs(driver)
                if total:
                    total_pages = min(math.ceil(total / PAGE_SIZE), MAX_PAGES)
                    logger.info(f"Dice: {total} total jobs → {total_pages} pages.")
                    scraper_status["progress"] = (
                        f"Found ~{total} jobs across {total_pages} pages. Scraping..."
                    )
                    _sync_status()

            page_jobs = _collect_page(driver, seen_ids, page_num)

            if not page_jobs:
                logger.info(f"Page {page_num}: no new jobs — stopping.")
                break

            all_jobs.extend(page_jobs)
            pages_scraped += 1
            scraper_status["total"] = len(all_jobs)
            logger.info(
                f"Page {page_num}/{total_pages}: +{len(page_jobs)} | total: {len(all_jobs)}"
            )
            _sync_status()

            if page_num >= total_pages:
                logger.info("Reached last calculated page.")
                break
            if not _has_next_page(driver):
                logger.info("No next-page button found.")
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
                _save_job(job_data)
                scraper_status["scraped"] = i
            except Exception as e:
                scraper_status["errors"].append(str(e))
            _sync_status()

        scraper_status["progress"] = f"Done! Saved {scraper_status['scraped']} Dice jobs."

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        scraper_status["progress"] = f"Error: {e}"
        scraper_status["errors"].append(str(e))
        run_failed = True
    finally:
        err_count  = len(scraper_status["errors"])
        run_status = "failed" if run_failed else ("partial" if err_count else "success")
        _save_run(keyword, started_at, pages_scraped,
                  len(all_jobs), scraper_status["scraped"], err_count, run_status)
        if driver and not is_attached:
            driver.quit()
        scraper_status["running"] = False
        scraper_status["done"]    = True
        _sync_status()
