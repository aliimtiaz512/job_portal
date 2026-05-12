import io
import json
import os
import subprocess
import sys
import pandas as pd
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from models import Job, StartupJob, IndeedJob, DiceJob, AdzunaJob, ScraperRun, Session, init_db
from scrapers.linkedin import STATUS_FILE as LINKEDIN_STATUS_FILE
from scrapers.startupjobs import STATUS_FILE as STARTUPJOBS_STATUS_FILE
from scrapers.indeed import STATUS_FILE as INDEED_STATUS_FILE
from scrapers.dice import STATUS_FILE as DICE_STATUS_FILE
from scrapers.adzuna import STATUS_FILE as ADZUNA_STATUS_FILE

app = FastAPI(title="Job Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    init_db()
except Exception as e:
    print(f"[WARNING] DB init failed: {e}")

_LINKEDIN_SCRIPT    = os.path.join(os.path.dirname(__file__), "scrapers", "linkedin",    "runner.py")
_STARTUPJOBS_SCRIPT = os.path.join(os.path.dirname(__file__), "scrapers", "startupjobs", "runner.py")
_INDEED_SCRIPT      = os.path.join(os.path.dirname(__file__), "scrapers", "indeed",      "runner.py")
_DICE_SCRIPT        = os.path.join(os.path.dirname(__file__), "scrapers", "dice",        "runner.py")
_ADZUNA_SCRIPT      = os.path.join(os.path.dirname(__file__), "scrapers", "adzuna",      "runner.py")

_proc_linkedin:    subprocess.Popen | None = None
_proc_startupjobs: subprocess.Popen | None = None
_proc_indeed:      subprocess.Popen | None = None
_proc_dice:        subprocess.Popen | None = None
_proc_adzuna:      subprocess.Popen | None = None

_DEFAULT_STATUS = {
    "running": False, "progress": "", "total": 0,
    "scraped": 0, "errors": [], "done": False,
    "elapsed_seconds": 0, "daily_runs": 0, "daily_date": "",
}


def _read_status(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return _DEFAULT_STATUS.copy()


def _is_running(proc: subprocess.Popen | None) -> bool:
    return proc is not None and proc.poll() is None


# ── Request models ────────────────────────────────────────────────────────────

class LinkedInScrapeRequest(BaseModel):
    keyword: str
    date_posted: str = ""
    salary_range: str = ""


class StartupJobsScrapeRequest(BaseModel):
    keyword: str
    job_type: str = ""
    salary: str = ""
    time_filter: str = ""


class IndeedScrapeRequest(BaseModel):
    keyword: str
    pay: str = ""
    job_type: str = ""
    date_posted: str = ""


class DiceScrapeRequest(BaseModel):
    keyword: str
    date_posted: str = ""
    employment_type: str = ""


class AdzunaScrapeRequest(BaseModel):
    keyword: str
    location: str = ""
    max_days_old: str = ""
    contract_type: str = ""


# ── LinkedIn endpoints ────────────────────────────────────────────────────────

@app.post("/api/scrape")
def start_linkedin_scrape(req: LinkedInScrapeRequest):
    global _proc_linkedin
    if _is_running(_proc_linkedin):
        raise HTTPException(status_code=409, detail="LinkedIn scraper is already running.")

    _proc_linkedin = subprocess.Popen(
        [sys.executable, _LINKEDIN_SCRIPT, req.keyword, req.date_posted, req.salary_range],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        cwd=os.path.dirname(__file__),
    )
    return {"message": "LinkedIn scraper started."}


@app.get("/api/status")
def get_linkedin_status():
    return _read_status(LINKEDIN_STATUS_FILE)


@app.get("/api/jobs")
def get_linkedin_jobs():
    session = Session()
    try:
        return [j.to_dict() for j in session.query(Job).order_by(Job.id.desc()).all()]
    finally:
        session.close()


@app.delete("/api/jobs/clear")
def clear_linkedin_jobs():
    session = Session()
    try:
        session.query(Job).delete()
        session.commit()
        return {"message": "All LinkedIn jobs cleared."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.delete("/api/jobs/{job_id}")
def delete_linkedin_job(job_id: int):
    session = Session()
    try:
        job = session.query(Job).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        session.delete(job)
        session.commit()
        return {"message": "Deleted."}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# ── Startup Jobs endpoints ────────────────────────────────────────────────────

@app.post("/api/scrape/startupjobs")
def start_startupjobs_scrape(req: StartupJobsScrapeRequest):
    global _proc_startupjobs
    if _is_running(_proc_startupjobs):
        raise HTTPException(status_code=409, detail="Startup Jobs scraper is already running.")

    _proc_startupjobs = subprocess.Popen(
        [sys.executable, _STARTUPJOBS_SCRIPT,
         req.keyword, req.job_type, req.salary, req.time_filter],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        cwd=os.path.dirname(__file__),
    )
    return {"message": "Startup Jobs scraper started."}


@app.get("/api/status/startupjobs")
def get_startupjobs_status():
    return _read_status(STARTUPJOBS_STATUS_FILE)


@app.get("/api/jobs/startupjobs")
def get_startup_jobs():
    session = Session()
    try:
        return [j.to_dict() for j in session.query(StartupJob).order_by(StartupJob.id.desc()).all()]
    finally:
        session.close()


@app.delete("/api/jobs/startupjobs/clear")
def clear_startup_jobs():
    session = Session()
    try:
        session.query(StartupJob).delete()
        session.commit()
        return {"message": "All Startup Jobs cleared."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.delete("/api/jobs/startupjobs/{job_id}")
def delete_startup_job(job_id: int):
    session = Session()
    try:
        job = session.query(StartupJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        session.delete(job)
        session.commit()
        return {"message": "Deleted."}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# ── Indeed endpoints ─────────────────────────────────────────────────────────

@app.post("/api/scrape/indeed")
def start_indeed_scrape(req: IndeedScrapeRequest):
    global _proc_indeed
    if _is_running(_proc_indeed):
        raise HTTPException(status_code=409, detail="Indeed scraper is already running.")

    _proc_indeed = subprocess.Popen(
        [sys.executable, _INDEED_SCRIPT,
         req.keyword, req.pay, req.job_type, req.date_posted],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        cwd=os.path.dirname(__file__),
    )
    return {"message": "Indeed scraper started."}


@app.get("/api/status/indeed")
def get_indeed_status():
    return _read_status(INDEED_STATUS_FILE)


@app.get("/api/jobs/indeed")
def get_indeed_jobs():
    session = Session()
    try:
        return [j.to_dict() for j in session.query(IndeedJob).order_by(IndeedJob.id.desc()).all()]
    finally:
        session.close()


@app.delete("/api/jobs/indeed/clear")
def clear_indeed_jobs():
    session = Session()
    try:
        session.query(IndeedJob).delete()
        session.commit()
        return {"message": "All Indeed jobs cleared."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.delete("/api/jobs/indeed/{job_id}")
def delete_indeed_job(job_id: int):
    session = Session()
    try:
        job = session.query(IndeedJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        session.delete(job)
        session.commit()
        return {"message": "Deleted."}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/export/indeed/csv")
def export_indeed_csv():
    session = Session()
    try:
        jobs = session.query(IndeedJob).order_by(IndeedJob.id.desc()).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No Indeed jobs to export.")
        df = pd.DataFrame([j.to_dict() for j in jobs])
        df.drop(columns=["id"], inplace=True, errors="ignore")
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=indeed_jobs.csv"},
        )
    finally:
        session.close()


# ── Dice endpoints ───────────────────────────────────────────────────────────

@app.post("/api/scrape/dice")
def start_dice_scrape(req: DiceScrapeRequest):
    global _proc_dice
    if _is_running(_proc_dice):
        raise HTTPException(status_code=409, detail="Dice scraper is already running.")

    _proc_dice = subprocess.Popen(
        [sys.executable, _DICE_SCRIPT,
         req.keyword, req.date_posted, req.employment_type],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        cwd=os.path.dirname(__file__),
    )
    return {"message": "Dice scraper started."}


@app.get("/api/status/dice")
def get_dice_status():
    return _read_status(DICE_STATUS_FILE)


@app.get("/api/jobs/dice")
def get_dice_jobs():
    session = Session()
    try:
        return [j.to_dict() for j in session.query(DiceJob).order_by(DiceJob.id.desc()).all()]
    finally:
        session.close()


@app.delete("/api/jobs/dice/clear")
def clear_dice_jobs():
    session = Session()
    try:
        session.query(DiceJob).delete()
        session.commit()
        return {"message": "All Dice jobs cleared."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.delete("/api/jobs/dice/{job_id}")
def delete_dice_job(job_id: int):
    session = Session()
    try:
        job = session.query(DiceJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        session.delete(job)
        session.commit()
        return {"message": "Deleted."}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/export/dice/csv")
def export_dice_csv():
    session = Session()
    try:
        jobs = session.query(DiceJob).order_by(DiceJob.id.desc()).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No Dice jobs to export.")
        df = pd.DataFrame([j.to_dict() for j in jobs])
        df.drop(columns=["id"], inplace=True, errors="ignore")
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=dice_jobs.csv"},
        )
    finally:
        session.close()


# ── Adzuna endpoints ─────────────────────────────────────────────────────────

@app.post("/api/scrape/adzuna")
def start_adzuna_scrape(req: AdzunaScrapeRequest):
    global _proc_adzuna
    if _is_running(_proc_adzuna):
        raise HTTPException(status_code=409, detail="Adzuna scraper is already running.")

    _proc_adzuna = subprocess.Popen(
        [sys.executable, _ADZUNA_SCRIPT,
         req.keyword, req.location, req.max_days_old, req.contract_type],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        cwd=os.path.dirname(__file__),
    )
    return {"message": "Adzuna scraper started."}


@app.get("/api/status/adzuna")
def get_adzuna_status():
    return _read_status(ADZUNA_STATUS_FILE)


@app.get("/api/jobs/adzuna")
def get_adzuna_jobs():
    session = Session()
    try:
        return [j.to_dict() for j in session.query(AdzunaJob).order_by(AdzunaJob.id.desc()).all()]
    finally:
        session.close()


@app.delete("/api/jobs/adzuna/clear")
def clear_adzuna_jobs():
    session = Session()
    try:
        session.query(AdzunaJob).delete()
        session.commit()
        return {"message": "All Adzuna jobs cleared."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.delete("/api/jobs/adzuna/{job_id}")
def delete_adzuna_job(job_id: int):
    session = Session()
    try:
        job = session.query(AdzunaJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")
        session.delete(job)
        session.commit()
        return {"message": "Deleted."}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/export/adzuna/csv")
def export_adzuna_csv():
    session = Session()
    try:
        jobs = session.query(AdzunaJob).order_by(AdzunaJob.id.desc()).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No Adzuna jobs to export.")
        df = pd.DataFrame([j.to_dict() for j in jobs])
        df.drop(columns=["id"], inplace=True, errors="ignore")
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=adzuna_jobs.csv"},
        )
    finally:
        session.close()


# ── Shared endpoints ──────────────────────────────────────────────────────────

@app.get("/api/runs")
def get_runs():
    session = Session()
    try:
        runs = (
            session.query(ScraperRun)
            .order_by(ScraperRun.id.desc())
            .limit(50)
            .all()
        )
        return [r.to_dict() for r in runs]
    finally:
        session.close()


@app.get("/api/export/csv")
def export_csv():
    session = Session()
    try:
        jobs = session.query(Job).order_by(Job.id.desc()).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No LinkedIn jobs to export.")
        df = pd.DataFrame([j.to_dict() for j in jobs])
        df.drop(columns=["id"], inplace=True, errors="ignore")
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=linkedin_jobs.csv"},
        )
    finally:
        session.close()


@app.get("/api/export/startupjobs/csv")
def export_startupjobs_csv():
    session = Session()
    try:
        jobs = session.query(StartupJob).order_by(StartupJob.id.desc()).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No Startup Jobs to export.")
        df = pd.DataFrame([j.to_dict() for j in jobs])
        df.drop(columns=["id"], inplace=True, errors="ignore")
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=startup_jobs.csv"},
        )
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
