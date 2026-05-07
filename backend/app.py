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
from models import Job, ScraperRun, Session, init_db
from scraper import STATUS_FILE

app = FastAPI(title="LinkedIn Job Scraper API")

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

# Path to the standalone scraper script
_SCRAPER_SCRIPT = os.path.join(os.path.dirname(__file__), "run_scraper.py")

# Track the running subprocess
_proc: subprocess.Popen | None = None

_DEFAULT_STATUS = {
    "running": False, "progress": "", "total": 0,
    "scraped": 0, "errors": [], "done": False,
    "elapsed_seconds": 0, "daily_runs": 0, "daily_date": "",
}


def _read_status() -> dict:
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except Exception:
        return _DEFAULT_STATUS.copy()


def _is_running() -> bool:
    return _proc is not None and _proc.poll() is None


class ScrapeRequest(BaseModel):
    keyword: str
    date_posted: str = ""
    salary_range: str = ""


@app.post("/api/scrape")
def start_scrape(req: ScrapeRequest):
    global _proc
    if _is_running():
        raise HTTPException(status_code=409, detail="Scraper is already running.")

    # Launch as a completely separate Python process — no fork, no threads inherited.
    # This is identical to running the scraper from the terminal, which works reliably.
    _proc = subprocess.Popen(
        [sys.executable, _SCRAPER_SCRIPT, req.keyword, req.date_posted, req.salary_range],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        cwd=os.path.dirname(__file__),
    )
    return {"message": "Scraper started."}


@app.get("/api/status")
def get_status():
    return _read_status()


@app.get("/api/jobs")
def get_jobs():
    session = Session()
    try:
        return [j.to_dict() for j in session.query(Job).order_by(Job.id.desc()).all()]
    finally:
        session.close()


@app.delete("/api/jobs/clear")
def clear_jobs():
    session = Session()
    try:
        session.query(Job).delete()
        session.commit()
        return {"message": "All jobs cleared."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int):
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
            raise HTTPException(status_code=404, detail="No jobs to export.")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
