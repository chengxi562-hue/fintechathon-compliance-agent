"""Placeholder tests for Mock Bank FastAPI app."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from mock_bank.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_wealth_products():
    r = client.get("/v1/wealth/products")
    assert r.status_code == 200
    ids = {p["product_id"] for p in r.json()}
    assert "WB_CASH_001" in ids


def test_get_customer_persona():
    r = client.get("/v1/customers/cust_yw_001")
    assert r.status_code == 200
    assert r.json()["risk_score"] == 2
