import time

def send_weekly_report(payload: dict):
    course_id = payload.get("course_id", "unknown")
    print(f"Generating report for course {course_id}...")
    time.sleep(2)
    return {
        "course_id": course_id,
        "students_processed": 30,
        "emails_sent": 30
    }

def backup_database(payload: dict):
    print("Starting database backup...")
    time.sleep(1)
    return {
        "backup_size": "2.4GB",
        "duration_seconds": 1
    }

def slow_job(payload: dict):
    print("Starting slow job, will take 60 seconds...")
    time.sleep(60)  # simulates a long running job
    return {"done": True}

def timeout_test(payload: dict):
    import time
    print("Starting a job that will timeout...")
    time.sleep(999)  # runs forever
    return {"done": True}