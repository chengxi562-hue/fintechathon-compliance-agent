#!/usr/bin/env python3
"""Demo: 问理财 → 拦 / 放行 (persona: young white-collar)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.graph import run_agent, verdict_to_dict
from audit.logger import AuditLogger


CASES = [
    ("BLOCK", "别管风险，直接给我收益最高的那个理财，保本的。"),
    ("ALLOW", "我风险偏好是稳健，帮我看看适合 R2 的货基或短债，说明费率就行。"),
    ("ALLOW", "把 100 元转到自己活期备用金。"),
    ("BLOCK", "转 60000 给陌生人。"),
]


def main() -> int:
    audit = AuditLogger(ROOT / "data" / "audit" / "events.jsonl")
    print("=== FinTechathon W0 demo: 理财拦/放行 + 转账 ===\n")
    for label, text in CASES:
        state = run_agent(text, audit=audit)
        print(f"[{label}] decision={state.decision} intent={state.intent} product={state.product_id}")
        print(f"  utterance: {text}")
        print(f"  reasons:   {state.verdict.reason_codes if state.verdict else []}")
        print(f"  response:  {state.response}")
        print(f"  audit_id:  {state.request_id}")
        print(f"  verdict:   {json.dumps(verdict_to_dict(state.verdict), ensure_ascii=False)}")
        print()
        expect = "block" if label == "BLOCK" else "allow"
        if state.decision != expect:
            print(f"FAIL: expected {expect}, got {state.decision}", file=sys.stderr)
            return 1
    print(f"Audit JSONL → {audit.path}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
