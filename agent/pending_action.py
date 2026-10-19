"""PendingAction confirmation gate stub (W1 first item: subscription writes).

Hard rule: change_amount / pause_debit / resume_debit / cancel_sub MUST create a
PendingAction first. Mock Bank state must NOT mutate until status == confirmed.
This module is intentionally write-free against bank seed — no half-finished writes.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

ActionType = Literal["change_amount", "pause_debit", "resume_debit", "cancel_sub"]
PendingStatus = Literal["pending", "confirmed", "cancelled", "expired"]

DEFAULT_TTL_SEC = 600  # 10 minutes


@dataclass
class PendingAction:
    pending_id: str
    session_id: str
    customer_id: str
    action: ActionType
    target_id: str  # subscription_id
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    expires_at: float = 0.0
    status: PendingStatus = "pending"
    before: Optional[dict[str, Any]] = None
    after: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# In-memory store (process-local; demo only)
_PENDING: dict[str, PendingAction] = {}


def create_pending(
    *,
    session_id: str,
    customer_id: str,
    action: ActionType,
    target_id: str,
    payload: Optional[dict[str, Any]] = None,
    before: Optional[dict[str, Any]] = None,
    ttl_sec: int = DEFAULT_TTL_SEC,
) -> PendingAction:
    """Create a pending write. Does NOT mutate Mock Bank subscriptions."""
    now = time.time()
    pa = PendingAction(
        pending_id=f"pend_{uuid.uuid4().hex[:12]}",
        session_id=session_id,
        customer_id=customer_id,
        action=action,
        target_id=target_id,
        payload=dict(payload or {}),
        created_at=now,
        expires_at=now + ttl_sec,
        status="pending",
        before=before,
    )
    _PENDING[pa.pending_id] = pa
    return pa


def get_pending(pending_id: str) -> Optional[PendingAction]:
    pa = _PENDING.get(pending_id)
    if pa is None:
        return None
    if pa.status == "pending" and time.time() > pa.expires_at:
        pa.status = "expired"
    return pa


def confirm_pending(pending_id: str, *, session_id: str) -> tuple[str, Optional[PendingAction]]:
    """Mark confirmed only. Caller must apply bank write AFTER this returns ok.

    Returns (reason_code, pending_or_none).
    Never writes to Mock Bank itself.
    """
    pa = get_pending(pending_id)
    if pa is None:
        return "PENDING_NOT_FOUND", None
    if pa.session_id != session_id:
        return "PENDING_SESSION_MISMATCH", pa
    if pa.status == "expired" or (pa.status == "pending" and time.time() > pa.expires_at):
        pa.status = "expired"
        return "PENDING_EXPIRED", pa
    if pa.status != "pending":
        return f"PENDING_NOT_PENDING:{pa.status}", pa
    pa.status = "confirmed"
    return "PENDING_CONFIRMED", pa


def cancel_pending(pending_id: str, *, session_id: str) -> tuple[str, Optional[PendingAction]]:
    pa = get_pending(pending_id)
    if pa is None:
        return "PENDING_NOT_FOUND", None
    if pa.session_id != session_id:
        return "PENDING_SESSION_MISMATCH", pa
    if pa.status != "pending":
        return f"PENDING_NOT_PENDING:{pa.status}", pa
    pa.status = "cancelled"
    return "PENDING_CANCELLED", pa


def clear_store() -> None:
    """Test helper."""
    _PENDING.clear()
