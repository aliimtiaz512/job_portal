import os
import time
import random
import logging
from urllib.parse import quote_plus
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from models import Job, Session, init_db

load_dotenv()

if not os.environ.get("DISPLAY"):
    os.environ["DISPLAY"] = ":0"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

scraper_status = {
    "running": False,
    "progress": "",
    "total": 0,
    "scraped": 0,
    "errors": [],
    "done": False,
}


def human_delay(min_sec=1.5, max_sec=3.5):
    time.sleep(random.uniform(min_sec, max_sec))


def build_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def linkedin_login(driver):
    logger.info("Navigating to LinkedIn login page...")
    scraper_status["progress"] = "Logging in to LinkedIn..."
    driver.get("https://www.linkedin.com/login")
    wait = WebDriverWait(driver, 20)

    email_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    human_delay(1, 2)
    email_field.clear()
    email_field.send_keys(LINKEDIN_EMAIL)

    human_delay(0.5, 1.5)
    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys(LINKEDIN_PASSWORD)

    human_delay(0.5, 1.5)
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


def navigate_to_jobs(driver, keyword: str, date_posted: str = "", salary_range: str = ""):
    logger.info(f"Searching LinkedIn jobs: keyword='{keyword}'")
    scraper_status["progress"] = f"Searching LinkedIn for '{keyword}'..."

    params = [
        f"keywords={quote_plus(keyword)}",
        "location=United+States",
        "f_WT=2",
    ]
    if date_posted:
        params.append(f"f_TPR={date_posted}")
    if salary_range:
        params.append(f"f_SB2={salary_range}")

    url = "https://www.linkedin.com/jobs/search/?" + "&".join(params)
    logger.info(f"Navigating to: {url}")
    driver.get(url)
    human_delay(3, 5)


def collect_job_urls(driver):
    logger.info("Collecting job card URLs from page 1...")
    scraper_status["progress"] = "Collecting job listings from page 1..."
    wait = WebDriverWait(driver, 20)

    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ul.jobs-search__results-list, div.jobs-search-results-list")
            )
        )
    except TimeoutException:
        logger.warning("Jobs list container not found, trying anyway...")

    human_delay(2, 3)

    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        human_delay(1, 2)
    driver.execute_script("window.scrollTo(0, 0);")
    human_delay(1, 2)

    selectors = [
        "a.job-card-list__title--link",
        "a.job-card-container__link",
        "div.job-card-container a[href*='/jobs/view/']",
        "ul.jobs-search__results-list li a[href*='/jobs/view/']",
        "a[href*='/jobs/view/']",
    ]

    job_urls = []
    for selector in selectors:
        links = driver.find_elements(By.CSS_SELECTOR, selector)
        for link in links:
            href = link.get_attribute("href")
            if href and "/jobs/view/" in href:
                base = href.split("?")[0].rstrip("/")
                if base not in job_urls:
                    job_urls.append(base)
        if job_urls:
            break

    logger.info(f"Found {len(job_urls)} job URLs.")
    return job_urls


def extract_text(driver, selectors, attribute=None):
    for selector in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            if attribute:
                return (el.get_attribute(attribute) or "").strip()
            return el.text.strip()
        except NoSuchElementException:
            continue
    return ""


def extract_job_details_fields(driver):
    result = {
        "employment_type": "",
        "location_type": "",
        "skills": "",
        "about_job": "",
    }

    try:
        details_el = driver.find_element(By.CSS_SELECTOR, "#job-details")
    except NoSuchElementException:
        return result

    result["about_job"] = details_el.text.strip()

    label_field_map = {
        "type": "employment_type",
        "employment type": "employment_type",
        "job type": "employment_type",
        "position type": "employment_type",
        "location": "location_type",
        "work location": "location_type",
        "workplace type": "location_type",
    }

    try:
        strongs = details_el.find_elements(By.TAG_NAME, "strong")
        for strong in strongs:
            raw_label = strong.text.strip().rstrip(":")
            label_lower = raw_label.lower()
            field = label_field_map.get(label_lower)
            if not field or result[field]:
                continue

            try:
                container = strong.find_element(By.XPATH, "ancestor::p[1]")
            except NoSuchElementException:
                try:
                    container = strong.find_element(By.XPATH, "..")
                except NoSuchElementException:
                    continue

            full_text = container.text.strip()
            if ":" in full_text:
                value = full_text.split(":", 1)[1].strip()
                if value:
                    result[field] = value
    except Exception as e:
        logger.warning(f"DOM extraction of #job-details fields failed: {e}")

    try:
        skills_header = details_el.find_element(By.CSS_SELECTOR, ".js-skills-header")
        skills_p = skills_header.find_element(By.XPATH, "following-sibling::p[1]")
        result["skills"] = skills_p.text.strip()
    except NoSuchElementException:
        pass

    return result


