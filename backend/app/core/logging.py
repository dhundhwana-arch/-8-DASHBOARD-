"""Structured logging setup with correlation-ID propagation and secret redaction."""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from app.core.config import Settings
from app.core.redaction import RedactingLogFilter

_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    current = _correlation_id_var.get()
    if not current:
        current = str(uuid.uuid4())
        _correlation_id_var.set(current)
    return current


def set_correlation_id(correlation_id: str | None) -> str:
    cleaned = (correlation_id or "").strip()
    if not cleaned or len(cleaned) > 128:
        cleaned = str(uuid.uuid4())
    _correlation_id_var.set(cleaned)
    return cleaned


class CorrelationLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id_var.get() or "-"
        return True


def configure_logging(settings: Settings) -> logging.Logger:
    logger = logging.getLogger("module08_admin")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] [corr=%(correlation_id)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Replace filters idempotently so secret literals track current settings
    logger.filters.clear()
    logger.addFilter(CorrelationLogFilter())
    logger.addFilter(RedactingLogFilter(secret_provider=settings.known_secret_literals))
    logger.propagate = False
    return logger
