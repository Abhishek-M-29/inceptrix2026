"""
State Manager Module

Handles job state transitions with strict validation and history tracking.
All state changes must go through this module to ensure consistency.
"""

from datetime import datetime, timezone
from typing import Optional, List
from app.core.redis import redis_client
from app.schemas import (
    JobState,
    VALID_TRANSITIONS,
    InvalidStateTransitionError,
    StateHistoryEntry,
)


def _status_key(engagement_id: str) -> str:
    """Generate Redis key for job status."""
    return f"job:{engagement_id}:status"


def _history_key(engagement_id: str) -> str:
    """Generate Redis key for job state history."""
    return f"job:{engagement_id}:history"


def get_state(engagement_id: str) -> Optional[JobState]:
    """
    Get the current state of a job.
    
    Args:
        engagement_id: The job identifier
        
    Returns:
        Current JobState or None if job doesn't exist
    """
    status = redis_client.get(_status_key(engagement_id))
    if status is None:
        return None
    return JobState(status)


def get_state_history(engagement_id: str) -> List[StateHistoryEntry]:
    """
    Get the full state transition history for a job.
    
    Args:
        engagement_id: The job identifier
        
    Returns:
        List of StateHistoryEntry objects in chronological order
    """
    history_data = redis_client.lrange(_history_key(engagement_id), 0, -1)
    history = []
    
    for entry in history_data:
        # Format: "STATE:ISO_TIMESTAMP" - split at first colon since state names don't have colons
        state_str, timestamp_str = entry.split(":", 1)
        history.append(StateHistoryEntry(
            state=JobState(state_str),
            timestamp=datetime.fromisoformat(timestamp_str)
        ))
    
    return history


def transition_state(
    engagement_id: str,
    new_state: JobState,
    *,
    validate: bool = True
) -> JobState:
    """
    Transition a job to a new state with validation.
    
    Args:
        engagement_id: The job identifier
        new_state: The target state to transition to
        validate: If True, enforce transition rules (default True)
        
    Returns:
        The new JobState after transition
        
    Raises:
        InvalidStateTransitionError: If the transition is not allowed
    """
    current_state = get_state(engagement_id)
    
    if validate:
        allowed_transitions = VALID_TRANSITIONS.get(current_state, set())
        if new_state not in allowed_transitions:
            raise InvalidStateTransitionError(current_state, new_state, engagement_id)
    
    # Get current timestamp in UTC
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Use Redis pipeline for atomic update
    pipe = redis_client.pipeline()
    pipe.set(_status_key(engagement_id), new_state.value)
    pipe.rpush(_history_key(engagement_id), f"{new_state.value}:{timestamp}")
    pipe.execute()
    
    print(f"[{engagement_id}] State: {current_state.value if current_state else 'None'} → {new_state.value}")
    
    return new_state


def force_fail(engagement_id: str, error_message: str) -> JobState:
    """
    Force a job into Failed state from any state.
    
    This bypasses normal transition validation and should be used
    for error handling scenarios.
    
    Args:
        engagement_id: The job identifier
        error_message: Description of why the job failed
        
    Returns:
        JobState.FAILED
    """
    current_state = get_state(engagement_id)
    
    # Skip if already in terminal state
    if current_state in (JobState.COMPLETED, JobState.FAILED):
        print(f"[{engagement_id}] Already in terminal state {current_state.value}, skipping force_fail")
        return current_state
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Use Redis pipeline for atomic update
    pipe = redis_client.pipeline()
    pipe.set(_status_key(engagement_id), JobState.FAILED.value)
    pipe.rpush(_history_key(engagement_id), f"{JobState.FAILED.value}:{timestamp}")
    pipe.set(f"job:{engagement_id}:error", error_message)
    pipe.execute()
    
    print(f"[{engagement_id}] State: {current_state.value if current_state else 'None'} → Failed (forced)")
    print(f"[{engagement_id}] Error: {error_message}")
    
    return JobState.FAILED


def initialize_job(engagement_id: str) -> JobState:
    """
    Initialize a new job with Provisioning state.
    
    This is a convenience method for creating new jobs.
    
    Args:
        engagement_id: The job identifier
        
    Returns:
        JobState.PROVISIONING
    """
    return transition_state(engagement_id, JobState.PROVISIONING, validate=True)


def is_terminal_state(state: Optional[JobState]) -> bool:
    """
    Check if a state is terminal (no further transitions allowed).
    
    Args:
        state: The state to check
        
    Returns:
        True if state is Completed or Failed
    """
    return state in (JobState.COMPLETED, JobState.FAILED)
