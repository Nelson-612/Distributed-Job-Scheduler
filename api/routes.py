from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Job
from api.models import JobRequest, JobResponse
from datetime import datetime
import uuid, redis

router = APIRouter()
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

@router.post("/jobs", response_model=JobResponse)
def submit_job(req: JobRequest, db: Session = Depends(get_db)):
    job = Job(
        id          = str(uuid.uuid4()),
        name        = req.name,
        handler     = req.handler,
        payload     = req.payload,
        schedule    = req.schedule,
        priority    = req.priority,
        max_retries = req.max_retries,
        timeout_sec = req.timeout_seconds,
        status      = "PENDING",
        next_run_at = datetime.utcnow() if not req.schedule else None
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if not req.schedule:
        r.zadd("job_queue", {job.id: job.priority})
        job.status = "QUEUED"
        db.commit()

    return JobResponse(
        job_id      = job.id,
        name        = job.name,
        status      = job.status,
        priority    = job.priority,
        schedule    = job.schedule,
        retry_count = job.retry_count,
        result      = job.result,
        created_at  = job.created_at
    )

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        job_id      = job.id,
        name        = job.name,
        status      = job.status,
        priority    = job.priority,
        schedule    = job.schedule,
        retry_count = job.retry_count,
        result      = job.result,
        created_at  = job.created_at
    )

@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return { "message": f"Job {job_id} deleted" }