"""
State Manager Module

Handles job state transitions with strict validation and history tracking.
All state changes must go through this module to ensure consistency.

Rules:
- No skipping states
- No backward transitions
- Only the orchestrator (Celery task) may modify state
- Every state change updates Redis atomically and logs the transition
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from app.core.redis import redis_client
from app.schemas import (
    JobState,
    VALID_TRANSITIONS,
    InvalidStateTransitionError,
    StateHistoryEntry,
)

logger = logging.getLogger("redshell.state")


# ─── Redis Key Helpers ────────────────────────────────────────────────────────

def _status_key(engagement_id: str) -> str:
    return f"job:{engagement_id}:status"


def _history_key(engagement_id: str) -> str:
    return f"job:{engagement_id}:history"


def _error_key(engagement_id: str) -> str:
    return f"job:{engagement_id}:error"


# ─── Read Helpers ─────────────────────────────────────────────────────────────

def get_state(engagement_id: str) -> Optional[JobState]:
    """Get the current state of a job (or None if it doesn't exist)."""
    status = redis_client.get(_status_key(engagement_id))
    if status is None:
        return None
    return JobState(status)


def get_state_history(engagement_id: str) -> List[StateHistoryEntry]:
    """Return the full state transition history in chronological order."""
    history_data = redis_client.lrange(_history_key(engagement_id), 0, -1)
    history = []

    for entry in history_data:
        # Format: "STATE:ISO_TIMESTAMP" — split at first colon
        state_str, timestamp_str = entry.split(":", 1)
        history.append(StateHistoryEntry(
            state=JobState(state_str),
            timestamp=datetime.fromisoformat(timestamp_str),
        ))

    return history


def get_failure_info(engagement_id: str) -> Optional[dict]:
    """Return structured failure metadata dict, or None if not failed."""
    raw = redis_client.get(_error_key(engagement_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # Legacy plain-string error — wrap it for backwards compat
        return {
            "failed_stage": "Unknown",
            "error": str(raw),
            "traceback": None,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }


# ─── State Transitions ───────────────────────────────────────────────────────

def transition_state(
    engagement_id: str,
    new_state: JobState,
    *,
    validate: bool = True,
) -> JobState:
    """
    Transition a job to *new_state* with strict validation.

    Raises InvalidStateTransitionError when the move is illegal.
    """
    current_state = get_state(engagement_id)

    if validate:
        allowed = VALID_TRANSITIONS.get(current_state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(current_state, new_state, engagement_id)

    timestamp = datetime.now(timezone.utc).isoformat()

    # Atomic Redis update: status + history append
    pipe = redis_client.pipeline()
    pipe.set(_status_key(engagement_id), new_state.value)
    pipe.rpush(_history_key(engagement_id), f"{new_state.value}:{timestamp}")
    pipe.execute()

    prev = current_state.value if current_state else "None"
    logger.info("[%s] State: %s → %s", engagement_id, prev, new_state.value)

    return new_state


def force_fail(
    engagement_id: str,
    error_message: str,
    *,
    failed_stage: str = "Unknown",
    traceback_str: Optional[str] = None,
) -> JobState:
    """
    Force a job into the Failed terminal state from any non-terminal state.

    Stores structured failure metadata as JSON at ``job:{id}:error`` so the
    frontend can display *what* failed, *where*, and *why*.
    """
    current_state = get_state(engagement_id)

    # Guard: never overwrite a terminal state
    if current_state in (JobState.COMPLETED, JobState.FAILED):
        logger.warning(
            "[%s] Already in terminal state %s — skipping force_fail",
            engagement_id,
            current_state.value,
        )
        return current_state

    timestamp = datetime.now(timezone.utc).isoformat()

    failure_payload = json.dumps({
        "failed_stage": failed_stage,
        "error": error_message,
        "traceback": traceback_str,
        "failed_at": timestamp,
    })

    pipe = redis_client.pipeline()
    pipe.set(_status_key(engagement_id), JobState.FAILED.value)
    pipe.rpush(_history_key(engagement_id), f"{JobState.FAILED.value}:{timestamp}")
    pipe.set(_error_key(engagement_id), failure_payload)
    pipe.execute()

    prev = current_state.value if current_state else "None"
    logger.error(
        "[%s] State: %s → Failed (forced) | stage=%s | error=%s",
        engagement_id,
        prev,
        failed_stage,
        error_message,
    )

    return JobState.FAILED


# ─── Convenience ──────────────────────────────────────────────────────────────

def initialize_job(engagement_id: str) -> JobState:
    """Create a new job and set its initial state to Provisioning."""
    return transition_state(engagement_id, JobState.PROVISIONING, validate=True)


def is_terminal_state(state: Optional[JobState]) -> bool:
    """Return True when *state* is Completed or Failed."""
    return state in (JobState.COMPLETED, JobState.FAILED)
