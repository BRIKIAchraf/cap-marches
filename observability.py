"""Journalisation structurée sans clé ni contenu sensible."""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Iterator


logger = logging.getLogger("cap_marches")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def event(name: str, **fields: object) -> None:
    payload = {"event": name, "timestamp": time.time(), **fields}
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))


@contextmanager
def traced(operation: str) -> Iterator[str]:
    trace_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    event("operation_started", trace_id=trace_id, operation=operation)
    try:
        yield trace_id
    except Exception as exc:
        event(
            "operation_failed",
            trace_id=trace_id,
            operation=operation,
            error_type=type(exc).__name__,
        )
        raise
    else:
        event(
            "operation_completed",
            trace_id=trace_id,
            operation=operation,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
