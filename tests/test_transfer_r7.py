"""Synthetic R7/W1-b regression tests; local MockBank state only."""
from copy import deepcopy
import json
import pytest

from agent import pending_action as pa
from agent.graph import run_agent
from audit.logger import AuditLogger
from mock_bank import data as store


@pytest.fixture(autouse=True)
def reset_demo_state():
    snapshot = store.snapshot()
    pa.clear_store()
    yield
    for name in ("CUSTOMERS", "ACCOUNTS", "PRODUCTS", "SUBSCRIPTIONS"):
        value = getattr(store, name)
        value.clear()
        value.update(snapshot[name.lower()])
    store.TRANSFERS[:] = snapshot["transfers"]
    pa.clear_store()


def propose(session="r7", amount=6000):
    return run_agent(f"转账{amount}元到自己活期备用金", session_id=session)


def test_transfer_confirm_posts_once_and_audits_same_pending(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLogger(audit_path)
    before = store.snapshot()
    first = run_agent("转账6000元到自己活期备用金", session_id="r7", audit=audit)
    assert first.intent == "transfer" and first.decision == "block"
    pending = pa.get_pending(first.pending_id)
    assert pending.action == "transfer" and pending.target_id == "acc_yw_backup"
    assert pending.payload["amount_cny"] == 6000
    assert pending.expires_at - pending.created_at == pa.DEFAULT_TTL_SEC
    assert store.snapshot() == before
    final = run_agent("确认", session_id="r7", audit=audit)
    assert final.intent == "transfer" and final.decision == "allow"
    assert final.pending_id == first.pending_id
    assert "TRANSFER_APPLIED" in final.verdict.reason_codes
    assert len(store.TRANSFERS) == len(before["transfers"]) + 1
    tx = store.TRANSFERS[-1]
    assert tx["amount_cny"] == 6000 and tx["to_account_id"] == "acc_yw_backup"
    assert store.ACCOUNTS["acc_yw_001"]["available"] == before["accounts"]["acc_yw_001"]["available"] - 6000
    assert store.ACCOUNTS["acc_yw_backup"]["available"] == before["accounts"]["acc_yw_backup"]["available"] + 6000
    for field in ("balance", "available"):
        assert sum(a[field] for a in store.ACCOUNTS.values()) == sum(a[field] for a in before["accounts"].values())
    assert store.SUBSCRIPTIONS == before["subscriptions"]
    rows = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert [row["decision"] for row in rows] == ["block", "allow"]
    assert {row["pending_id"] for row in rows} == {first.pending_id}
    assert rows[-1]["tool_calls"][0]["data"]["status"] == "posted"


@pytest.mark.parametrize("reply", ["取消", "取消转账", "不转了", "拒绝", "不确认"])
def test_cancel_or_refuse_never_posts(reply):
    before = store.snapshot()
    first = propose()
    result = run_agent(reply, session_id="r7")
    assert result.decision == "allow" and "PENDING_CANCELLED" in result.verdict.reason_codes
    assert pa.get_pending(first.pending_id).status == "cancelled"
    replay = run_agent("确认", session_id="r7")
    assert replay.decision == "block"
    assert "PENDING_NOT_PENDING:cancelled" in replay.verdict.reason_codes
    assert store.snapshot() == before


def test_wrong_session_cannot_confirm_or_cancel():
    before = store.snapshot()
    first = propose("owner")
    code, _ = pa.confirm_pending(first.pending_id, session_id="other")
    assert code == "PENDING_SESSION_MISMATCH"
    code, _ = pa.cancel_pending(first.pending_id, session_id="other")
    assert code == "PENDING_SESSION_MISMATCH"
    for reply in ("确认", "取消"):
        result = run_agent(reply, session_id="other")
        assert result.decision == "block" and "PENDING_NOT_FOUND" in result.verdict.reason_codes
    assert pa.get_pending(first.pending_id).status == "pending"
    assert store.snapshot() == before


def test_same_session_different_customer_cannot_confirm():
    first = propose()
    store.CUSTOMERS["cust_test_other"] = {**store.CUSTOMERS["cust_yw_001"], "customer_id": "cust_test_other"}
    before = store.snapshot()
    result = run_agent("确认", customer_id="cust_test_other", session_id="r7")
    assert result.decision == "block"
    assert "PENDING_CUSTOMER_MISMATCH" in result.verdict.reason_codes
    assert pa.get_pending(first.pending_id).status == "pending"
    assert store.snapshot() == before


@pytest.mark.parametrize("reply", ["确认", "取消"])
def test_expired_confirmation_or_cancellation_does_not_write(reply):
    before = store.snapshot()
    first = propose()
    pa.get_pending(first.pending_id).expires_at = 0
    result = run_agent(reply, session_id="r7")
    assert result.decision == "block"
    assert any("EXPIRED" in reason or "expired" in reason for reason in result.verdict.reason_codes)
    assert store.snapshot() == before


def test_repeated_confirmation_does_not_post_again():
    propose()
    run_agent("确认", session_id="r7")
    before = store.snapshot()
    again = run_agent("确认执行", session_id="r7")
    assert again.decision == "block" and "PENDING_NOT_PENDING:confirmed" in again.verdict.reason_codes
    assert store.snapshot() == before


@pytest.mark.parametrize("utterance,reason", [
    ("转账25000元到自己活期备用金", "TRANSFER_SOFT_LIMIT"),
    ("转60000给陌生人", "TRANSFER_WHITELIST_REQUIRED"),
    ("转账-100元到自己活期备用金", "TRANSFER_AMOUNT_INVALID"),
    ("付给房东房租5500", "TRANSFER_RECIPIENT_MISSING"),
    ("转账6000给房东，从自己的账户扣", "TRANSFER_RECIPIENT_MISSING"),
    ("转账6000元到自己活期备用金，再转6000元到自己活期备用金", "TRANSFER_BATCH_UNSUPPORTED"),
])
def test_refused_proposals_never_get_an_executable_pending(utterance, reason):
    before = store.snapshot()
    result = run_agent(utterance, session_id="r7")
    assert result.decision == "block" and reason in result.verdict.reason_codes
    assert result.pending_id is None
    assert run_agent("确认", session_id="r7").decision == "block"
    assert store.snapshot() == before


def test_mock_bank_rejection_is_terminal_and_never_changes_subscriptions():
    propose()
    store.ACCOUNTS["acc_yw_001"]["available"] = 100
    before = store.snapshot()
    result = run_agent("确认", session_id="r7")
    assert result.decision == "block" and "TRANSFER_BANK_REJECT" in result.verdict.reason_codes
    assert result.tool_calls[0]["ok"] is False
    assert store.snapshot() == before
    store.ACCOUNTS["acc_yw_001"]["available"] = 10000
    before_retry = store.snapshot()
    retry = run_agent("确认", session_id="r7")
    assert retry.decision == "block" and "PENDING_NOT_PENDING:confirmed" in retry.verdict.reason_codes
    assert store.snapshot() == before_retry


def test_bill_wealth_transfer_confirmation_chain():
    before = store.snapshot()
    bills = run_agent("查看我的订阅和代扣", session_id="r7")
    wealth = run_agent("介绍低风险货币基金", session_id="r7")
    assert bills.decision == wealth.decision == "allow"
    assert all(t["tool"] not in {"transfer_apply", "subscription_apply"} for s in (bills, wealth) for t in s.tool_calls)
    assert store.snapshot() == before
    first = propose()
    result = run_agent("确认", session_id="r7")
    assert result.intent == "transfer" and "TRANSFER_APPLIED" in result.verdict.reason_codes
    assert result.pending_id == first.pending_id


def test_latest_transfer_confirmation_never_applies_older_subscription():
    sub = run_agent("把Netflix月费改成30", session_id="r7")
    first = propose()
    before_sub = deepcopy(store.SUBSCRIPTIONS)
    result = run_agent("确认", session_id="r7")
    assert result.intent == "transfer" and result.pending_id == first.pending_id
    again = run_agent("确认", session_id="r7")
    assert again.decision == "block"
    assert pa.get_pending(sub.pending_id).status == "cancelled"
    assert store.SUBSCRIPTIONS == before_sub


def test_latest_subscription_confirmation_never_posts_older_transfer():
    first = propose()
    sub = run_agent("把Netflix月费改成30", session_id="r7")
    before_accounts = deepcopy(store.ACCOUNTS)
    result = run_agent("确认", session_id="r7")
    assert result.intent == "subscription_manage" and result.pending_id == sub.pending_id
    assert "SUBSCRIPTION_APPLIED" in result.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 30
    assert run_agent("确认", session_id="r7").decision == "block"
    assert pa.get_pending(first.pending_id).status == "cancelled"
    assert store.ACCOUNTS == before_accounts


def test_latest_subscription_proposal_wins_and_cancel_does_not_reveal_old_one():
    run_agent("把Netflix月费改成30", session_id="r7")
    latest = run_agent("把Netflix月费改成40", session_id="r7")
    result = run_agent("取消", session_id="r7")
    assert result.pending_id == latest.pending_id and result.decision == "allow"
    assert run_agent("确认", session_id="r7").decision == "block"
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 68


def test_explicit_transfer_reply_does_not_confirm_subscription():
    run_agent("把Netflix月费改成30", session_id="r7")
    before = store.snapshot()
    result = run_agent("确认转账", session_id="r7")
    assert result.decision == "block" and "PENDING_ACTION_MISMATCH" in result.verdict.reason_codes
    assert store.snapshot() == before


def test_changed_recipient_is_rejected_before_posting():
    propose()
    store.ACCOUNTS["acc_yw_backup"]["customer_id"] = "cust_test_other"
    before = store.snapshot()
    result = run_agent("确认", session_id="r7")
    assert result.decision == "block" and "TRANSFER_RECIPIENT_MISMATCH" in result.verdict.reason_codes
    assert store.snapshot() == before


@pytest.mark.parametrize("latest_request", [
    "转账25000元到自己活期备用金",
    "转60000给陌生人",
    "转账6000给房东",
    "把不存在商家的订阅月费改成30",
])
def test_rejected_new_write_cancels_old_transfer(latest_request):
    before = store.snapshot()
    first = propose()
    rejected = run_agent(latest_request, session_id="r7")
    assert rejected.decision == "block" and rejected.pending_id is None
    assert pa.get_pending(first.pending_id).status == "cancelled"
    result = run_agent("确认", session_id="r7")
    assert result.decision == "block"
    assert store.snapshot() == before


def test_rejected_transfer_cannot_confirm_older_subscription():
    before = store.snapshot()
    first = run_agent("把Netflix月费改成30", session_id="r7")
    assert propose(amount=25000).decision == "block"
    assert pa.get_pending(first.pending_id).status == "cancelled"
    assert run_agent("确认", session_id="r7").decision == "block"
    assert store.snapshot() == before