def scrape_job_detail(driver, job_url, main_handle):
    driver.execute_script(f"window.open('{job_url}', '_blank');")
    human_delay(1, 2)

    new_handle = [h for h in driver.window_handles if h != main_handle][-1]
    driver.switch_to.window(new_handle)

    wait = WebDriverWait(driver, 25)
    try:
        wait.until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1")),
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name")
                ),
            )
        )
    except TimeoutException:
        logger.warning(f"Timeout loading job page: {job_url}")

    human_delay(2, 3)

    job_title = ""
    try:
        title_el = driver.find_element(
            By.XPATH, "//p[.//svg[@id='verified-medium']]"
        )
        job_title = driver.execute_script(
            "var n=arguments[0].firstChild;"
            "return n ? n.textContent.trim() : '';",
            title_el,
        )
    except (NoSuchElementException, Exception):
        pass

    if not job_title:
        try:
            title_els = driver.find_elements(
                By.XPATH,
                "//div[contains(@class,'job-details-jobs-unified-top-card')]"
                "//p[not(ancestor::div[@id='job-details'])]",
            )
            for el in title_els[:5]:
                t = driver.execute_script(
                    "var n=arguments[0].firstChild;"
                    "return n ? n.textContent.trim() : arguments[0].textContent.trim();",
                    el,
                )
                if t and 3 < len(t) < 200:
                    job_title = t
                    break
        except Exception:
            pass

    if not job_title:
        job_title = extract_text(driver, [
            ".job-details-jobs-unified-top-card__job-title h1",
            ".job-details-jobs-unified-top-card__job-title",
            "div.display-flex.justify-space-between.flex-wrap.mt2 h1",
            ".jobs-unified-top-card__job-title h1",
            ".jobs-unified-top-card__job-title",
            "h1.t-24.t-bold",
            "h1",
        ])

    company_name = extract_text(driver, [
        ".job-details-jobs-unified-top-card__company-name a",
        ".job-details-jobs-unified-top-card__company-name",
        ".jobs-unified-top-card__company-name a",
        ".jobs-unified-top-card__company-name",
        "div.display-flex.align-items-center a.app-aware-link",
        ".topcard__org-name-link",
    ])

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    human_delay(1, 2)
    driver.execute_script("window.scrollTo(0, 0);")

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#job-details")))
        details_el = driver.find_element(By.CSS_SELECTOR, "#job-details")
        driver.execute_script("arguments[0].scrollIntoView(true);", details_el)
        human_delay(1.5, 2.5)

        try:
            show_more = details_el.find_element(
                By.CSS_SELECTOR,
                "button[aria-label*='show more'], button.jobs-description__footer-button, "
                ".jobs-description__details button",
            )
            driver.execute_script("arguments[0].click();", show_more)
            human_delay(1, 2)
        except NoSuchElementException:
            pass
    except TimeoutException:
        logger.warning(f"#job-details not found on {job_url}")

    fields = extract_job_details_fields(driver)
    employment_type = fields["employment_type"]
    location_type = fields["location_type"]
    skills = fields["skills"]
    about_job = fields["about_job"]

    if not employment_type or not location_type:
        spans = driver.find_elements(
            By.CSS_SELECTOR,
            ".jobs-unified-top-card__job-insight span, "
            ".job-details-jobs-unified-top-card__job-insight span",
        )
        remote_kw = {"remote", "hybrid", "on-site", "onsite", "in-person"}
        time_kw = {"full-time", "part-time", "contract", "internship", "temporary"}
        for span in spans:
            txt = span.text.strip()
            low = txt.lower()
            if any(kw in low for kw in remote_kw) and not location_type:
                location_type = txt
            if any(kw in low for kw in time_kw) and not employment_type:
                employment_type = txt

    if not employment_type or not location_type:
        prefs = extract_text(driver, [
            ".job-details-fit-level-preferences",
            ".jobs-unified-top-card__workplace-type",
            ".job-details-jobs-unified-top-card__workplace-type",
        ])
        if prefs:
            remote_kw = {"remote", "hybrid", "on-site", "onsite", "in-person"}
            time_kw = {"full-time", "part-time", "contract", "internship", "temporary"}
            for part in [p.strip() for p in prefs.split("\n") if p.strip()]:
                low = part.lower()
                if any(kw in low for kw in remote_kw) and not location_type:
                    location_type = part
                if any(kw in low for kw in time_kw) and not employment_type:
                    employment_type = part

    if not about_job:
        about_job = extract_text(driver, [
            ".jobs-description-content__text",
            ".jobs-description__content",
            ".jobs-description",
        ])

    driver.close()
    driver.switch_to.window(main_handle)
    human_delay(1, 2)

    return {
        "job_title": job_title or "N/A",
        "company_name": company_name or "N/A",
        "location_type": location_type or "N/A",
        "employment_type": employment_type or "N/A",
        "skills": skills or "N/A",
        "about_job": about_job or "N/A",
        "job_url": job_url,
    }


