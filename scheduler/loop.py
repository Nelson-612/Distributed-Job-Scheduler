import time
import redis
from datetime import datetime, timezone, timedelta
from db.database import SessionLocal
from db.models import Job
from croniter import croniter

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

HEARTBEAT_TIMEOUT = 15

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def enqueue_due_jobs(db):
    now = utcnow()
    due_jobs = db.query(Job).filter(
        Job.schedule != None,
        Job.status == "PENDING",
        Job.next_run_at <= now
    ).all()

    for job in due_jobs:
        r.zadd("job_queue", {job.id: job.priority})
        job.status = "QUEUED"
        db.commit()
        print(f"Enqueued cron job: {job.name}")

def detect_crashed_workers(db):
    timeout_threshold = utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT)
    stuck_jobs = db.query(Job).filter(
        Job.status == "RUNNING",
        Job.last_heartbeat <= timeout_threshold
    ).all()

    for job in stuck_jobs:
        print(f"Detected crashed worker for job: {job.name} — requeuing")
        job.retry_count += 1
        if job.retry_count >= job.max_retries:
            job.status = "FAILED"
            job.result = {"error": "Worker crashed, max retries exceeded"}
            print(f"Job {job.name} permanently failed")
        else:
            job.status = "PENDING"
            r.zadd("job_queue", {job.id: job.priority})
            print(f"Job {job.name} requeued (retry {job.retry_count}/{job.max_retries})")
        db.commit()

def reschedule_completed_jobs(db):
    done_jobs = db.query(Job).filter(
        Job.schedule != None,
        Job.status == "SUCCESS"
    ).all()

    for job in done_jobs:
        cron = croniter(job.schedule, utcnow())
        job.next_run_at = cron.get_next(datetime)
        job.status = "PENDING"
        job.result = None
        db.commit()
        print(f"Rescheduled {job.name} for {job.next_run_at}")

def run_scheduler():
    print("Scheduler started...")
    while True:
        db = SessionLocal()
        try:
            enqueue_due_jobs(db)
            detect_crashed_workers(db)
            reschedule_completed_jobs(db)
        finally:
            db.close()
        time.sleep(5)

if __name__ == "__main__":
    run_scheduler()