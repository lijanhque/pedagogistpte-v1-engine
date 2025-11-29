"""
Database models for persistent state (Postgres).
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True)
    student_id = Column(String, index=True)
    submission_type = Column(String)  # speaking, writing, etc.
    text = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ScoringJob(Base):
    __tablename__ = "scoring_jobs"

    job_id = Column(String, primary_key=True)
    assessment_id = Column(String, index=True)
    state = Column(String)  # pending, processing, scored, enriched, completed, failed
    scores = Column(JSON)  # {fluency, lexical_resource, etc.}
    section_score = Column(Float)
    model_used = Column(String)
    ai_features = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class ScoringAuditLog(Base):
    __tablename__ = "scoring_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, index=True)
    action = Column(String)  # created, scored, enriched, failed
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
