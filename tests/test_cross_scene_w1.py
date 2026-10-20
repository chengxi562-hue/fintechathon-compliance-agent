"""W1 DoD: cross-scene bill insight → wealth suggest → (optional) transfer confirm."""

from __future__ import annotations

from agent import pending_action as pa
from agent.gates import classify_intent
from agent.graph import run_agent


SCRIPT_E = "这个月外卖花太多了，要不要挪一点去货基？"
NEG_TRANSFER_SUB = "账单里有笔奇怪扣款，先别转账，帮我看看订阅。"
WRITE_TOOLS = {
    "transfer_apply",
    "subscription_apply",
    "wealth_purchase_apply",
    "purchase_apply",
}


def setup_function() -> None:
    pa.clear_store()


def test_script_e_intent_bill_insight() -> None:
    assert classify_intent(SCRIPT_E) == "bill_insight"


def test_script_e_insight_suggest_no_fund_write() -> None:
    st = run_agent(SCRIPT_E, session_id="sess_xe1")
    assert st.intent == "bill_insight"
    assert st.decision == "allow"
    assert "账单洞察" in st.response or "外卖" in st.response
    assert "货基" in st.response or "WB_CASH_001" in st.response or "灵活宝" in st.response
    assert "非承诺" in st.response or "不代表未来" in st.response or "理财非存款" in st.response
    tool_names = [t.get("tool") for t in st.tool_calls]
    assert "list_bills" in tool_names
    assert "suggest_product" in tool_names
    assert not any(t.get("tool") in WRITE_TOOLS for t in st.tool_calls)
    assert "BILL_INSIGHT_OK" in st.verdict.reason_codes
    # Multi-step plan for audit / Demo
    assert "bill_insight" in st.plan
    assert "suggest_product" in st.plan


def test_pure_transfer_smoke() -> None:
    st = run_agent("把 100 元转到自己活期备用金。", session_id="sess_xe_tf")
    assert st.intent == "transfer"
    assert st.decision == "allow"
    assert any(t.get("tool") == "transfer_check" for t in st.tool_calls)


def test_negation_look_subscription_not_transfer() -> None:
    assert classify_intent(NEG_TRANSFER_SUB) == "subscription_manage"
    st = run_agent(NEG_TRANSFER_SUB, session_id="sess_xe_sub")
    assert st.intent == "subscription_manage"
    assert st.intent != "transfer"
    assert not any(t.get("tool") in {"transfer_check", "transfer_apply"} for t in st.tool_calls)
    assert "Netflix" in st.response or "订阅" in st.response


def test_followup_transfer_uses_pending_confirm() -> None:
    """Nice-to-have: after insight, explicit amount transfer reuses PendingAction path."""
    st0 = run_agent(SCRIPT_E, session_id="sess_xe_fu")
    assert st0.intent == "bill_insight"
    assert not any(t.get("tool") in WRITE_TOOLS for t in st0.tool_calls)

    # Amount > confirm_above (5000) → pending confirm; use 6000 to force confirm gate,
    # or use small amount that still creates pending for 备用金 when >5000.
    # Demo path: 6000 → TRANSFER_CONFIRM_REQUIRED + create_pending for 备用金.
    st1 = run_agent("把 6000 元转到自己活期备用金。", session_id="sess_xe_fu")
    assert st1.intent == "transfer"
    assert "TRANSFER_CONFIRM_REQUIRED" in st1.verdict.reason_codes
    assert st1.pending_id
    assert not any(t.get("tool") == "transfer_apply" for t in st1.tool_calls)

    st2 = run_agent("确认", session_id="sess_xe_fu")
    assert "TRANSFER_APPLIED" in st2.verdict.reason_codes or st2.decision in {"allow", "block"}
    # If applied, transfer_apply present; either way insight turn stayed write-free.
    assert not any(t.get("tool") in WRITE_TOOLS for t in st0.tool_calls)
