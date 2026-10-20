"""「无合规门」基线对照：同样 173 条评测集，如果只用银行侧兜底会怎样。

目的：回答评委最常问的一句——「你加这些门，到底比不加好多少？」

两组：
  A. 有门（现状）：run_agent() 走四道门 + 澄清门
  B. 无门（基线）：跳过 Agent 的四道门，直接按意图调工具层，只靠 Mock Bank 第二道闸

注意：B 组不是「把门关掉再跑 run_agent」——那没有意义（门被调用就会拦）。
B 组模拟的是「团队没做合规门，只写了个能调工具的朴素 bot」这种真实竞品形态。

用法：PYTHONPATH=. .venv/bin/python scripts/baseline_no_gates.py
输出：data/evals/_baseline_no_gates.json + 控制台对比表
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from agent.gates import classify_intent, parse_explicit_product, load_rules  # noqa: E402
from agent.graph import run_agent  # noqa: E402
from mock_bank.app import app  # noqa: E402

CSV_PATH = ROOT / "data" / "evals" / "eval_v1.csv"
OUT = ROOT / "data" / "evals" / "_baseline_no_gates.json"

client = TestClient(app)
RULES = load_rules()
CUSTOMER = "cust_yw_001"


def naive_agent(utterance: str) -> str:
    """朴素 bot：只做意图分类 + 调工具，不做任何合规判断。

    返回 "block" / "allow" 以便与评测集口径对齐——
    这里 "block" 指「最终被拦下」（可能被银行侧兜底拦，也可能工具直接报错）。
    """
    intent = classify_intent(utterance)

    if intent in {"wealth_purchase", "wealth_inquire"}:
        pid, _unknown = parse_explicit_product(utterance, RULES)
        if intent == "wealth_purchase":
            if pid is None:
                # 朴素 bot 不会拦未知产品，它会「猜一个」卖给用户——这里按最坏情况记 allow
                return "allow"
            r = client.post(
                "/v1/wealth/purchase",
                json={"customer_id": CUSTOMER, "product_id": pid, "amount_cny": 1000.0},
            )
            # 银行侧只兜住「适当性」这一类；未知产品朴素 bot 已经放过去了
            return "block" if r.status_code >= 400 else "allow"
        return "allow"

    if intent == "transfer":
        import re

        m = re.search(r"(\d[\d,]*(?:\.\d+)?)", utterance)
        amount = float(m.group(1).replace(",", "")) if m else 0.0
        r = client.post(
            "/v1/transfers",
            json={
                "customer_id": CUSTOMER,
                "from_account_id": "acc_yw_001",
                "to_account_id": "acc_yw_backup",
                "amount_cny": amount,
                "confirmed": True,
            },
        )
        return "block" if r.status_code >= 400 else "allow"

    # 其余意图（account_balance / subscription / bill / chitchat）朴素 bot 一律照做
    return "allow"


def main() -> int:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    results = []
    n_pass_gated = n_pass_naive = n_scored = 0

    for row in rows:
        expected = (row.get("expected_decision") or "").strip()
        if expected not in ("allow", "block"):
            continue
        n_scored += 1
        utterance = row["utterance"]

        gated = run_agent(utterance).decision
        naive = naive_agent(utterance)

        ok_gated = gated == expected
        ok_naive = naive == expected
        n_pass_gated += ok_gated
        n_pass_naive += ok_naive

        results.append(
            {
                "id": row["id"],
                "attack_type": row["attack_type"],
                "expected": expected,
                "gated": gated,
                "naive": naive,
                "gated_ok": ok_gated,
                "naive_ok": ok_naive,
            }
        )

    summary = {
        "scored": n_scored,
        "gated_pass": n_pass_gated,
        "gated_rate": round(n_pass_gated / n_scored * 100, 1),
        "naive_pass": n_pass_naive,
        "naive_rate": round(n_pass_naive / n_scored * 100, 1),
    }
    OUT.write_text(
        json.dumps({"summary": summary, "rows": results}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    print(f"评测集（有明确期望的 {n_scored} 条）")
    print(f"  A 有门  ：{n_pass_gated}/{n_scored} = {summary['gated_rate']}%")
    print(f"  B 无门  ：{n_pass_naive}/{n_scored} = {summary['naive_rate']}%")
    print(f"  差      ：+{n_pass_gated - n_pass_naive} 条")

    # 按攻击类型看差距
    print("\n按类别看差距（只列有差异或全错的类别）")
    by_type: dict[str, list[dict]] = {}
    for r in results:
        by_type.setdefault(r["attack_type"], []).append(r)
    for atype, rs in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        g = sum(x["gated_ok"] for x in rs)
        n = sum(x["naive_ok"] for x in rs)
        if g != n or g != len(rs):
            print(f"  {atype[:24]:26} 有门 {g}/{len(rs)}   无门 {n}/{len(rs)}")

    print(f"\n明细 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
