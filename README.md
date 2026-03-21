# Distributed Job Scheduler

A production-style distributed job scheduler built in Python from scratch, inspired by systems like Google Cloud Scheduler, AWS EventBridge, and Celery. Submit a task, tell it when to run and how urgent it is — the system guarantees execution even when servers crash.

---

## Demo

Submit a job:
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weekly_report",
    "handler": "tasks.example.send_weekly_report",
    "payload": { "course_id": 42 },
    "priority": 3,
    "max_retries": 3,
    "timeout_seconds": 120
  }'
```

Check cluster health:
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "current_leader": "Nelsons-MacBook-Pro.local_70147",
  "jobs": {
    "queued": 0,
    "running": 1,
    "success": 42,
    "failed": 0
  },
  "dead_letter_queue": 0
}
```

---

## Architecture

```
Client
  │
  ▼
FastAPI (REST API)
  │
  ├──► PostgreSQL (job metadata, state, history)
  │
  └──► Redis (priority job queue)
         │
         ▼
    Worker Pool ──► Execute handler ──► Write result
         │
         └──► Heartbeat thread (every 5s)
                    │
                    ▼
           Scheduler cluster
           ┌─────────────────────────────┐
           │  Leader (holds Redis lock)  │
           │  - Polls for due cron jobs  │
           │  - Detects crashed workers  │
           │  - Reschedules completed    │
           └─────────────────────────────┘
           ┌──────────────┐  ┌──────────────┐
           │  Follower    │  │  Follower    │
           │  (standby)   │  │  (standby)   │
           └──────────────┘  └──────────────┘
```

---

## Features

### v1 — Single node scheduler
- REST API for job submission, inspection, and cancellation
- PostgreSQL metadata store tracking full job lifecycle
- Redis priority queue with atomic job dequeuing (ZPOPMIN)
- Dynamic handler loading — any Python function can be a job
- Full job state machine: PENDING → QUEUED → RUNNING → SUCCESS / FAILED
- Configurable retry logic with max attempts

### v2 — Fault tolerance
- Heartbeat pattern — workers send a pulse every 5 seconds while running
- Crash detection — scheduler detects stale heartbeats and requeues jobs
- Cron job scheduling — jobs trigger automatically based on cron expressions
- Auto-rescheduling — completed cron jobs calculate their next run time

### v3 — Distributed leader election
- Multiple scheduler nodes run simultaneously
- Leader election via Redis SET NX distributed lock with TTL
- Automatic failover — if the leader crashes, a follower takes over within 10 seconds
- Zero human intervention required

### v4 — Production polish
- List all jobs with status filtering (GET /jobs?status=FAILED)
- Cluster health endpoint showing leader, job counts, and DLQ size
- Job timeout enforcement — workers kill jobs exceeding timeout_seconds
- Dead letter queue — permanently failed jobs moved to DLQ for inspection
- Structured logging with timestamps and log levels throughout

---

## Tech Stack

| Component | Technology |
|---|---|
| API layer | FastAPI + Pydantic |
| Metadata store | PostgreSQL + SQLAlchemy |
| Job queue | Redis sorted set |
| Leader election | Redis SET NX distributed lock |
| Cron parsing | croniter |
| Runtime | Python 3.10+ |
| Infrastructure | Docker + Docker Compose |

---

## Getting Started

### Prerequisites
- Python 3.10+
- Docker Desktop

### Installation

```bash
# Clone the repo
git clone https://github.com/Nelson-612/Distributed-Job-Scheduler.git
cd Distributed-Job-Scheduler

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis and PostgreSQL
docker compose up -d

# Terminal 1 — API server
uvicorn api.main:app --reload

# Terminal 2 — Worker
python -m worker.worker

# Terminal 3 — Scheduler
python -m scheduler.loop
```

Open the API docs at `http://localhost:8000/docs`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /jobs | Submit a new job |
| GET | /jobs | List all jobs (filter by ?status=) |
| GET | /jobs/{id} | Get job status and result |
| DELETE | /jobs/{id} | Cancel a job |
| GET | /health | Cluster health and job counts |

---

## Key Engineering Decisions

**Why Redis for leader election instead of ZooKeeper?**
Redis was already in the stack for the job queue, keeping infrastructure simple. The SET NX command with TTL provides sufficient consistency guarantees for this use case. For stronger consistency under network partition, ZooKeeper or etcd would be the production choice.

**Why ZPOPMIN for job dequeuing?**
ZPOPMIN atomically pops the lowest-score (highest priority) job in a single Redis operation. This guarantees exactly one worker claims each job — no race conditions, no duplicate execution.

**Why 10-second TTL with 5-second renewal for the leader lock?**
A shorter TTL means faster failover but risks false positives — a slow-but-alive leader losing its lock due to a momentary network hiccup. 10 seconds balances availability with safety.

**Why PostgreSQL for metadata instead of Redis?**
Job history, retry counts, and execution results need durability across restarts. Redis is used for ephemeral queue state; PostgreSQL owns the source of truth.

---

## Concepts Demonstrated

| Concept | Implementation |
|---|---|
| Atomic operations | Redis ZPOPMIN — one worker per job guaranteed |
| Distributed consensus | Redis SET NX leader election |
| Fault tolerance | Heartbeat + crash detection + auto-requeue |
| State machines | PENDING → QUEUED → RUNNING → SUCCESS/FAILED |
| Idempotency | Retry-safe job handlers |
| Dead letter queue | Permanently failed jobs isolated for inspection |
| Observability | Structured logging + health endpoint |

---

## Roadmap

- [x] v1 — Single node scheduler with API, queue, and worker
- [x] v2 — Fault tolerance with heartbeats and crash detection
- [x] v3 — Distributed leader election with automatic failover
- [x] v4 — Production polish — health, timeouts, DLQ, logging
- [ ] Job dependencies — job B only runs after job A succeeds
- [ ] Rate limiting — configurable max concurrent jobs
- [ ] Monitoring dashboard — live job status UI
- [ ] Load testing — benchmark throughput and latency under stress

---

## Related Systems

This project is a simplified implementation of concepts used in:
- **Google** — Borg, Cloud Scheduler
- **Meta** — Async (internal task queue)
- **Amazon** — AWS SQS, Step Functions, EventBridge
- **Airbnb** — Apache Airflow
- **Uber** — Temporal (formerly Cadence)
- **LinkedIn** — Azkaban
