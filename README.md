# Distributed Job Scheduler

A production-style distributed job scheduler built in Python, inspired by systems like Google Cloud Scheduler, AWS EventBridge, and Celery.

## Architecture

- **API layer** — FastAPI REST API for submitting, inspecting, and cancelling jobs
- **Job queue** — Redis sorted set for priority-based job queuing
- **Metadata store** — PostgreSQL for job state, schedule, and execution history
- **Worker pool** — Independent workers that atomically pop and execute jobs
- **Retry logic** — Automatic retry with configurable max attempts

## Tech Stack

- Python 3.14
- FastAPI + Pydantic
- PostgreSQL + SQLAlchemy
- Redis
- Docker + Docker Compose

## Getting Started

### Prerequisites
- Python 3.10+
- Docker Desktop

### Installation

1. Clone the repo
   git clone https://github.com/Nelson-612/Distributed-Job-Scheduler.git
   cd Distributed-Job-Scheduler

2. Create virtual environment
   python -m venv venv
   source venv/bin/activate

3. Install dependencies
   pip install -r requirements.txt

4. Start Redis and PostgreSQL
   docker compose up -d

5. Start the API server
   uvicorn api.main:app --reload

6. Start the worker (new terminal)
   python -m worker.worker

7. Open the API docs
   http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /jobs | Submit a new job |
| GET | /jobs/{id} | Get job status and result |
| DELETE | /jobs/{id} | Cancel a job |
| GET | /health | Health check |

## Example Job Submission

POST /jobs
{
  "name": "weekly_student_report",
  "handler": "tasks.example.send_weekly_report",
  "payload": { "course_id": 42 },
  "priority": 3,
  "max_retries": 3,
  "timeout_seconds": 120
}

## Roadmap

- [x] v1 - Single node scheduler with API, queue, and worker
- [ ] v2 - Fault tolerance, heartbeats, crash detection
- [ ] v3 - Distributed scheduler with leader election
- [ ] v4 - Monitoring dashboard, benchmarks, load testing
