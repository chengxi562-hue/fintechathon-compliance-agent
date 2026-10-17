"""R4 意图修复：实体优先（目录中文品名/WB_*）+ 英文 buy + 否定式转账。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.gates import classify_intent
from agent.graph import run_agent


# --- classify_intent 单元断言 ---


@pytest.mark.parametrize(
    "utterance,expected",
    [
        ("我自测是激进型 R5，帮我买进取混合FOF。", "wealth_purchase"),   # R01
        ("我全部 18 万都买进取混合FOF。", "wealth_purchase"),           # R03
        ("buy WB_EQ_MIX_003 for me, risk 4 is fine.", "wealth_purchase"),  # R04
        ("帮我买 10000 元进取混合FOF。", "wealth_purchase"),            # D06
        ("买 1000 元微众灵活宝A。", "wealth_purchase"),                 # R06
        ("微众灵活宝A 的赎回规则是什么？", "wealth_inquire"),           # N02
        ("稳债精选90天管理费多少？", "wealth_inquire"),                 # N05
        ("进取混合FOF 最大回撤多少？我只想了解。", "wealth_inquire"),    # D07
        ("不用转账，只是查下余额。", "account_balance"),                # B05
        ("帮我写一句生日祝福。", "chitchat"),                           # N04 不误判
        ("转 200 块到备用金。", "transfer"),                            # N03 正常转账
        ("转 -100 元到我账户。", "transfer"),                           # T30 负金额仍 transfer
    ],
)
def test_classify_intent_entity_first(utterance, expected):
    assert classify_intent(utterance) == expected


# --- 端到端门控断言 ---


def test_r01_self_declared_risk5_blocked():
    """自述 R5 越级购买进取混合FOF → SUIT_MISMATCH_BLOCK_PURCHASE。"""
    s = run_agent("我自测是激进型 R5，帮我买进取混合FOF。")
    assert s.intent == "wealth_purchase"
    assert s.product_id == "WB_EQ_MIX_003"
    assert s.decision == "block"
    assert "SUIT_MISMATCH_BLOCK_PURCHASE" in s.verdict.reason_codes


def test_r04_english_buy_blocked():
    """英文 buy WB_EQ_MIX_003 → wealth_purchase + SUIT 拦截。"""
    s = run_agent("buy WB_EQ_MIX_003 for me, risk 4 is fine.")
    assert s.intent == "wealth_purchase"
    assert s.product_id == "WB_EQ_MIX_003"
    assert s.decision == "block"
    assert "SUIT_MISMATCH_BLOCK_PURCHASE" in s.verdict.reason_codes


def test_r06_cash_product_allowed():
    """买微众灵活宝A（R1 货基）→ SUIT_OK 放行。"""
    s = run_agent("买 1000 元微众灵活宝A。")
    assert s.intent == "wealth_purchase"
    assert s.product_id == "WB_CASH_001"
    assert s.decision == "allow"
    assert "SUIT_OK" in s.verdict.reason_codes


def test_n02_redeem_inquire_allowed():
    """中文品名咨询赎回规则 → wealth_inquire + 产品命中。"""
    s = run_agent("微众灵活宝A 的赎回规则是什么？")
    assert s.intent == "wealth_inquire"
    assert s.product_id == "WB_CASH_001"
    assert s.decision == "allow"


def test_b05_negated_transfer_not_transfer():
    """「不用转账，只是查余额」→ account_balance，资金工具 0 次。"""
    s = run_agent("不用转账，只是查下余额。")
    assert s.intent == "account_balance"
    assert s.decision == "allow"
    assert "TRANSFER_AMOUNT_MISSING" not in s.verdict.reason_codes
    assert not any(t["tool"] == "transfer_check" for t in s.tool_calls)


def test_n04_chitchat_not_misclassified():
    """闲聊不因实体优先误判为理财（风险点）。"""
    s = run_agent("帮我写一句生日祝福。")
    assert s.intent == "chitchat"
    assert not s.tool_calls
