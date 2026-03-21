from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import Job
from api.models import JobRequest, JobResponse
from datetime import datetime, timezone
import uuid, redis, logging

logger = logging.getLogger(__name__)
router = APIRouter()
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

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
        next_run_at = utcnow() if not req.schedule else None
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if not req.schedule:
        r.zadd("job_queue", {job.id: job.priority})
        job.status = "QUEUED"
        db.commit()

    logger.info(f"Job submitted: {job.name} ({job.id})")
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

@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    status: str = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status.upper())
    jobs = query.order_by(Job.created_at.desc()).all()
    return [JobResponse(
        job_id      = j.id,
        name        = j.name,
        status      = j.status,
        priority    = j.priority,
        schedule    = j.schedule,
        retry_count = j.retry_count,
        result      = j.result,
        created_at  = j.created_at
    ) for j in jobs]

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
    logger.info(f"Job deleted: {job_id}")
    return { "message": f"Job {job_id} deleted" }

@router.get("/health")
def health(db: Session = Depends(get_db)):
    current_leader = r.get("scheduler:leader")
    queued  = db.query(Job).filter(Job.status == "QUEUED").count()
    running = db.query(Job).filter(Job.status == "RUNNING").count()
    success = db.query(Job).filter(Job.status == "SUCCESS").count()
    failed  = db.query(Job).filter(Job.status == "FAILED").count()
    dlq     = r.llen("dead_letter_queue")

    return {
        "status":         "ok",
        "current_leader": current_leader or "none",
        "jobs": {
            "queued":  queued,
            "running": running,
            "success": success,
            "failed":  failed,
        },
        "dead_letter_queue": dlq
    }