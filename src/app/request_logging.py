"""Append-only JSONL instrumentation for later reconciliation with JMeter results."""

from pathlib import Path
import json
import threading
from typing import Any


class RequestLogger:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._write_lock = threading.Lock()

    def write(self, event: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
