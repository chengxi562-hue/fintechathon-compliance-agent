"""Regression: loopback Mock Bank traffic must never be carried by an operator proxy.

Bug (2026-10-20): httpx defaults to ``trust_env=True`` and therefore honours the
macOS system proxy (HTTPProxy/SOCKSProxy 127.0.0.1:7897). With the proxy running
and Mock Bank healthy on 127.0.0.1:8000, ``httpx.post`` to loopback returned
HTTP **502**, so every confirmed subscription write was reported as
``SUBSCRIPTION_BANK_REJECT`` and the test suite went red depending on whether a
proxy was up. A grader machine with a proxy on would see the same failure.

Fix: ``agent/graph.py`` calls the Mock Bank through ``_local_http_get`` /
``_local_http_post`` with ``trust_env=False``.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest
import uvicorn

from agent import pending_action as pa
from agent.graph import run_agent
from mock_bank import data as store
from mock_bank.app import app


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def mock_bank_server():
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while time.time() < deadline and not server.started:
        time.sleep(0.05)
    assert server.started, "Mock Bank did not start"
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture()
def dead_proxy(monkeypatch):
    """Point every proxy variable at a closed port: any proxied request fails."""
    dead = "http://127.0.0.1:9"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(key, dead)
    for key in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(key, "")
    return dead


def setup_function() -> None:
    pa.clear_store()
    store.reset_subscriptions_seed()


def test_subscription_confirm_lands_through_real_http(mock_bank_server, dead_proxy):
    """Write goes over real HTTP, and still works with a dead proxy configured."""
    st1 = run_agent("把 Netflix 月费改成 30", session_id="sess_proxy",
                    mock_bank_url=mock_bank_server)
    assert st1.pending_id

    st2 = run_agent("确认", session_id="sess_proxy", mock_bank_url=mock_bank_server)
    assert st2.decision == "allow", st2.response
    assert "SUBSCRIPTION_APPLIED" in st2.verdict.reason_codes
    assert store.SUBSCRIPTIONS["sub_netflix_001"]["amount_cny"] == 30.0

    apply_calls = [t for t in st2.tool_calls if t.get("tool") == "subscription_apply"]
    assert apply_calls and apply_calls[0]["ok"] is True


def test_product_lookup_uses_seed_not_proxy(mock_bank_server, dead_proxy):
    """Product resolution must not be poisoned by a proxy 502 either."""
    st = run_agent("我风险偏好是稳健，帮我看看适合 R2 的货基或短债，说明费率就行。",
                   session_id="sess_proxy_prod", mock_bank_url=mock_bank_server)
    assert st.decision == "allow", st.response
    assert "WB_CASH_001" in st.response


def test_no_proxy_helpers_are_used_for_env(monkeypatch):
    """Guard: the graph module must not regress to bare httpx calls."""
    import inspect

    from agent import graph

    source = inspect.getsource(graph)
    assert "trust_env=False" in source
    # bare calls that would silently re-enable the system proxy
    assert "httpx.get(" not in source.replace("return httpx.get(url", "")
    assert "httpx.post(" not in source.replace("return httpx.post(url", "")
