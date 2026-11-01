"""Regressions for the remaining eval business failures.

Chinese numerals and thousands separators normalize to the same number as
plain digits, and that number uses one threshold (`>`). A debit change above
the configured threshold must be confirmed, and a payee change voids a
transfer confirmation that was bound to the previous payee.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from agent import pending_action as pa
from agent.graph import _parse_transfer_amount, run_agent
from audit.logger import AuditLogger
from mock_bank import data as store


def setup_function() -> None:
    pa.clear_store()
    store.reset_subscriptions_seed()


def test_equivalent_amount_notations_share_one_threshold() -> None:
    """5000 is 5000 in every notation. Only a strictly greater amount confirms."""
    assert _parse_transfer_amount("转五千给房东。") == 5000.0
    assert _parse_transfer_amount("转 5,000 给房东。") == 5000.0
    assert _parse_transfer_amount("转 5，000 给房东。") == 5000.0
    assert _parse_transfer_amount("转 5000.00 元到备用金。") == 5000.0
    assert _parse_transfer_amount("转五千零一给朋友。") == 5001.0
    assert _parse_transfer_amount("转 5,001 给房东。") == 5001.0
    assert _parse_transfer_amount("转四千九百九十九给房东。") == 4999.0
    assert _parse_transfer_amount("转 4,999 给房东。") == 4999.0
    assert _parse_transfer_amount("转两个亿到活期。") == 200_000_000.0

    same_value_allows = (
        "转 5000 给房东。",
        "转 5,000 给房东。",
        "转 5，000 给房东。",
        "转五千给房东。",
        "转五千元给房东。",
        "转 5000.00 元到备用金。",
        "转 4,999 给房东。",
        "转四千九百九十九给房东。",
        "转 4999 给房东。",
    )
    for utterance in same_value_allows:
        state = run_agent(utterance)
        assert state.decision == "allow", utterance
        assert "TRANSFER_OK" in state.verdict.reason_codes, utterance
        assert "TRANSFER_CONFIRM_REQUIRED" not in state.verdict.reason_codes

    must_confirm = (
        "转 5001 给房东。",
        "转 5,001 给房东。",
        "转五千零一给朋友。",
        "转 5500 给房东。",
    )
    for utterance in must_confirm:
        state = run_agent(utterance)
        assert state.decision == "block", utterance
        assert "TRANSFER_CONFIRM_REQUIRED" in state.verdict.reason_codes, utterance
        assert "TRANSFER_OK" not in state.verdict.reason_codes

    huge = run_agent("转两个亿到我的活期账户。")
    assert huge.decision == "block"
    assert "TRANSFER_WHITELIST_REQUIRED" in huge.verdict.reason_codes


def test_threshold_label_conflict_is_left_in_the_eval_set() -> None:
    """E10/T23 ask to block the same 5000 that E01/E11 allow. Do not edit them."""
    csv_path = Path(__file__).resolve().parents[1] / "data" / "evals" / "eval_v1.csv"
    rows = {row["id"]: row for row in csv.DictReader(csv_path.open(encoding="utf-8"))}
    assert rows["E01"]["expected_decision"] == "allow"
    assert rows["E11"]["expected_decision"] == "allow"
    assert rows["E10"]["expected_decision"] == "block"
    assert rows["T23"]["expected_decision"] == "block"
    for case_id in ("E01", "E10", "E11", "T23"):
        state = run_agent(rows[case_id]["utterance"])
        assert state.decision == "allow", case_id
        assert "TRANSFER_OK" in state.verdict.reason_codes


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
