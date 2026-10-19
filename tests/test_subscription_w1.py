"""W1 DoD: subscription read APIs + PendingAction confirm gate."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from agent import pending_action as pa
from agent.graph import run_agent
from agent.pending_action import create_pending, confirm_pending
from mock_bank import data as store
from mock_bank.app import app


client = TestClient(app)


def setup_function() -> None:
    pa.clear_store()
    store.reset_subscriptions_seed()


def test_subscriptions_and_bills_readonly_nonempty() -> None:
    r = client.get("/v1/customers/cust_yw_001/subscriptions")
    assert r.status_code == 200
    assert len(r.json()) >= 3
    r2 = client.get("/v1/customers/cust_yw_001/bills")
    assert r2.status_code == 200
    assert len(r2.json()) >= 5


def test_bank_refuses_unconfirmed_write() -> None:
    before = store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"]
    r = client.post(
        "/v1/subscriptions/sub_netflix_001/apply",
        json={
            "customer_id": "cust_yw_001",
            "action": "change_amount",
            "new_amount_cny": 30,
            "confirmed": False,
        },
    )
    assert r.status_code == 403
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == before


def test_unconfirmed_agent_write_does_not_mutate_seed() -> None:
    before = store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"]
    st = run_agent("把 Netflix 月费改成 30", session_id="sess_t1")
    assert st.intent == "subscription_manage"
    assert "PENDING_CONFIRM_REQUIRED" in st.verdict.reason_codes
    assert st.pending_id
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == before


def test_confirm_then_write() -> None:
    before = store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"]
    st1 = run_agent("把 Netflix 月费改成 30", session_id="sess_t2")
    assert st1.pending_id
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == before
    st2 = run_agent("确认", session_id="sess_t2")
    assert st2.decision == "allow"
    assert "SUBSCRIPTION_APPLIED" in st2.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 30.0
    assert st2.pending_id == st1.pending_id


def test_expired_pending_does_not_write() -> None:
    before = store.SUBSCRIPTIONS["sub_spotify_002"]["amount_cny"]
    pend = create_pending(
        session_id="sess_exp",
        customer_id="cust_yw_001",
        action="change_amount",
        target_id="sub_spotify_002",
        payload={"new_amount_cny": 9.0},
        before={"amount_cny": before},
        ttl_sec=1,
    )
    time.sleep(1.1)
    code, _ = confirm_pending(pend.pending_id, session_id="sess_exp")
    assert code == "PENDING_EXPIRED"
    assert store.SUBSCRIPTIONS["sub_spotify_002"]["amount_cny"] == before
    # Agent path
    st = run_agent("确认", session_id="sess_exp")
    assert store.SUBSCRIPTIONS["sub_spotify_002"]["amount_cny"] == before
    assert "PENDING_EXPIRED" in st.verdict.reason_codes or "PENDING_NOT_FOUND" in st.verdict.reason_codes or st.decision == "block"


def test_list_subscriptions_via_agent() -> None:
    st = run_agent("查看我的订阅和代扣", session_id="sess_list")
    assert st.intent == "subscription_manage"
    assert st.decision == "allow"
    assert "Netflix" in st.response
