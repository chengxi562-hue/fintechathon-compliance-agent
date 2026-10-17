"""LangGraph-ready agent skeleton.

W0: plain Python state machine mirroring nodes we will map to LangGraph later:
  User → Intent → Plan → ComplianceGate(4) → Tools → Explain+Audit

Swap `run_agent` internals for a compiled StateGraph without changing call sites.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import httpx

from agent.gates import ComplianceVerdict, GateResult, load_rules, run_four_gates
from audit.logger import AuditLogger
from mock_bank import data as bank_seed


@dataclass
class AgentState:
    request_id: str
    utterance: str
    customer_id: str = "cust_yw_001"
    intent: str = ""
    plan: list[str] = field(default_factory=list)
    product_id: Optional[str] = None
    verdict: Optional[ComplianceVerdict] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    response: str = ""
    decision: str = ""  # allow | block


def _customer(customer_id: str) -> dict[str, Any]:
    cust = bank_seed.CUSTOMERS.get(customer_id)
    if not cust:
        raise KeyError(f"unknown customer {customer_id}")
    return cust


def _plan_for_intent(intent: str) -> list[str]:
    if intent in {"wealth_inquire", "wealth_purchase"}:
        return [
            "classify_intent",
            "match_product_from_catalog",
            "run_four_compliance_gates",
            "fetch_product_or_refuse",
            "explain_and_audit",
        ]
    if intent == "transfer":
        return [
            "classify_intent",
            "run_four_compliance_gates",
            "check_transfer_limits",
            "execute_or_confirm",
            "explain_and_audit",
        ]
    return ["classify_intent", "run_four_compliance_gates", "respond", "audit"]


def _fetch_product(mock_bank_url: str, product_id: str) -> dict[str, Any] | None:
    try:
        r = httpx.get(f"{mock_bank_url.rstrip('/')}/v1/wealth/products/{product_id}", timeout=3.0)
        if r.status_code == 200:
            return r.json()
    except httpx.HTTPError:
        pass
    # Offline fallback to seed
    return bank_seed.PRODUCTS.get(product_id)



_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}


def _cn_num(seg: str) -> float | None:
    """Parse a Chinese-numeral segment like 五千 / 三万五 / 十二. Returns None if no CN numerals."""
    if not seg or not any(c in _CN_DIGITS or c in _CN_UNITS for c in seg):
        return None
    total, cur = 0, 0
    for ch in seg:
        if ch in _CN_DIGITS:
            cur = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            total += (cur or 1) * unit
            cur = 0
        elif ch == "万":
            total = (total + cur) * 10000
            cur = 0
        elif ch == "亿":
            total = (total + cur) * 100000000
            cur = 0
        else:
            return None
    return float(total + cur)


def _parse_amounts(utterance: str) -> list[float]:
    """Extract all transfer amounts (CNY) with unit normalization.

    Handles 万/万元/亿/千 multipliers, thousands separators (25,000),
    Chinese numerals (五千 / 三万五千), and negative numbers (kept signed so the
    caller can reject <= 0 as TRANSFER_AMOUNT_INVALID).
    """
    u = re.sub(r"(?<=\d)[,，](?=\d{3})", "", utterance)  # strip thousands separators
    amounts: list[float] = []

    def _flush(m: re.Match[str]) -> str:
        num = float(m.group(1))
        unit = m.group(2) or ""
        mult = {"亿": 1e8, "万元": 1e4, "万": 1e4, "千": 1e3}.get(unit, 1.0)
        amounts.append(num * mult)
        return " "

    # Arabic numerals with optional unit; negative allowed (validated later)
    u = re.sub(r"(-?\d+(?:\.\d+)?)\s*(亿元|亿|万元|万|千元|千|元|块|块钱)?", _flush, u)
    # Chinese numerals with optional 万/亿 big units
    cn_pat = r"([零一二两三四五六七八九十百千万亿]+)"
    for m in re.finditer(cn_pat, u):
        v = _cn_num(m.group(1))
        if v is not None:
            amounts.append(v)
    return amounts


def _parse_transfer_amount(utterance: str) -> float | None:
    """Total amount across all mentions (multi-transfer requests are summed)."""
    amounts = _parse_amounts(utterance)
    if not amounts:
        return None
    return sum(amounts)


def _transfer_decision(utterance: str, rules: dict) -> tuple[str, str, list[str]]:
    """Return decision, response, reason_codes for transfer intent."""
    cfg = rules.get("transfer", {})
    soft = float(cfg.get("daily_soft_limit_cny", 20000))
    confirm_above = float(cfg.get("require_confirm_above_cny", 5000))
    whitelist_above = float(cfg.get("whitelist_only_above_cny", 50000))
    amount = _parse_transfer_amount(utterance)
    reasons: list[str] = []
    n_amounts = len(_parse_amounts(utterance))
    count_note = f"（共 {n_amounts} 笔，合计 {amount:.0f} 元）" if n_amounts > 1 else ""
    if amount is None:
        return "block", "请说明转账金额（例如：把 100 元转到自己活期备用金）。", ["TRANSFER_AMOUNT_MISSING"]
    if amount <= 0:
        return "block", "转账金额必须为正数（元），请重新说明。", ["TRANSFER_AMOUNT_INVALID"]
    if amount > whitelist_above or re.search(r"陌生人|未知|随便一个人", utterance):
        reasons.append("TRANSFER_WHITELIST_REQUIRED")
        return "block", f"金额 {amount:.0f} 元超过白名单阈值或收款方不在白名单，已拦截。", reasons
    if amount > soft:
        reasons.append("TRANSFER_SOFT_LIMIT")
        return "block", f"金额 {amount:.0f} 元超过日软限额 {soft:.0f} 元，已拦截。", reasons
    if amount > confirm_above:
        reasons.append("TRANSFER_CONFIRM_REQUIRED")
        return "block", f"金额 {amount:.0f} 元{count_note}需二次确认后才能执行（阈值 {confirm_above:.0f} 元）。", reasons
    # Internal backup heuristic
    to_backup = bool(re.search(r"备用金|自己", utterance))
    reasons.append("TRANSFER_OK")
    dest = "acc_yw_backup" if to_backup else "external_pending"
    return (
        "allow",
        f"权限内转账 {amount:.0f} 元至{'活期备用金' if to_backup else '指定账户'}可通过；演示路径已记审计（目标账户 {dest}）。",
        reasons,
    )


def run_agent(
    utterance: str,
    customer_id: str = "cust_yw_001",
    mock_bank_url: str = "http://127.0.0.1:8000",
    audit: AuditLogger | None = None,
) -> AgentState:
    """Execute one turn. Demo path: 问理财 → 拦 / 放行."""
    audit = audit or AuditLogger()
    rules = load_rules()
    state = AgentState(request_id=f"req_{uuid.uuid4().hex[:10]}", utterance=utterance, customer_id=customer_id)
    cust = _customer(customer_id)

    verdict = run_four_gates(utterance, cust, rules)
    state.verdict = verdict
    state.intent = verdict.intent
    state.product_id = verdict.product_id
    state.plan = _plan_for_intent(verdict.intent)
    state.decision = "allow" if verdict.allowed else "block"

    if verdict.intent == "transfer":
        # Transfer uses extra amount/limit gate on top of four gates
        if not verdict.allowed:
            state.response = verdict.response_hint
            state.decision = "block"
        else:
            decision, response, xreasons = _transfer_decision(utterance, rules)
            state.decision = decision
            state.response = response
            verdict.reason_codes = list(verdict.reason_codes) + xreasons
            # Keep ComplianceVerdict.allowed in sync with transfer limit gate
            verdict.allowed = decision == "allow"
            if decision == "block":
                verdict.response_hint = response
            state.tool_calls.append(
                {
                    "tool": "transfer_check",
                    "ok": decision == "allow",
                    "amount": _parse_transfer_amount(utterance),
                    "reasons": xreasons,
                }
            )
    elif verdict.allowed and verdict.product_id and verdict.intent.startswith("wealth"):
        prod = _fetch_product(mock_bank_url, verdict.product_id)
        state.tool_calls.append(
            {"tool": "get_product", "product_id": verdict.product_id, "ok": prod is not None, "data": prod}
        )
        if prod:
            state.response = (
                f"{verdict.response_hint}\n"
                f"产品：{prod['name']}（{prod['product_id']}）｜"
                f"流动性：{prod['liquidity']}｜提示：{prod['expected_yield_hint']}"
            )
        else:
            state.response = verdict.response_hint
    else:
        state.response = verdict.response_hint

    gate_payload = [
        {"name": g.name, "passed": g.passed, "reason_codes": g.reason_codes, "details": g.details}
        for g in (verdict.gates if verdict else [])
    ]
    audit.write(
        {
            "request_id": state.request_id,
            "customer_id": customer_id,
            "utterance": utterance,
            "intent": state.intent,
            "plan": state.plan,
            "gate_results": gate_payload,
            "decision": state.decision,
            "reason_codes": verdict.reason_codes,
            "tool_calls": state.tool_calls,
            "response": state.response,
            "product_id": state.product_id,
        }
    )
    return state


def verdict_to_dict(v: ComplianceVerdict) -> dict[str, Any]:
    return {
        "allowed": v.allowed,
        "intent": v.intent,
        "product_id": v.product_id,
        "reason_codes": v.reason_codes,
        "response_hint": v.response_hint,
        "gates": [asdict(g) if isinstance(g, GateResult) else g for g in v.gates],
    }
