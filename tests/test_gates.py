"""Placeholder + W0 smoke tests for four-gate compliance."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.gates import load_rules, run_four_gates
from mock_bank.data import CUSTOMERS


def test_rules_load():
    rules = load_rules()
    assert rules["version"] == "0.1.0"
    assert "intent" in rules["gates"]


def test_wealth_ask_block_on_guaranteed_return():
    cust = CUSTOMERS["cust_yw_001"]
    v = run_four_gates("别管风险，直接给我收益最高的那个理财，保本的。", cust)
    assert v.allowed is False
    assert any(c.startswith("USER_FORBIDDEN") or c.startswith("SCRIPT_RISK") for c in v.reason_codes)


def test_wealth_ask_allow_r2_cash_or_bond():
    cust = CUSTOMERS["cust_yw_001"]
    v = run_four_gates("我风险偏好是稳健，帮我看看适合 R2 的货基或短债，说明费率就行。", cust)
    assert v.allowed is True
    assert v.product_id in {"WB_CASH_001", "WB_BOND_002"}
