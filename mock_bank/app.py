"""FastAPI Mock Bank: account / transfer / wealth."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from mock_bank import data as store

app = FastAPI(
    title="FinTechathon Mock Bank",
    version="0.1.0",
    description="Account / transfer / wealth stubs for 合规官 demo.",
)

# ---------------------------------------------------------------------------
# 第二道闸（bank-side 兜底）：即使 Agent 合规门被绕过，银行侧仍独立执行。
# 阈值与 configs/compliance_rules.yaml 的 transfer.* / suitability 一致。
# ---------------------------------------------------------------------------
DAILY_SOFT_LIMIT_CNY = 20_000.0
WHITELIST_ONLY_ABOVE_CNY = 50_000.0


def _is_whitelisted_recipient(customer_id: str, to_account_id: str) -> bool:
    """白名单 = 客户本人名下账户（行内同名划转）。"""
    acc = store.ACCOUNTS.get(to_account_id)
    return bool(acc and acc["customer_id"] == customer_id)


def _daily_posted_total(customer_id: str) -> float:
    """当日已出账累计（demo 无日期维度，按内存全部 posted 计）。"""
    return sum(
        t["amount_cny"]
        for t in store.TRANSFERS
        if t.get("customer_id") == customer_id and t.get("status") == "posted"
    )



class TransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount_cny: float = Field(gt=0)
    memo: Optional[str] = None
    customer_id: str = "cust_yw_001"
    confirmed: bool = False


class WealthPurchaseRequest(BaseModel):
    customer_id: str = "cust_yw_001"
    account_id: str = "acc_yw_001"
    product_id: str
    amount_cny: float = Field(gt=0)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/customers/{customer_id}")
def get_customer(customer_id: str) -> dict[str, Any]:
    cust = store.CUSTOMERS.get(customer_id)
    if not cust:
        raise HTTPException(404, "customer not found")
    return cust


@app.get("/v1/accounts/{account_id}")
def get_account(account_id: str) -> dict[str, Any]:
    acc = store.ACCOUNTS.get(account_id)
    if not acc:
        raise HTTPException(404, "account not found")
    return acc


@app.get("/v1/customers/{customer_id}/accounts")
def list_accounts(customer_id: str) -> list[dict[str, Any]]:
    return [a for a in store.ACCOUNTS.values() if a["customer_id"] == customer_id]


@app.get("/v1/wealth/products")
def list_products() -> list[dict[str, Any]]:
    return list(store.PRODUCTS.values())


@app.get("/v1/wealth/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    prod = store.PRODUCTS.get(product_id)
    if not prod:
        raise HTTPException(404, "product not found")
    return prod


@app.post("/v1/transfers")
def create_transfer(body: TransferRequest) -> dict[str, Any]:
    src = store.ACCOUNTS.get(body.from_account_id)
    if not src or src["customer_id"] != body.customer_id:
        raise HTTPException(404, "source account not found")
    if body.amount_cny > src["available"]:
        raise HTTPException(400, "insufficient funds")
    # 第二道闸：白名单硬拦（大额转非本人账户，Agent 绕过也生效）
    if body.amount_cny > WHITELIST_ONLY_ABOVE_CNY and not _is_whitelisted_recipient(
        body.customer_id, body.to_account_id
    ):
        raise HTTPException(
            403,
            f"TRANSFER_BANK_WHITELIST_REQUIRED: amount > {WHITELIST_ONLY_ABOVE_CNY} to non-whitelisted recipient",
        )
    # 第二道闸：日累计软限硬拦（本人名下划转不占用限额）
    if not _is_whitelisted_recipient(
        body.customer_id, body.to_account_id
    ) and _daily_posted_total(body.customer_id) + body.amount_cny > DAILY_SOFT_LIMIT_CNY:
        raise HTTPException(
            403,
            f"TRANSFER_BANK_DAILY_LIMIT_EXCEEDED: daily soft limit {DAILY_SOFT_LIMIT_CNY}",
        )
    # Soft policy hint for agent layer; bank still executes if confirmed
    needs_confirm = body.amount_cny >= 5000 and not body.confirmed
    if needs_confirm:
        return {
            "status": "pending_confirm",
            "reason": "amount_requires_confirm",
            "amount_cny": body.amount_cny,
        }
    src["balance"] -= body.amount_cny
    src["available"] -= body.amount_cny
    tx = {
        "transfer_id": f"tx_{uuid.uuid4().hex[:12]}",
        "status": "posted",
        **body.model_dump(),
    }
    store.TRANSFERS.append(tx)
    return tx


@app.post("/v1/wealth/purchase")
def purchase_wealth(body: WealthPurchaseRequest) -> dict[str, Any]:
    """Naive purchase: deduct demand account. Suitability is enforced by Agent gates."""
    prod = store.PRODUCTS.get(body.product_id)
    if not prod:
        raise HTTPException(404, "product not found")
    acc = store.ACCOUNTS.get(body.account_id)
    if not acc or acc["customer_id"] != body.customer_id:
        raise HTTPException(404, "account not found")
    if body.amount_cny < prod["min_purchase"]:
        raise HTTPException(400, f"min purchase {prod['min_purchase']}")
    if body.amount_cny > acc["available"]:
        raise HTTPException(400, "insufficient funds")
    # 第二道闸：适当性兜底（客户风险等级 < 产品要求 → 拒）
    cust = store.CUSTOMERS.get(body.customer_id)
    if cust and cust["risk_score"] < prod["min_risk_score"]:
        raise HTTPException(
            403,
            f"SUITABILITY_MISMATCH: customer risk R{cust['risk_score']} < product min R{prod['min_risk_score']}",
        )
    acc["balance"] -= body.amount_cny
    acc["available"] -= body.amount_cny
    return {
        "status": "posted",
        "order_id": f"ord_{uuid.uuid4().hex[:12]}",
        "product_id": body.product_id,
        "amount_cny": body.amount_cny,
        "customer_id": body.customer_id,
    }
