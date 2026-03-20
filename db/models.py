from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy.sql import func
from db.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id          = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    handler     = Column(String, nullable=False)
    payload     = Column(JSON, default={})
    schedule    = Column(String, nullable=True)
    priority    = Column(Integer, default=5)
    status      = Column(String, default="PENDING")
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    timeout_sec = Column(Integer, default=300)
    result      = Column(JSON, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, onupdate=func.now())