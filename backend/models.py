import os
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/job")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title = Column(String(500))
    company_name = Column(String(500))
    job_url = Column(String(1000), unique=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "job_url": self.job_url,
        }


class StartupJob(Base):
    __tablename__ = "startup_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title = Column(String(500))
    company_name = Column(String(500))
    job_url = Column(String(1000), unique=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "job_url": self.job_url,
        }


class IndeedJob(Base):
    __tablename__ = "indeed_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title = Column(String(500))
    company_name = Column(String(500))
    job_url = Column(String(1000), unique=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "job_url": self.job_url,
        }


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    scraper          = Column(String(50), default="linkedin")
    keyword          = Column(String(500))
    started_at       = Column(String(50))
    finished_at      = Column(String(50))
    duration_seconds = Column(Integer)
    pages_scraped    = Column(Integer)
    jobs_found       = Column(Integer)
    jobs_saved       = Column(Integer)
    error_count      = Column(Integer)
    run_status       = Column(String(20))

    def to_dict(self):
        return {
            "id":               self.id,
            "scraper":          self.scraper or "linkedin",
            "keyword":          self.keyword,
            "started_at":       self.started_at,
            "finished_at":      self.finished_at,
            "duration_seconds": self.duration_seconds,
            "pages_scraped":    self.pages_scraped,
            "jobs_found":       self.jobs_found,
            "jobs_saved":       self.jobs_saved,
            "error_count":      self.error_count,
            "run_status":       self.run_status,
        }


def init_db():
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        # Drop leftover columns from old LinkedIn scraper versions
        for col in ("location_type", "employment_type", "skills", "about_job"):
            try:
                conn.execute(text(f"ALTER TABLE jobs DROP COLUMN IF EXISTS {col}"))
                conn.commit()
            except Exception:
                conn.rollback()

        # Add scraper column to existing scraper_runs table (migration)
        try:
            conn.execute(text(
                "ALTER TABLE scraper_runs ADD COLUMN IF NOT EXISTS scraper VARCHAR(50) DEFAULT 'linkedin'"
            ))
            conn.commit()
        except Exception:
            conn.rollback()
