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
        "subscriptions": deepcopy(SUBSCRIPTIONS),
        "bills": deepcopy(BILLS),
    }


# --- W1: subscription / bills seed (≥3 subs, ≥5 bills) ---
SUBSCRIPTIONS: dict[str, dict[str, Any]] = {
    "sub_netflix_001": {
        "subscription_id": "sub_netflix_001",
        "customer_id": "cust_yw_001",
        "merchant": "Netflix",
        "category": "streaming",
        "amount_cny": 68.0,
        "currency": "CNY",
        "cadence": "monthly",
        "status": "active",  # active | paused | cancelled
        "debit_enabled": True,
        "next_debit_date": "2026-11-05",
        "account_id": "acc_yw_001",
    },
    "sub_spotify_002": {
        "subscription_id": "sub_spotify_002",
        "customer_id": "cust_yw_001",
        "merchant": "Spotify",
        "category": "streaming",
        "amount_cny": 15.0,
        "currency": "CNY",
        "cadence": "monthly",
        "status": "active",
        "debit_enabled": True,
        "next_debit_date": "2026-11-12",
        "account_id": "acc_yw_001",
    },
    "sub_gym_003": {
        "subscription_id": "sub_gym_003",
        "customer_id": "cust_yw_001",
        "merchant": "乐刻健身",
        "category": "fitness",
        "amount_cny": 199.0,
        "currency": "CNY",
        "cadence": "monthly",
        "status": "active",
        "debit_enabled": True,
        "next_debit_date": "2026-11-01",
        "account_id": "acc_yw_001",
    },
    "sub_icloud_004": {
        "subscription_id": "sub_icloud_004",
        "customer_id": "cust_yw_001",
        "merchant": "iCloud+",
        "category": "cloud",
        "amount_cny": 21.0,
        "currency": "CNY",
        "cadence": "monthly",
        "status": "paused",
        "debit_enabled": False,
        "next_debit_date": None,
        "account_id": "acc_yw_001",
    },
}

BILLS: list[dict[str, Any]] = [
    {
        "bill_id": "bill_001",
        "customer_id": "cust_yw_001",
        "subscription_id": "sub_netflix_001",
        "merchant": "Netflix",
        "amount_cny": 68.0,
        "posted_at": "2026-10-05T10:00:00+08:00",
        "status": "posted",
        "note": "正常月费",
    },
    {
        "bill_id": "bill_002",
        "customer_id": "cust_yw_001",
        "subscription_id": "sub_spotify_002",
        "merchant": "Spotify",
        "amount_cny": 15.0,
        "posted_at": "2026-10-12T09:30:00+08:00",
        "status": "posted",
        "note": "正常月费",
    },
    {
        "bill_id": "bill_003",
        "customer_id": "cust_yw_001",
        "subscription_id": "sub_gym_003",
        "merchant": "乐刻健身",
        "amount_cny": 199.0,
        "posted_at": "2026-10-01T08:00:00+08:00",
        "status": "posted",
        "note": "正常月费",
    },
    {
        "bill_id": "bill_004",
        "customer_id": "cust_yw_001",
        "subscription_id": "sub_netflix_001",
        "merchant": "Netflix",
        "amount_cny": 98.0,
        "posted_at": "2026-09-05T10:00:00+08:00",
        "status": "posted",
        "note": "异常：较上月上涨 30 元（疑似档位变更）",
        "anomaly": True,
    },
    {
        "bill_id": "bill_005",
        "customer_id": "cust_yw_001",
        "subscription_id": "sub_icloud_004",
        "merchant": "iCloud+",
        "amount_cny": 21.0,
        "posted_at": "2026-09-20T11:00:00+08:00",
        "status": "posted",
        "note": "暂停前最后一笔",
    },
    {
        "bill_id": "bill_006",
        "customer_id": "cust_yw_001",
        "subscription_id": None,
        "merchant": "美团月付",
        "amount_cny": 0.0,
        "posted_at": "2026-10-08T19:20:00+08:00",
        "status": "insight",
        "note": "账单洞察：餐饮周支出偏高，可考虑预算提醒",
        "anomaly": False,
    },
]


def reset_subscriptions_seed() -> None:
    """Test helper: restore subscription seed to initial amounts/status."""
    SUBSCRIPTIONS["sub_netflix_001"].update(
        {"amount_cny": 68.0, "status": "active", "debit_enabled": True, "next_debit_date": "2026-11-05"}
    )
    SUBSCRIPTIONS["sub_spotify_002"].update(
        {"amount_cny": 15.0, "status": "active", "debit_enabled": True, "next_debit_date": "2026-11-12"}
    )
    SUBSCRIPTIONS["sub_gym_003"].update(
        {"amount_cny": 199.0, "status": "active", "debit_enabled": True, "next_debit_date": "2026-11-01"}
    )
    SUBSCRIPTIONS["sub_icloud_004"].update(
        {"amount_cny": 21.0, "status": "paused", "debit_enabled": False, "next_debit_date": None}
    )
