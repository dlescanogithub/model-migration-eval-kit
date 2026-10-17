"""Structured JSON logs. One object per line. Secrets are not added here."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import TextIO


class JsonFormatter(logging.Formatter):
    """Format a log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            for key, value in extra.items():
                if key in {"api_key", "authorization", "token", "llm_api_key"}:
                    continue
                payload[str(key)] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> logging.Logger:
    """Attach a JSON handler to the migration_eval logger and return it."""
    logger = logging.getLogger("migration_eval")
    logger.handlers.clear()
    logger.setLevel(level.upper())
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(event: str, **fields: object) -> None:
    """Emit one JSON log line with an event name and extra fields."""
    logging.getLogger("migration_eval").info(
        event,
        extra={"extra_fields": {"event": event, **fields}},
    )
