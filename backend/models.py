import os
from sqlalchemy import create_engine, Column, Integer, String, Text, text
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
    skills = Column(Text)
    about_job = Column(Text)
    job_url = Column(String(1000), unique=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_title": self.job_title,
            "company_name": self.company_name,
            "location_type": self.location_type,
            "employment_type": self.employment_type,
            "skills": self.skills,
            "about_job": self.about_job,
            "job_url": self.job_url,
        }


def init_db():
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills TEXT"))
            conn.commit()
        except Exception:
            conn.rollback()
