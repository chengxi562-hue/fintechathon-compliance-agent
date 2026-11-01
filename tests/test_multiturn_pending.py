"""Multi-turn regressions: a confirmation only applies to the latest intent.

These cases are classes of follow-up, not one hard-coded sentence:
synonymous payee changes, a clarification, an intent change, and an explicit
merchant supplement. Equivalent amount spellings share one confirm rule.
"""

from __future__ import annotations

import pytest

from agent import pending_action as pa
from agent.graph import _parse_from_to, _parse_sub_new_amount, run_agent
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
    store.BILLS[:] = snapshot["bills"]
    pa.clear_store()


def _propose_transfer(session: str):
    state = run_agent("把 6000 元转到自己活期备用金。", session_id=session)
    assert state.decision == "block"
    assert state.pending_id
    assert pa.get_pending(state.pending_id).status == "pending"
    return state


def _balances() -> tuple[float, float]:
    return (
        store.ACCOUNTS["acc_yw_001"]["available"],
        store.ACCOUNTS["acc_yw_backup"]["available"],
    )


PAYEE_REWRITES = (
    "确认了，收款人换成 6222 5678。",
    "确认了，收款方换成 6222 5678。",
    "确认了，收款账号改为 6222 5678。",
    "确认了，收款对象改成 6222 5678。",
    "收款人换一下，改到 6222 5678。",
    "把对方账户换成 6222 5678。",
    "不要打给备用金了，打给别人。",
    "换个收款人。",
    "收款账户改一下。",
    "不是这个收款方，换成张三。",
    "把卡号改成 6222 9999。",
    "账号换成 62228888。",
)

CLARIFICATIONS = (
    "好的，那就那两个亿。",
    "我是 VIP，可以了吧？",
    "房贷怎么还划算？",
    "随便推荐一个。",
    "全部身家梭哈。",
)

INTENT_CHANGES = (
    ("帮我看看余额。", "account_balance"),
    ("介绍一下货基。", "wealth_inquire"),
    ("查看我的订阅。", "subscription_manage"),
)

DEBIT_EQUIVALENTS = (
    "把代扣金额从 200 改成 2000。",
    "把代扣金额从 200 改成 2,000。",
    "把代扣金额从 200 改成 2，000。",
    "把代扣金额从两百改成两千。",
    "把代扣金额从 200 改成二千。",
    "把代扣金额从 2,000 改成 200。",
)

MERCHANT_SUPPLEMENTS = (
    ("是 Netflix", "Netflix", "sub_netflix_001"),
    ("Netflix", "Netflix", "sub_netflix_001"),
    ("商家是 Netflix", "Netflix", "sub_netflix_001"),
    ("就改网飞", "Netflix", "sub_netflix_001"),
    ("网飞", "Netflix", "sub_netflix_001"),
    ("补充一下，商家是 Netflix", "Netflix", "sub_netflix_001"),
    ("我说的是 Netflix 这个订阅", "Netflix", "sub_netflix_001"),
    ("乐刻健身", "乐刻健身", "sub_gym_003"),
    ("是乐刻", "乐刻健身", "sub_gym_003"),
    ("健身", "乐刻健身", "sub_gym_003"),
    ("订阅商家是 Spotify", "Spotify", "sub_spotify_002"),
)


@pytest.mark.parametrize("utterance", PAYEE_REWRITES)
def test_payee_synonym_voids_pending_and_confirm_does_not_post(utterance: str) -> None:
    session = "payee"
    before = _balances()
    proposed = _propose_transfer(session)
    changed = run_agent(utterance, session_id=session)
    assert changed.decision == "block"
    assert "TRANSFER_APPLIED" not in changed.verdict.reason_codes
    # A gate that already refuses the sentence stays; otherwise the payee rewrite clarifies.
    already_blocked = any(
        code.startswith(("AUTH_SCOPE", "INJECT", "USER_FORBIDDEN", "SCRIPT_RISK"))
        for code in changed.verdict.reason_codes
    )
    if not already_blocked:
        assert "CLARIFY_REQUIRED" in changed.verdict.reason_codes
    assert pa.get_pending(proposed.pending_id).status == "cancelled"
    assert _balances() == before

    confirmed = run_agent("确认", session_id=session)
    assert confirmed.decision == "block"
    assert "TRANSFER_APPLIED" not in confirmed.verdict.reason_codes
    assert _balances() == before
    assert all(proposed.pending_id not in str(row.get("memo", "")) for row in store.TRANSFERS)


