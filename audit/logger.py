"""Append-only JSONL audit trail for compliance decisions."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class AuditLogger:
    def __init__(self, path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        default = root / "data" / "audit" / "events.jsonl"
        self.path = Path(path or os.environ.get("AUDIT_DIR", default))
        if self.path.is_dir() or str(self.path).endswith("/"):
            self.path = Path(self.path) / "events.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = {"ts": _now_iso(), **event}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload
