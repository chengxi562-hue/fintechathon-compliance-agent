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


# ---------------------------------------------------------------------------
# MOCK_BANK_URL plumbing (2026-10-20)
#
# .env.example has advertised MOCK_BANK_URL since W0, but nothing read it: every
# call fell back to the hard-coded 127.0.0.1:8000. That made the suite depend on
# the coincidence that no Mock Bank was running — README step 2 starts one, step 4
# runs pytest, and doing both failed two confirmation tests because they took the
# HTTP branch and asserted against local memory.
# ---------------------------------------------------------------------------


def test_mock_bank_url_env_is_honoured(monkeypatch):
    from agent.graph import _default_bank_url

    monkeypatch.delenv("MOCK_BANK_URL", raising=False)
    assert _default_bank_url() == "http://127.0.0.1:8000"

    monkeypatch.setenv("MOCK_BANK_URL", "http://127.0.0.1:59999")
    assert _default_bank_url() == "http://127.0.0.1:59999"


def test_explicit_argument_beats_env(monkeypatch):
    """A caller-supplied URL must win so tests can target their own server."""
    monkeypatch.setenv("MOCK_BANK_URL", "http://127.0.0.1:59999")
    called = {}

    from agent import graph

    real_post = graph._local_http_post

    def spy(url, payload):
        called["url"] = url
        return real_post(url, payload)

    monkeypatch.setattr(graph, "_local_http_post", spy)
    graph.pa.clear_store()
    graph.run_agent("把 Spotify 月费改成 9", session_id="envarg",
                    mock_bank_url="http://127.0.0.1:12345")
    graph.run_agent("确认", session_id="envarg", mock_bank_url="http://127.0.0.1:12345")
    assert "127.0.0.1:12345" in called.get("url", "")


def test_confirmation_tests_cannot_reach_a_real_listener():
    """Guard: with the session conftest, the default URL must not be a live server."""
    import os

    from agent.graph import _default_bank_url

    url = os.environ.get("MOCK_BANK_URL") or _default_bank_url()
    assert "8000" not in url, (
        "conftest must pin MOCK_BANK_URL to an unused port; otherwise running "
        "pytest while a Mock Bank is up changes which process receives the write"
    )