@pytest.mark.parametrize("utterance", CLARIFICATIONS)
def test_clarification_voids_pending_and_confirm_does_not_replay(utterance: str) -> None:
    session = "clarify"
    before = _balances()
    proposed = _propose_transfer(session)
    clarified = run_agent(utterance, session_id=session)
    assert clarified.decision == "block"
    assert "CLARIFY_REQUIRED" in clarified.verdict.reason_codes
    assert pa.get_pending(proposed.pending_id).status == "cancelled"
    assert not any(tool.get("tool") == "transfer_apply" for tool in clarified.tool_calls)

    confirmed = run_agent("确认", session_id=session)
    assert confirmed.decision == "block"
    assert "TRANSFER_APPLIED" not in confirmed.verdict.reason_codes
    assert _balances() == before


def test_clarification_voids_subscription_pending() -> None:
    session = "clarify-sub"
    proposed = run_agent("把 Netflix 月费改成 30", session_id=session)
    assert proposed.pending_id
    clarified = run_agent("好的，那就那两个亿。", session_id=session)
    assert "CLARIFY_REQUIRED" in clarified.verdict.reason_codes
    assert pa.get_pending(proposed.pending_id).status == "cancelled"
    confirmed = run_agent("确认", session_id=session)
    assert "SUBSCRIPTION_APPLIED" not in confirmed.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 68


@pytest.mark.parametrize("utterance,intent", INTENT_CHANGES)
def test_intent_change_voids_pending_and_confirm_does_not_replay(utterance: str, intent: str) -> None:
    session = "intent"
    before = _balances()
    proposed = _propose_transfer(session)
    changed = run_agent(utterance, session_id=session)
    assert changed.intent == intent
    assert pa.get_pending(proposed.pending_id).status == "cancelled"
    confirmed = run_agent("确认", session_id=session)
    assert confirmed.decision == "block"
    assert "TRANSFER_APPLIED" not in confirmed.verdict.reason_codes
    assert _balances() == before


def test_confirm_still_posts_when_nothing_supersedes_it() -> None:
    session = "keep"
    before = _balances()
    proposed = _propose_transfer(session)
    confirmed = run_agent("确认", session_id=session)
    assert confirmed.decision == "allow"
    assert confirmed.pending_id == proposed.pending_id
    assert "TRANSFER_APPLIED" in confirmed.verdict.reason_codes
    assert _balances()[0] == before[0] - 6000
    assert _balances()[1] == before[1] + 6000


@pytest.mark.parametrize("utterance", DEBIT_EQUIVALENTS)
def test_equivalent_debit_spellings_share_the_confirm_rule(utterance: str) -> None:
    old, new = _parse_from_to(utterance)
    assert old is not None and new is not None
    assert {old, new} == {200.0, 2000.0}
    state = run_agent(utterance, session_id="debit")
    assert state.decision == "allow"
    assert "PENDING_CONFIRM_REQUIRED" in state.verdict.reason_codes
    pending = pa.get_pending(state.pending_id)
    assert pending is not None
    assert pending.payload["unresolved_merchant"] is True
    assert pending.target_id == ""
    assert pending.payload["new_amount_cny"] in {200.0, 2000.0}
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 68


