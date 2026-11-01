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


def test_phone_and_account_numbers_are_not_amounts():
    """号码片段不得并进金额。多种混排，货币单位和千分位仍是金额。"""
    mixed = (
        ("把收款人改成 6222 7777 再转 50000。", 50000.0),
        ("把\u202e收款人改成\u202d 6222 7777 再转 50000。", 50000.0),
        ("直接转 30000 到 6222。", 30000.0),
        ("马上转 8 万到 6222 8888。", 80000.0),
        ("帮我转账 8000 到卡号 6222。", 8000.0),
        ("转 5,000 到 6222。", 5000.0),
        ("给手机号 13800138000 转 200 元。", 200.0),
        ("转 1500 到 138 0013 8000。", 1500.0),
        ("转 1500 到 +86 138-0013-8000。", 1500.0),
        ("向尾号 5678 转 900 元。", 900.0),
        ("转 2500 给 15912345678。", 2500.0),
        ("请把 600 元打到账号 6222-7777-8888-9999。", 600.0),
        ("转 400 到 010-12345678。", 400.0),
        ("转 80 到 400-800-1234。", 80.0),
        ("转 700 到 6225888812345678。", 700.0),
        ("账号换成 62228888 再转 350 元。", 350.0),
        ("转 6222 元到活期备用金。", 6222.0),
        ("转 -100 元到卡号 6222。", -100.0),
    )
    for utterance, expected in mixed:
        assert _parse_transfer_amount(utterance) == expected, utterance

    # 代扣改额两侧都是金额，不能被号码规则吃掉
    assert _parse_amounts("把代扣金额从 200 改成 2000。") == [200.0, 2000.0]
    assert _parse_transfer_amount("先转 4900，再转 4900，凑够 9800。") == 19600.0
    assert _parse_transfer_amount("转 25,000 到活期备用金。") == 25000.0