def save_job(data):
    session = Session()
    try:
        existing = session.query(Job).filter_by(job_url=data["job_url"]).first()
        if existing:
            updated = False
            for field in ("employment_type", "location_type", "skills", "about_job"):
                new_val = data.get(field, "")
                old_val = getattr(existing, field, "") or ""
                if new_val and new_val != "N/A" and (not old_val or old_val == "N/A"):
                    setattr(existing, field, new_val)
                    updated = True
            if updated:
                session.commit()
                logger.info(f"Updated: {data['job_title']} @ {data['company_name']}")
            else:
                logger.info(f"Skipping duplicate: {data['job_url']}")
            return
        job = Job(**data)
        session.add(job)
        session.commit()
        logger.info(f"Saved: {data['job_title']} @ {data['company_name']}")
    except Exception as e:
        session.rollback()
        logger.error(f"DB error: {e}")
    finally:
        session.close()


def run_scraper(keyword: str = "AI ML jobs", date_posted: str = "", salary_range: str = ""):
    global scraper_status

    scraper_status.update({
        "running": True,
        "progress": "Starting...",
        "total": 0,
        "scraped": 0,
        "errors": [],
        "done": False,
    })

    init_db()
    driver = None
    try:
        driver = build_driver()
        linkedin_login(driver)
        navigate_to_jobs(driver, keyword, date_posted, salary_range)

        main_handle = driver.current_window_handle
        job_urls = collect_job_urls(driver)

        scraper_status["total"] = len(job_urls)
        if not job_urls:
            scraper_status["progress"] = "No jobs found. Check login or search."
            scraper_status["done"] = True
            scraper_status["running"] = False
            return

        for i, url in enumerate(job_urls, 1):
            scraper_status["progress"] = f"Scraping job {i}/{len(job_urls)}..."
            try:
                data = scrape_job_detail(driver, url, main_handle)
                save_job(data)
                scraper_status["scraped"] = i
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                scraper_status["errors"].append(str(e))
            human_delay(1, 2)

        scraper_status["progress"] = f"Done! Scraped {scraper_status['scraped']} jobs."

    except Exception as e:
        logger.error(f"Scraper error: {e}")
        scraper_status["progress"] = f"Error: {e}"
        scraper_status["errors"].append(str(e))
    finally:
        if driver:
            driver.quit()
        scraper_status["running"] = False
        scraper_status["done"] = True
