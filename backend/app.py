import io
import threading
import pandas as pd
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from models import Job, Session, init_db
from scraper import run_scraper, scraper_status

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
    print(f"[WARNING] DB init failed — check DATABASE_URL in .env: {e}")


class ScrapeRequest(BaseModel):
    keyword: str
    date_posted: str = ""
    salary_range: str = ""


@app.post("/api/scrape")
def start_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks = BackgroundTasks()):
    if scraper_status["running"]:
        raise HTTPException(status_code=409, detail="Scraper is already running.")
    background_tasks.add_task(run_scraper, req.keyword, req.date_posted, req.salary_range)
    return {"message": "Scraper started."}


@app.get("/api/status")
def get_status():
    return scraper_status


@app.get("/api/jobs")
def get_jobs():
    session = Session()
    try:
        jobs = session.query(Job).order_by(Job.id.desc()).all()
        return [j.to_dict() for j in jobs]
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


@app.get("/api/export/csv")
def export_csv():
    session = Session()
    try:
        jobs = session.query(Job).order_by(Job.id.desc()).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs to export.")

        data = [j.to_dict() for j in jobs]
        df = pd.DataFrame(data)
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
