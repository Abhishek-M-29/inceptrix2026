from pydantic import BaseModel, HttpUrl
from uuid import UUID

class ScanRequest(BaseModel):
    target_url: HttpUrl

class ScanResponse(BaseModel):
    engagement_id: UUID
    status: str
