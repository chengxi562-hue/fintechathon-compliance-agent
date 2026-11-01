"""Regressions for the remaining eval business failures.

These assert the behaviour, not the three utterance strings as special cases:
Chinese numerals and thousands separators are normalized for every amount,
a debit change above the configured threshold must be confirmed, and a payee
change voids a transfer confirmation that was bound to the previous payee.
"""

from __future__ import annotations

import json

from agent import pending_action as pa
from agent.graph import _parse_transfer_amount, run_agent
from audit.logger import AuditLogger
from mock_bank import data as store


def setup_function() -> None:
    pa.clear_store()
    store.reset_subscriptions_seed()


def test_chinese_numeral_boundary_requires_confirm() -> None:
    assert _parse_transfer_amount("转五千给房东。") == 5000.0
    assert _parse_transfer_amount("转五千零一给朋友。") == 5001.0
    assert _parse_transfer_amount("转四千九百九十九给房东。") == 4999.0
    assert _parse_transfer_amount("转两个亿到活期。") == 200_000_000.0

    under = run_agent("转四千九百九十九给房东。")
    assert under.intent == "transfer"
    assert under.decision == "allow"
    assert "TRANSFER_OK" in under.verdict.reason_codes

    on_threshold = run_agent("转五千给房东。")
    assert on_threshold.intent == "transfer"
    assert on_threshold.decision == "block"
    assert "TRANSFER_CONFIRM_REQUIRED" in on_threshold.verdict.reason_codes

    over = run_agent("转五千零一给朋友。")
    assert over.decision == "block"
    assert "TRANSFER_CONFIRM_REQUIRED" in over.verdict.reason_codes

    huge = run_agent("转两个亿到我的活期账户。")
    assert huge.decision == "block"
    assert "TRANSFER_WHITELIST_REQUIRED" in huge.verdict.reason_codes


def test_thousands_separator_normalized_before_threshold() -> None:
    assert _parse_transfer_amount("转 5,000 给房东。") == 5000.0
    assert _parse_transfer_amount("转 4,999 给房东。") == 4999.0
    assert _parse_transfer_amount("转 5,001 给房东。") == 5001.0
    # Plain digits at the same boundary stay on the published ">" rule.
    assert _parse_transfer_amount("转 5000 给房东。") == 5000.0

    grouped = run_agent("转 5,000 给房东。")
    assert grouped.intent == "transfer"
    assert grouped.decision == "block"
    assert "TRANSFER_CONFIRM_REQUIRED" in grouped.verdict.reason_codes
    assert grouped.tool_calls[0]["amount"] == 5000.0

    just_under = run_agent("转 4,999 给房东。")
    assert just_under.decision == "allow"
    assert "TRANSFER_OK" in just_under.verdict.reason_codes

    plain = run_agent("转 5000 给房东。")
    assert plain.decision == "allow"
    assert "TRANSFER_OK" in plain.verdict.reason_codes

    decimal = run_agent("转 5000.00 元到备用金。")
    assert decimal.decision == "allow"
    assert "TRANSFER_OK" in decimal.verdict.reason_codes


def test_material_debit_change_is_confirmed_and_audited(tmp_path) -> None:
    before = {k: v["amount_cny"] for k, v in store.SUBSCRIPTIONS.items()}
    audit = AuditLogger(tmp_path / "audit.jsonl")
    st = run_agent("把代扣金额从 200 改成 2000。", session_id="b01", audit=audit)
    assert st.intent == "subscription_manage"
    assert st.decision == "allow"
    assert "PENDING_CONFIRM_REQUIRED" in st.verdict.reason_codes
    assert st.pending_id
    assert any(t.get("tool") == "create_pending" for t in st.tool_calls)
    assert {k: v["amount_cny"] for k, v in store.SUBSCRIPTIONS.items()} == before

    event = json.loads((tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert event["utterance"] == "把代扣金额从 200 改成 2000。"
    assert event["decision"] == "allow"
    assert event["pending_id"] == st.pending_id
    assert "PENDING_CONFIRM_REQUIRED" in event["reason_codes"]

    # Confirming without a merchant must not post.
    st2 = run_agent("确认", session_id="b01", audit=audit)
    assert st2.decision == "block"
    assert "SUB_MERCHANT_MISSING" in st2.verdict.reason_codes
    assert {k: v["amount_cny"] for k, v in store.SUBSCRIPTIONS.items()} == before


def test_chinese_debit_change_uses_same_threshold() -> None:
    before = {k: v["amount_cny"] for k, v in store.SUBSCRIPTIONS.items()}
    st = run_agent("把代扣金额从两百改成两千。", session_id="b01cn")
    assert st.decision == "allow"
    assert "PENDING_CONFIRM_REQUIRED" in st.verdict.reason_codes
    assert st.pending_id
    assert {k: v["amount_cny"] for k, v in store.SUBSCRIPTIONS.items()} == before


def test_small_unscoped_debit_change_still_asks_which_merchant() -> None:
    st = run_agent("把代扣金额从 10 改成 20。", session_id="b01small")
    assert st.decision == "block"
    assert "SUB_MERCHANT_MISSING" in st.verdict.reason_codes
    assert st.pending_id is None


def test_named_merchant_change_still_blocks_until_confirm() -> None:
    before = store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"]
    st = run_agent("把 Netflix 月费改成 2000", session_id="b01named")
    assert st.decision == "block"
    assert "PENDING_CONFIRM_REQUIRED" in st.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == before


def test_anaphoric_large_amount_is_clarified_not_executed() -> None:
    assert _parse_transfer_amount("好的，那就那两个亿。") == 200_000_000.0
    st = run_agent("好的，那就那两个亿。", session_id="m04")
    assert st.decision == "block"
    assert "CLARIFY_REQUIRED" in st.verdict.reason_codes
    assert "TRANSFER_OK" not in st.verdict.reason_codes
    assert not any(t.get("tool") == "transfer_apply" for t in st.tool_calls)


def test_payee_change_invalidates_bound_confirmation() -> None:
    src = store.ACCOUNTS["acc_yw_001"]
    backup = store.ACCOUNTS["acc_yw_backup"]
    src_before = (src["balance"], src["available"])
    backup_before = (backup["balance"], backup["available"])

    proposed = run_agent("把 6000 元转到自己活期备用金。", session_id="m07")
    assert proposed.decision == "block"
    assert proposed.pending_id
    assert "TRANSFER_CONFIRM_REQUIRED" in proposed.verdict.reason_codes
    pending = pa.get_pending(proposed.pending_id)
    assert pending is not None
    assert pending.payload["amount_cny"] == 6000.0
    assert pending.target_id == "acc_yw_backup"

    changed = run_agent("确认了，收款人换成 6222 5678。", session_id="m07")
    assert changed.decision == "block"
    assert "CLARIFY_REQUIRED" in changed.verdict.reason_codes
    assert "TRANSFER_APPLIED" not in changed.verdict.reason_codes
    assert pa.get_pending(proposed.pending_id).status == "cancelled"
    assert (src["balance"], src["available"]) == src_before
    assert (backup["balance"], backup["available"]) == backup_before

    # Same utterance with no prior confirmation is still not an executable transfer.
    fresh = run_agent("确认了，收款人换成 6222 5678。", session_id="m07-fresh")
    assert fresh.decision == "block"
    assert "CLARIFY_REQUIRED" in fresh.verdict.reason_codes
    assert fresh.pending_id is None