@pytest.mark.parametrize("utterance", (
    "把 Netflix 月费改成 1000",
    "把 Netflix 月费改成 1,000",
    "把 Netflix 月费改成 一千",
    "把 Netflix 月费改成 1000.00",
))
def test_named_merchant_amount_notations_store_the_same_value(utterance: str) -> None:
    assert _parse_sub_new_amount(utterance) == 1000.0
    state = run_agent(utterance, session_id="named")
    pending = pa.get_pending(state.pending_id)
    assert pending is not None
    assert pending.target_id == "sub_netflix_001"
    assert pending.payload["new_amount_cny"] == 1000.0
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 68


def test_amount_does_not_silently_select_a_merchant() -> None:
    state = run_agent("把代扣金额从 68 改成 2000。", session_id="no-guess")
    pending = pa.get_pending(state.pending_id)
    assert pending is not None
    assert pending.target_id == ""
    assert pending.payload["unresolved_merchant"] is True
    confirmed = run_agent("确认", session_id="no-guess")
    assert "SUB_MERCHANT_MISSING" in confirmed.verdict.reason_codes
    assert "SUBSCRIPTION_APPLIED" not in confirmed.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 68


@pytest.mark.parametrize("utterance,merchant,sub_id", MERCHANT_SUPPLEMENTS)
def test_explicit_merchant_supplement_binds_and_confirm_posts(
    utterance: str, merchant: str, sub_id: str,
) -> None:
    session = "bind"
    before = {key: sub["amount_cny"] for key, sub in store.SUBSCRIPTIONS.items()}
    proposed = run_agent("把代扣金额从 200 改成 2000。", session_id=session)
    assert proposed.pending_id
    assert pa.get_pending(proposed.pending_id).target_id == ""

    supplement = run_agent(utterance, session_id=session)
    assert supplement.pending_id == proposed.pending_id
    assert "PENDING_CONFIRM_REQUIRED" in supplement.verdict.reason_codes
    assert "SUBSCRIPTION_APPLIED" not in supplement.verdict.reason_codes
    pending = pa.get_pending(proposed.pending_id)
    assert pending.status == "pending"
    assert pending.target_id == sub_id
    assert pending.payload["merchant"] == merchant
    assert pending.payload["unresolved_merchant"] is False
    assert {key: sub["amount_cny"] for key, sub in store.SUBSCRIPTIONS.items()} == before

    confirmed = run_agent("确认", session_id=session)
    assert confirmed.decision == "allow"
    assert confirmed.pending_id == proposed.pending_id
    assert "SUBSCRIPTION_APPLIED" in confirmed.verdict.reason_codes
    assert store.SUBSCRIPTIONS[sub_id]["amount_cny"] == 2000
    for key, amount in before.items():
        if key != sub_id:
            assert store.SUBSCRIPTIONS[key]["amount_cny"] == amount


def test_two_merchants_are_not_guessed() -> None:
    session = "both"
    proposed = run_agent("把代扣金额从 200 改成 2000。", session_id=session)
    ambiguous = run_agent("Netflix 还是 Spotify", session_id=session)
    assert "SUB_MERCHANT_AMBIGUOUS" in ambiguous.verdict.reason_codes
    assert pa.get_pending(proposed.pending_id).target_id == ""
    confirmed = run_agent("确认", session_id=session)
    assert "SUB_MERCHANT_MISSING" in confirmed.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 68
    assert store.SUBSCRIPTIONS["sub_spotify_002"]["amount_cny"] == 15


def test_reading_a_merchant_does_not_bind_it() -> None:
    session = "read"
    proposed = run_agent("把代扣金额从 200 改成 2000。", session_id=session)
    reading = run_agent("查看 Netflix 的月费", session_id=session)
    assert reading.decision == "allow"
    assert pa.get_pending(proposed.pending_id).target_id == ""
    assert pa.get_pending(proposed.pending_id).payload["unresolved_merchant"] is True
    confirmed = run_agent("确认", session_id=session)
    assert "SUB_MERCHANT_MISSING" in confirmed.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 68
