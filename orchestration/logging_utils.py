from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class FormatterJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trace_id"):
            payload["trace_id"] = getattr(record, "trace_id")
        if hasattr(record, "extra_payload"):
            payload["extra_payload"] = getattr(record, "extra_payload")
        return json.dumps(payload, ensure_ascii=True)


def konfigurasikan_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatterJson())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def logger_dengan_trace(nama: str, trace_id: str) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logging.getLogger(nama), {"trace_id": trace_id})
