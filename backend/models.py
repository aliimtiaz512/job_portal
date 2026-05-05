import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, text
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
    location_type = Column(String(200))
    employment_type = Column(String(200))
    salary = Column(String(500))
    skills = Column(Text)
    about_job = Column(Text)
    job_url = Column(String(1000), unique=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "location_type": self.location_type,
            "employment_type": self.employment_type,
            "salary": self.salary,
            "skills": self.skills,
            "about_job": self.about_job,
            "job_url": self.job_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }


def init_db():
    Base.metadata.create_all(engine)
    # Migrate existing tables — add new columns if they don't exist yet
    new_cols = [("salary", "VARCHAR(500)"), ("skills", "TEXT")]
    with engine.connect() as conn:
        for col, col_type in new_cols:
            try:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN IF NOT EXISTS {col} {col_type}"))
                conn.commit()
            except Exception:
                conn.rollback()
