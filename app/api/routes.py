from fastapi import APIRouter, HTTPException
from app.schemas import ScanRequest, ScanResponse
from app.core.redis import redis_client
from app.worker.tasks import run_scan_task
import uuid
import json

router = APIRouter()

@router.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest):
    engagement_id = str(uuid.uuid4())
    
    # Update Redis status
    redis_client.set(f"job:{engagement_id}:status", "Queued")
    
    # Trigger Celery task
    run_scan_task.delay(engagement_id, str(request.target_url))
    
    return ScanResponse(engagement_id=engagement_id, status="Queued")

@router.get("/status/{engagement_id}")
async def get_status(engagement_id: str):
    status = redis_client.get(f"job:{engagement_id}:status")
    
    if not status:
        raise HTTPException(status_code=404, detail="Engagement ID not found")
        
    return {"engagement_id": engagement_id, "status": status}

@router.get("/report/{engagement_id}")
async def get_report(engagement_id: str):
    status = redis_client.get(f"job:{engagement_id}:status")
    
    if not status:
        raise HTTPException(status_code=404, detail="Engagement ID not found")
        
    if status != "Completed":
        raise HTTPException(status_code=400, detail="Report not ready")
        
    report = redis_client.get(f"job:{engagement_id}:report")
    if not report:
         raise HTTPException(status_code=404, detail="Report data missing")
         
    return json.loads(report)
