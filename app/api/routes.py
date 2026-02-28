from fastapi import APIRouter, HTTPException, Query
from app.schemas import ScanRequest, ScanResponse, StatusResponse, JobState, ReportResponse
from app.core.redis import redis_client
from app.core.state_manager import (
    initialize_job,
    get_state,
    get_state_history,
)
from app.worker.tasks import run_scan_task
import uuid
import json



router = APIRouter()

from pydantic import BaseModel
from datetime import datetime, timezone

WEBHOOK_QUEUE_KEY = "webhook:queue"
PAGE_SIZE = 20


# -------- Payload Schema --------
class ScanWebhook(BaseModel):
    engagement_id: str
    status: str


# -------- Webhook Endpoint --------
@router.post("/webhook/scan")
async def receive_scan(data: ScanWebhook):
    entry = {
        "engagement_id": data.engagement_id,
        "status": data.status,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.rpush(WEBHOOK_QUEUE_KEY, json.dumps(entry))

    print(f"[webhook] queued → engagement_id={data.engagement_id} status={data.status}")
    return {"engagement_id": data.engagement_id, "status": data.status}


# -------- Queue Read Endpoint --------
@router.get("/queue")
async def get_queue(page: int = Query(1, ge=1), page_size: int = Query(PAGE_SIZE, ge=1, le=100)):
    total = redis_client.llen(WEBHOOK_QUEUE_KEY)
    start = (page - 1) * page_size
    end = start + page_size - 1

    raw_items = redis_client.lrange(WEBHOOK_QUEUE_KEY, start, end)
    items = [json.loads(item) for item in raw_items]

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": items,
    }

@router.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest):
    """Start a new scan job and enqueue it for processing.

    Wrapped in a try/except so that any setup errors are surfaced
    to the client instead of a generic 500.
    """
    try:
        engagement_id = str(uuid.uuid4())

        # Initialize job with Provisioning state (using state manager)
        state = initialize_job(engagement_id)

        # Trigger Celery task
        run_scan_task.delay(engagement_id, str(request.target_url))

        return ScanResponse(engagement_id=engagement_id, status=state)
    except Exception as e:
        # Log server-side for debugging and return a clear error detail
        print(f"[SCAN_ERROR] Failed to start scan: {e}")
        raise HTTPException(status_code=500, detail=f"scan_setup_error: {e}")

@router.get("/status/{engagement_id}", response_model=StatusResponse)
async def get_status(engagement_id: str, include_history: bool = Query(False)):
    state = get_state(engagement_id)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Engagement ID not found")
    
    response = StatusResponse(engagement_id=engagement_id, status=state)
    
    if include_history:
        response.history = get_state_history(engagement_id)
        
    return response

@router.get("/status/{engagement_id}/history")
async def get_status_history(engagement_id: str):
    state = get_state(engagement_id)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Engagement ID not found")
    
    history = get_state_history(engagement_id)
    return {
        "engagement_id": engagement_id,
        "current_state": state,
        "history": [{"state": h.state.value, "timestamp": h.timestamp.isoformat()} for h in history]
    }

@router.get("/report/{engagement_id}", response_model=ReportResponse)
async def get_report(engagement_id: str):
    state = get_state(engagement_id)
    
    if state is None:
        raise HTTPException(status_code=404, detail="Engagement ID not found")
        
    if state != JobState.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Report not ready. Current state: {state.value}")
        
    report = redis_client.get(f"job:{engagement_id}:report")
    if not report:
         raise HTTPException(status_code=404, detail="Report data missing")
         
    return json.loads(report)
