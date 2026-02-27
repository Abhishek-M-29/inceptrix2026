from fastapi import APIRouter, HTTPException, Query
from app.schemas import ScanRequest, ScanResponse, StatusResponse, JobState
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


# -------- Payload Schema --------
class ScanWebhook(BaseModel):
    tool: str
    target: str
    command_used: str
    status: str


# -------- Webhook Endpoint --------
@router.post("/webhook/scan")
async def receive_scan(data: ScanWebhook):
    print("Webhook received:")
    print(f"Tool: {data.tool}")
    print(f"Target: {data.target}")
    print(f"Command: {data.command_used}")
    print(f"Status: {data.status}")

    return {"message": "Webhook received successfully"}

@router.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest):
    engagement_id = str(uuid.uuid4())
    
    # Initialize job with Queued state (using state manager)
    state = initialize_job(engagement_id)
    
    # Trigger Celery task
    run_scan_task.delay(engagement_id, str(request.target_url))
    
    return ScanResponse(engagement_id=engagement_id, status=state)

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

@router.get("/report/{engagement_id}")
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
