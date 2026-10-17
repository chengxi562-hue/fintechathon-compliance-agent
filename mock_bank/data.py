"""In-memory seed data for the mock bank."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

CUSTOMERS: dict[str, dict[str, Any]] = {
    "cust_yw_001": {
        "customer_id": "cust_yw_001",
        "name": "林晓晴",
        "risk_score": 2,  # R2 稳健
        "risk_label": "R2_稳健型",
        "kyc_ok": True,
        "city": "深圳",
        "investable_assets_cny": 180_000,
    }
}

ACCOUNTS: dict[str, dict[str, Any]] = {
    "acc_yw_001": {
        "account_id": "acc_yw_001",
        "customer_id": "cust_yw_001",
        "type": "demand",
        "currency": "CNY",
        "balance": 52_380.55,
        "available": 52_380.55,
    },
    "acc_yw_backup": {
        "account_id": "acc_yw_backup",
        "customer_id": "cust_yw_001",
        "type": "demand_backup",
        "currency": "CNY",
        "balance": 3_200.00,
        "available": 3_200.00,
        "label": "活期备用金",
    },
}

PRODUCTS: dict[str, dict[str, Any]] = {
    "WB_CASH_001": {
        "product_id": "WB_CASH_001",
        "name": "微众灵活宝A",
        "category": "money_market",
        "min_risk_score": 1,
        "expected_yield_hint": "2.1%~2.4%（近7日年化，非承诺）",
        "min_purchase": 1.0,
        "liquidity": "T+0",
    },
    "WB_BOND_002": {
        "product_id": "WB_BOND_002",
        "name": "稳债精选90天",
        "category": "short_bond",
        "min_risk_score": 2,
        "expected_yield_hint": "2.6%~3.2%（业绩比较基准，非承诺）",
        "min_purchase": 1000.0,
        "liquidity": "封闭90天",
    },
    "WB_EQ_MIX_003": {
        "product_id": "WB_EQ_MIX_003",
        "name": "进取混合FOF",
        "category": "equity_mix",
        "min_risk_score": 4,
        "expected_yield_hint": "波动较大，历史区间年化仅供参考",
        "min_purchase": 1000.0,
        "liquidity": "T+1",
    },
}

TRANSFERS: list[dict[str, Any]] = []


def snapshot() -> dict[str, Any]:
    return {
        "customers": deepcopy(CUSTOMERS),
        "accounts": deepcopy(ACCOUNTS),
        "products": deepcopy(PRODUCTS),
        "transfers": deepcopy(TRANSFERS),
    }
