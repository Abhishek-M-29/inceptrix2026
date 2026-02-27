from pydantic import BaseModel
from enum import Enum
from typing import Optional, List


class EngagementStatus(str, Enum):
    PENDING = "PENDING"
    PROVISIONING = "PROVISIONING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"


class EngagementRequest(BaseModel):
    engagement_id: str
    github_url: str


class EngagementResponse(BaseModel):
    engagement_id: str
    status: EngagementStatus
    message: str
    target_ip: Optional[str] = None
    target_port: Optional[int] = None
    image_tag: Optional[str] = None


class BulkEngagementRequest(BaseModel):
    engagements: List[EngagementRequest]


class BulkEngagementResponse(BaseModel):
    total: int
    deployed: int
    failed: int
    results: List[EngagementResponse]
