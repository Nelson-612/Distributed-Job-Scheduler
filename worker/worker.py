import redis
import json
import time
import importlib
from datetime import datetime, timezone
from db.database import SessionLocal
from db.models import Job

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def get_handler(handler_path: str):
    module_path, func_name = handler_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)

def process_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            print(f"Job {job_id} not found")
            return

        job.status = "RUNNING"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        print(f"Running job: {job.name} ({job_id})")

        handler = get_handler(job.handler)
        result = handler(job.payload)

        job.status = "SUCCESS"
        job.result = result
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        print(f"Job {job.name} completed successfully")

    except Exception as e:
        print(f"Error: {e}")   # this will show us the real error
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.retry_count += 1
            if job.retry_count >= job.max_retries:
                job.status = "FAILED"
                job.result = {"error": str(e)}
                print(f"Job {job.name} failed after {job.retry_count} retries")
            else:
                job.status = "PENDING"
                r.zadd("job_queue", {job.id: job.priority})
                print(f"Job {job.name} retrying ({job.retry_count}/{job.max_retries})")
            db.commit()
    finally:
        db.close()

def run_worker():
    print("Worker started, waiting for jobs...")
    while True:
        result = r.zpopmin("job_queue", 1)
        if result:
            job_id = result[0][0]
            process_job(job_id)
        else:
            time.sleep(1)

if __name__ == "__main__":
    run_worker()