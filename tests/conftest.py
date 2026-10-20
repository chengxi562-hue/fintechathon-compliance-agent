"""Suite-wide isolation from any Mock Bank a developer happens to be running.

Why this exists (2026-10-20): README step 2 tells the reader to start Mock Bank on
127.0.0.1:8000, and step 4 tells them to run pytest. Doing both in one sitting used
to fail two tests, because the agent then talked to the *real* server process while
the assertions inspected the *local* seed memory:

    FAILED tests/test_subscription_w1.py::test_confirm_then_write
    FAILED tests/test_transfer_r7.py::test_latest_subscription_confirmation_never_posts_older_transfer

Those tests are about the in-process confirmation gate, so they must never reach a
network listener. We point MOCK_BANK_URL at a port nothing listens on, which also
exercises the documented offline fallback ("离线会回退到内存产品目录").
"""

from __future__ import annotations

import socket

import pytest

_UNUSED_PORT = 9  # discard; conventionally nothing listens here


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True, scope="session")
def _isolate_from_developer_mock_bank():
    """Pin MOCK_BANK_URL to a closed loopback port for the whole session."""
    import os

    previous = os.environ.get("MOCK_BANK_URL")
    os.environ["MOCK_BANK_URL"] = f"http://127.0.0.1:{_free_port()}"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("MOCK_BANK_URL", None)
        else:
            os.environ["MOCK_BANK_URL"] = previous
