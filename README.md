# Inceptrix - Red Team Scan Engine

Automated security scanning platform with strict state machine lifecycle management.

## Architecture

```
┌─────────────┐     POST /scan      ┌─────────────┐
│   Client    │ ──────────────────► │   FastAPI   │
└─────────────┘                     │  (main.py)  │
      ▲                             └──────┬──────┘
      │ GET /status, /report               │
      │                                    │ dispatch task
      │                                    ▼
      │                             ┌─────────────┐
      │                             │    Redis    │ ◄── State Storage
      │                             │  (6379)     │     + Celery Broker
      │                             └──────┬──────┘
      │                                    │
      │                                    ▼
      │                             ┌─────────────┐
      └──────────────────────────── │   Celery    │
           (reads status/report)    │   Worker    │
                                    └──────┬──────┘
                                           │ runs containers
                                           ▼
                                    ┌─────────────┐
                                    │   Docker    │
                                    └─────────────┘
```

## State Machine

Jobs follow a strict state transition lifecycle:

```
Queued → Provisioning → Provisioned → Attacking → Normalizing → Generating_Report → Completed
   ↓           ↓              ↓           ↓            ↓                ↓
   └───────────┴──────────────┴───────────┴────────────┴────────────────┴────────→ Failed
```

| State | Description |
|-------|-------------|
| `Queued` | Job created, waiting for worker pickup |
| `Provisioning` | Starting target container, creating network |
| `Provisioned` | Container ready, endpoint reachable |
| `Attacking` | Executing scan tools (nmap, nuclei, etc.) |
| `Normalizing` | Parsing raw outputs, mapping to schema |
| `Generating_Report` | Creating final report |
| `Completed` | Scan finished successfully |
| `Failed` | Error occurred (reachable from any state) |

## API Endpoints

### `POST /scan`
Start a new scan job.

**Request:**
```json
{ "target_url": "http://example.com" }
```

**Response:**
```json
{ "engagement_id": "uuid", "status": "Queued" }
```

### `GET /status/{engagement_id}`
Get current job status.

**Query Params:** `?include_history=true` (optional)

**Response:**
```json
{
  "engagement_id": "uuid",
  "status": "Completed",
  "history": [
    { "state": "Queued", "timestamp": "2026-02-27T16:49:08Z" },
    { "state": "Provisioning", "timestamp": "2026-02-27T16:49:08Z" },
    ...
  ]
}
```

### `GET /status/{engagement_id}/history`
Get full state transition history with timestamps.

### `GET /report/{engagement_id}`
Get scan report (only available when status is `Completed`).

## Redis Key Schema

| Key | Type | Description |
|-----|------|-------------|
| `job:{id}:status` | STRING | Current state value |
| `job:{id}:history` | LIST | State transition history (`STATE:TIMESTAMP`) |
| `job:{id}:report` | STRING | Final report JSON |
| `job:{id}:error` | STRING | Error message (on failure) |

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Redis
```bash
docker-compose up -d redis
```

### 3. Start Celery worker
```bash
python -m celery -A app.worker.celery_app worker --loglevel=info --pool=solo
```

### 4. Start FastAPI server
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## File Structure

```
app/
├── main.py              # FastAPI entry point
├── schemas.py           # Pydantic models + JobState enum
├── api/
│   └── routes.py        # HTTP endpoints
├── core/
│   ├── redis.py         # Redis client
│   └── state_manager.py # State machine logic
└── worker/
    ├── celery_app.py    # Celery configuration
    └── tasks.py         # Scan task implementation
```

## State Manager API

```python
from app.core.state_manager import transition_state, force_fail, get_state, get_state_history
from app.schemas import JobState

# Transition to next state (validates transition rules)
transition_state(engagement_id, JobState.PROVISIONING)

# Force fail from any state
force_fail(engagement_id, "Container startup failed")

# Get current state
state = get_state(engagement_id)

# Get full history
history = get_state_history(engagement_id)
```
