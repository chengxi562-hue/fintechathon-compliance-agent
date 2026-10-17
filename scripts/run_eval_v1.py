"""eval_v1 minimal runner.

Reads data/evals/eval_v1.csv, runs run_agent() per row, compares
expected_decision vs actual decision (skip when expected is empty),
writes data/evals/eval_v1_results.json and prints P/F counts.

Usage:
    .venv/bin/python scripts/run_eval_v1.py [--limit N] [--smoke]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.graph import run_agent  # noqa: E402

CSV_PATH = ROOT / "data" / "evals" / "eval_v1.csv"
OUT_PATH = ROOT / "data" / "evals" / "eval_v1_results.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全量）")
    ap.add_argument("--smoke", action="store_true", help="等价于 --limit 15")
    args = ap.parse_args()
    limit = 15 if args.smoke else args.limit

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    if limit:
        rows = rows[:limit]

    results = []
    n_pass = n_fail = n_skip = 0
    for r in rows:
        state = run_agent(r["utterance"])
        actual = state.decision
        exp = (r.get("expected_decision") or "").strip()
        if exp in ("allow", "block"):
            status = "P" if actual == exp else "F"
            n_pass += status == "P"
            n_fail += status == "F"
        else:
            status = "SKIP"
            n_skip += 1
        results.append(
            {
                "id": r["id"],
                "source": r["source"],
                "attack_type": r["attack_type"],
                "utterance": r["utterance"],
                "expected_decision": exp,
                "expected_reason": r.get("expected_reason", ""),
                "actual_decision": actual,
                "actual_intent": state.intent,
                "actual_product": state.product_id,
                "actual_reasons": list(state.verdict.reason_codes),
                "status": status,
            }
        )

    OUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = len(results)
    print(f"P {n_pass} / F {n_fail} / SKIP {n_skip}  (total {total})")
    print(f"results -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
