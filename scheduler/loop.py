import time
import redis
from datetime import datetime, timezone, timedelta
from db.database import SessionLocal
from db.models import Job
from croniter import croniter
import os
import socket

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

HEARTBEAT_TIMEOUT = 15
LEADER_KEY = "scheduler:leader"
LEADER_TTL = 10        # lock expires after 10 seconds
RENEW_INTERVAL = 5     # renew every 5 seconds

NODE_ID = socket.gethostname() + "_" + str(os.getpid())

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def try_become_leader():
    result = r.set(LEADER_KEY, NODE_ID, nx=True, ex=LEADER_TTL)
    return result is not None

def am_i_leader():
    return r.get(LEADER_KEY) == NODE_ID

def renew_leadership():
    if am_i_leader():
        r.expire(LEADER_KEY, LEADER_TTL)
        return True
    return False

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
    print(f"Scheduler node started: {NODE_ID}")
    while True:
        if try_become_leader() or am_i_leader():
            renew_leadership()
            print(f"[LEADER] {NODE_ID} is running...")
            db = SessionLocal()
            try:
                enqueue_due_jobs(db)
                detect_crashed_workers(db)
                reschedule_completed_jobs(db)
            finally:
                db.close()
        else:
            current_leader = r.get(LEADER_KEY)
            print(f"[FOLLOWER] {NODE_ID} standing by. Leader is: {current_leader}")

        time.sleep(RENEW_INTERVAL)

if __name__ == "__main__":
    run_scheduler()