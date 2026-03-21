import redis
import time
import importlib
import threading
import logging
from datetime import datetime, timezone
from db.database import SessionLocal
from db.models import Job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def get_handler(handler_path: str):
    module_path, func_name = handler_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)

def send_heartbeat(job_id: str, stop_event: threading.Event):
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.last_heartbeat = utcnow()
                db.commit()
        finally:
            db.close()
        stop_event.wait(5)

def process_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = "RUNNING"
        job.last_heartbeat = utcnow()
        job.updated_at = utcnow()
        db.commit()
        logger.info(f"Running job: {job.name} ({job_id})")

        stop_event = threading.Event()
        heartbeat_thread = threading.Thread(
            target=send_heartbeat,
            args=(job_id, stop_event),
            daemon=True
        )
        heartbeat_thread.start()

        result = [None]
        error  = [None]

        def run_handler():
            try:
                handler = get_handler(job.handler)
                result[0] = handler(job.payload)
            except Exception as e:
                error[0] = e

        handler_thread = threading.Thread(target=run_handler)
        handler_thread.start()
        handler_thread.join(timeout=job.timeout_sec)

        stop_event.set()

        if handler_thread.is_alive():
            # job timed out
            logger.warning(f"Job {job.name} timed out after {job.timeout_sec}s")
            job = db.query(Job).filter(Job.id == job_id).first()
            job.retry_count += 1
            if job.retry_count >= job.max_retries:
                job.status = "FAILED"
                job.result = {"error": "Job timed out, max retries exceeded"}
                r.lpush("dead_letter_queue", job_id)
                logger.error(f"Job {job.name} moved to dead letter queue")
            else:
                job.status = "PENDING"
                r.zadd("job_queue", {job.id: job.priority})
                logger.info(f"Job {job.name} requeued after timeout ({job.retry_count}/{job.max_retries})")
            db.commit()
            return

        if error[0]:
            raise error[0]

        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "SUCCESS"
        job.result = result[0]
        job.updated_at = utcnow()
        db.commit()
        logger.info(f"Job {job.name} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} error: {e}")
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.retry_count += 1
            if job.retry_count >= job.max_retries:
                job.status = "FAILED"
                job.result = {"error": str(e)}
                r.lpush("dead_letter_queue", job_id)
                logger.error(f"Job {job.name} moved to dead letter queue")
            else:
                job.status = "PENDING"
                r.zadd("job_queue", {job.id: job.priority})
                logger.info(f"Job {job.name} retrying ({job.retry_count}/{job.max_retries})")
            db.commit()
    finally:
        db.close()

def run_worker():
    logger.info("Worker started, waiting for jobs...")
    while True:
        result = r.zpopmin("job_queue", 1)
        if result:
            job_id = result[0][0]
            process_job(job_id)
        else:
            time.sleep(1)

if __name__ == "__main__":
    run_worker()