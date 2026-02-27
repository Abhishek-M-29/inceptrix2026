from pydantic import BaseModel, HttpUrl
from uuid import UUID
from enum import Enum
from typing import Optional, List
from datetime import datetime


class JobState(str, Enum):
    """
    Job lifecycle states following strict state machine transitions.
    
    Flow: Queued → Provisioning → Provisioned → Attacking → Normalizing → Generating_Report → Completed
    Any state can transition to Failed.
    """
    QUEUED = "Queued"
    PROVISIONING = "Provisioning"
    PROVISIONED = "Provisioned"
    ATTACKING = "Attacking"
    NORMALIZING = "Normalizing"
    GENERATING_REPORT = "Generating_Report"
    COMPLETED = "Completed"
    FAILED = "Failed"


# Valid state transitions - each state maps to its allowed next states
VALID_TRANSITIONS: dict[Optional[JobState], set[JobState]] = {
    None: {JobState.QUEUED},  # Initial state (no previous state)
    JobState.QUEUED: {JobState.PROVISIONING, JobState.FAILED},
    JobState.PROVISIONING: {JobState.PROVISIONED, JobState.FAILED},
    JobState.PROVISIONED: {JobState.ATTACKING, JobState.FAILED},
    JobState.ATTACKING: {JobState.NORMALIZING, JobState.FAILED},
    JobState.NORMALIZING: {JobState.GENERATING_REPORT, JobState.FAILED},
    JobState.GENERATING_REPORT: {JobState.COMPLETED, JobState.FAILED},
    JobState.COMPLETED: set(),  # Terminal state - no transitions allowed
    JobState.FAILED: set(),  # Terminal state - no transitions allowed
}


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, current_state: Optional[JobState], new_state: JobState, engagement_id: str):
        self.current_state = current_state
        self.new_state = new_state
        self.engagement_id = engagement_id
        current = current_state.value if current_state else "None"
        super().__init__(
            f"Invalid state transition for job {engagement_id}: "
            f"{current} → {new_state.value}"
        )


class StateHistoryEntry(BaseModel):
    """Single entry in state transition history."""
    state: JobState
    timestamp: datetime


class ScanRequest(BaseModel):
    target_url: HttpUrl


class ScanResponse(BaseModel):
    engagement_id: UUID
    status: JobState


class StatusResponse(BaseModel):
    engagement_id: str
    status: JobState
    history: Optional[List[StateHistoryEntry]] = None
