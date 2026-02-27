"""
Centralised logging configuration for the Inceptrix MCP server.

Features
--------
* TRACE level (5) – finer than DEBUG – for raw command I/O.
* JSON lines emitted to stdout (Docker-friendly).
* Per-request correlation IDs via contextvars.
* Colour-coded human-readable formatter when LOG_FORMAT=pretty.
* Automatic log-level control via LOG_LEVEL env-var (default INFO).
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Custom TRACE level
# ---------------------------------------------------------------------------
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def _trace(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)  # type: ignore[attr-defined]


logging.Logger.trace = _trace  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Correlation-ID context var
# ---------------------------------------------------------------------------
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    """Emit one JSON object per log record — machine-parseable."""

    def format(self, record: logging.LogRecord) -> str:
        exc_text = None
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)

        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "cid": correlation_id.get("-"),
            "msg": record.getMessage(),
        }
        if exc_text:
            payload["exc"] = exc_text
        extra_keys = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord.__dict__
            and k
            not in {
                "args", "msg", "levelname", "levelno", "name",
                "pathname", "filename", "module", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "exc_info", "exc_text",
                "stack_info", "taskName",
            }
        }
        if extra_keys:
            payload.update(extra_keys)
        return json.dumps(payload, default=str)


_LEVEL_COLOURS = {
    "TRACE":    "\033[90m",   # dark grey
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_RESET = "\033[0m"


class _PrettyFormatter(logging.Formatter):
    """Human-readable coloured formatter for local development."""

    FMT = "{colour}{level:<8}{reset} {ts} [{cid}] {name} — {msg}"

    def format(self, record: logging.LogRecord) -> str:
        colour = _LEVEL_COLOURS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%H:%M:%S.%f"
        )[:-3]
        line = self.FMT.format(
            colour=colour,
            reset=_RESET,
            level=record.levelname,
            ts=ts,
            cid=correlation_id.get("-"),
            name=record.name,
            msg=record.getMessage(),
        )
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


# ---------------------------------------------------------------------------
# Public initialiser
# ---------------------------------------------------------------------------

def setup_logging() -> None:
    """Call once at startup to configure the root logger."""
    raw_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = TRACE if raw_level == "TRACE" else getattr(logging, raw_level, logging.INFO)

    fmt = os.environ.get("LOG_FORMAT", "json").lower()
    formatter = _PrettyFormatter() if fmt == "pretty" else _JSONFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    # Remove any handlers added by libraries before we configure
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party / internal loggers
    if level > logging.DEBUG:
        for noisy in (
            "uvicorn.access",
            "uvicorn.error",
            "uvicorn",
            "httpx",
            "httpcore",
            "mcp.server.streamable_http_manager",
            "mcp.server",
            "fastmcp",
            "websockets",
            "asyncio",
        ):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    # Suppress Python deprecation warnings from libraries
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
