"""Bank-side 第二道闸 tests: 软限 / 白名单 / 适当性兜底（绕过 Agent 直连 bank）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mock_bank import data as store
from mock_bank.app import app


@pytest.fixture(autouse=True)
def reset_store():
    snap = store.snapshot()
    yield
    store.CUSTOMERS.clear(); store.CUSTOMERS.update(snap["customers"])
    store.ACCOUNTS.clear(); store.ACCOUNTS.update(snap["accounts"])
    store.PRODUCTS.clear(); store.PRODUCTS.update(snap["products"])
    store.TRANSFERS.clear(); store.TRANSFERS.extend(snap["transfers"])


@pytest.fixture
def client():
    return TestClient(app)


def _transfer(client, amount, to="acc_yw_backup", confirmed=True):
    return client.post(
        "/v1/transfers",
        json={
            "from_account_id": "acc_yw_001",
            "to_account_id": to,
            "amount_cny": amount,
            "customer_id": "cust_yw_001",
            "confirmed": confirmed,
        },
    )


def test_large_transfer_to_non_whitelisted_blocked(client):
    store.ACCOUNTS["acc_yw_001"]["balance"] = 80_000
    store.ACCOUNTS["acc_yw_001"]["available"] = 80_000
    # 60000 > 50000，收款方非本人账户 → 403，即便 Agent 被绕过
    r = _transfer(client, 60_000, to="acc_stranger_999")
    assert r.status_code == 403
    assert "TRANSFER_BANK_WHITELIST_REQUIRED" in r.json()["detail"]


def test_large_transfer_to_own_account_allowed(client):
    store.ACCOUNTS["acc_yw_001"]["balance"] = 80_000
    store.ACCOUNTS["acc_yw_001"]["available"] = 80_000
    # 本人名下白名单，余额足够 → posted
    r = _transfer(client, 60_000, to="acc_yw_backup")
    assert r.status_code == 200
    assert r.json().get("status") == "posted"


def test_daily_soft_limit_accumulates(client):
    # 对外转账（非本人账户）累计计入日软限 20000
    store.ACCOUNTS["acc_yw_001"]["balance"] = 60_000
    store.ACCOUNTS["acc_yw_001"]["available"] = 60_000
    assert _transfer(client, 4_000, to="acc_landlord_1").status_code == 200
    assert _transfer(client, 4_000, to="acc_landlord_1").status_code == 200
    # 累计 8000，再转 13_000 → 21000 > 20000 → 403
    r = _transfer(client, 13_000, to="acc_landlord_1")
    assert r.status_code == 403
    assert "TRANSFER_BANK_DAILY_LIMIT_EXCEEDED" in r.json()["detail"]


def test_wealth_purchase_r2_buys_r4_blocked(client):
    r = client.post(
        "/v1/wealth/purchase",
        json={
            "customer_id": "cust_yw_001",
            "account_id": "acc_yw_001",
            "product_id": "WB_EQ_MIX_003",  # min_risk_score 4 > 客户 R2
            "amount_cny": 1_000,
        },
    )
    assert r.status_code == 403
    assert "SUITABILITY_MISMATCH" in r.json()["detail"]


def test_wealth_purchase_r2_buys_r2_allowed(client):
    r = client.post(
        "/v1/wealth/purchase",
        json={
            "customer_id": "cust_yw_001",
            "account_id": "acc_yw_001",
            "product_id": "WB_BOND_002",  # min_risk_score 2 == 客户 R2
            "amount_cny": 1_000,
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "posted"
