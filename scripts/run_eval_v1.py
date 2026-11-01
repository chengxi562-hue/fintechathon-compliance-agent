"""eval_v1 minimal runner.

Reads data/evals/eval_v1.csv, runs run_agent() per row, compares
expected_decision vs actual decision (skip when expected is empty).
`clarify` is scored: pass only when the agent blocks with CLARIFY_REQUIRED.
The CSV has no prior turn, so that is the check those rows can make.
Writes data/evals/eval_v1_results.json, artifacts/eval_v1_per_row.log,
and prints P/F counts.

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
LOG_PATH = ROOT / "artifacts" / "eval_v1_per_row.log"


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
        reasons = list(state.verdict.reason_codes)
        if exp in ("allow", "block"):
            status = "P" if actual == exp else "F"
        elif exp == "clarify":
            # The row's utterance is the whole case: refuse to execute, and say so.
            status = "P" if actual == "block" and "CLARIFY_REQUIRED" in reasons else "F"
        else:
            status = "SKIP"
        n_pass += status == "P"
        n_fail += status == "F"
        n_skip += status == "SKIP"
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
                "actual_reasons": reasons,
                "status": status,
            }
        )

    OUT_PATH.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = len(results)
    print(f"P {n_pass} / F {n_fail} / SKIP {n_skip}  (total {total})")
    print(f"results -> {OUT_PATH}")
    _write_per_row_log(results, n_pass, n_fail, n_skip, total)
    print(f"per-row log -> {LOG_PATH}")
    return 0


def _write_per_row_log(
    results: list[dict], n_pass: int, n_fail: int, n_skip: int, total: int,
) -> None:
    fails = [r["id"] for r in results if r["status"] == "F"]
    skips = [r["id"] for r in results if r["status"] == "SKIP"]
    lines = [
        f"P {n_pass} / F {n_fail} / SKIP {n_skip}  (total {total})",
        f"results -> {OUT_PATH}",
        "EVAL_EXIT=0",
        "",
        "# per-row recount from data/evals/eval_v1_results.json written by this run",
        f"# rows={total} P={n_pass} F={n_fail} SKIP={n_skip}",
        "# fail_ids=" + ",".join(fails),
        "# skip_ids=" + ",".join(skips),
        "id\tstatus\texpected_decision\tactual_decision\tactual_intent\tactual_reasons",
    ]
    for r in results:
        reasons = ",".join(r["actual_reasons"])
        lines.append(
            "\t".join(
                [
                    r["id"],
                    r["status"],
                    r["expected_decision"],
                    r["actual_decision"],
                    r["actual_intent"] or "",
                    reasons,
                ]
            )
        )
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
