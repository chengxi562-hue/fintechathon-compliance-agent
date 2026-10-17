"""P0-1: 金额归一（万/万元/亿/中文数字/千分位/负数/多笔）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.graph import _parse_amounts, _parse_transfer_amount, run_agent


def test_t21_yi():
    assert _parse_transfer_amount("转 1 亿到我的活期账户。") == 1e8
    s = run_agent("转 1 亿到我的活期账户。")
    assert s.decision == "block"
    assert "TRANSFER_WHITELIST_REQUIRED" in s.verdict.reason_codes


def test_t22_wanyuan():
    s = run_agent("给我妈转3万元。")
    assert s.decision == "block"
    assert _parse_transfer_amount("给我妈转3万元。") == 30000.0


def test_t23_chinese_numeral():
    assert _parse_transfer_amount("转五千给房东。") == 5000.0
    assert _parse_amounts("转三万五千")[0] == 35000.0


def test_t24_thousands_sep():
    assert _parse_transfer_amount("转 25,000 到活期备用金。") == 25000.0
    s = run_agent("转 25,000 到活期备用金。")
    assert s.decision == "block"
    assert "TRANSFER_SOFT_LIMIT" in s.verdict.reason_codes


def test_t25_split_sum():
    # 拆分规避：两笔 4900 合计超限即拦，不得首笔盲放行；目标额 9800 提及也计入（宁多勿漏）
    s = run_agent("先转 4900，再转 4900，凑够 9800。")
    assert s.decision == "block"
    assert "TRANSFER_CONFIRM_REQUIRED" in s.verdict.reason_codes
    assert "19600" in s.response


def test_t30_negative_invalid():
    assert _parse_transfer_amount("转 -100 元到我账户。") == -100.0
    s = run_agent("转 -100 元到我账户。")
    assert s.decision == "block"
    assert "TRANSFER_AMOUNT_INVALID" in s.verdict.reason_codes


def test_wan_bare_unit():
    # 关键回归：「转 10 万」不得按 10 元放行
    s = run_agent("转 10 万到活期")
    assert s.decision == "block"
    # 10万=100000 超过白名单阈值 50000；关键是不得按 10 元放行
    assert "TRANSFER_WHITELIST_REQUIRED" in s.verdict.reason_codes
