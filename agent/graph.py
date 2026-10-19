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
from agent import pending_action as pa
from audit.logger import AuditLogger
from mock_bank import data as bank_seed


@dataclass
class AgentState:
    request_id: str
    utterance: str
    customer_id: str = "cust_yw_001"
    session_id: str = ""
    intent: str = ""
    plan: list[str] = field(default_factory=list)
    product_id: Optional[str] = None
    verdict: Optional[ComplianceVerdict] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    response: str = ""
    decision: str = ""  # allow | block
    pending_id: Optional[str] = None


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
    if intent == "subscription_manage":
        return [
            "classify_intent",
            "run_four_compliance_gates",
            "list_or_propose_subscription_change",
            "pending_confirm_gate",
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



def _list_subscriptions(customer_id: str) -> list[dict[str, Any]]:
    return [s for s in bank_seed.SUBSCRIPTIONS.values() if s["customer_id"] == customer_id]


def _list_bills(customer_id: str) -> list[dict[str, Any]]:
    return [b for b in bank_seed.BILLS if b["customer_id"] == customer_id]


def _find_sub_by_merchant(customer_id: str, utterance: str) -> dict[str, Any] | None:
    subs = _list_subscriptions(customer_id)
    u = utterance.lower()
    for s in subs:
        name = str(s.get("merchant", "")).lower()
        if name and name in u:
            return s
    # Chinese aliases
    aliases = {"网飞": "Netflix", "奈飞": "Netflix", "健身": "乐刻健身", "苹果云": "iCloud+"}
    for k, merchant in aliases.items():
        if k in utterance:
            for s in subs:
                if s.get("merchant") == merchant:
                    return s
    return None


def _parse_sub_new_amount(utterance: str) -> float | None:
    m = re.search(
        r"(?:改成|改为|调整为|改到|设为|变成)\s*(\d+(?:\.\d+)?)\s*(元|块)?",
        utterance,
    )
    if m:
        return float(m.group(1))
    amounts = _parse_amounts(utterance)
    return amounts[0] if amounts else None


def _subscription_turn(
    utterance: str,
    customer_id: str,
    session_id: str,
    mock_bank_url: str,
) -> tuple[str, str, list[str], list[dict[str, Any]], Optional[str]]:
    """Handle subscription_manage: list / insight / pending write / confirm.

    Returns decision, response, reason_codes, tool_calls, pending_id.
    """
    tools: list[dict[str, Any]] = []
    u = utterance.strip()

    # Confirm / cancel pending
    if re.fullmatch(r"确认|确认执行|好的确认|确认变更", u) or u in {"确认", "确认执行"}:
        # Use latest pending for this session
        latest = None
        for p in pa._PENDING.values():  # demo: session-scoped lookup
            if p.session_id == session_id and p.status == "pending":
                latest = p
                break
        # also accept expired refresh via get
        if latest is None:
            for p in list(pa._PENDING.values()):
                if p.session_id == session_id:
                    latest = pa.get_pending(p.pending_id)
                    break
        if latest is None:
            return "block", "当前没有待确认的订阅变更，请先说明要改哪一项。", ["PENDING_NOT_FOUND"], tools, None
        code, pend = pa.confirm_pending(latest.pending_id, session_id=session_id)
        if code != "PENDING_CONFIRMED" or pend is None:
            return "block", f"确认失败：{code}。订阅未改动。", [code], tools, latest.pending_id
        # Apply bank write
        payload = {
            "customer_id": customer_id,
            "action": pend.action,
            "confirmed": True,
            "pending_id": pend.pending_id,
        }
        if pend.action == "change_amount":
            payload["new_amount_cny"] = pend.payload.get("new_amount_cny")
        try:
            r = httpx.post(
                f"{mock_bank_url.rstrip('/')}/v1/subscriptions/{pend.target_id}/apply",
                json=payload,
                timeout=3.0,
            )
            ok = r.status_code == 200
            data = r.json() if ok else {"detail": r.text}
        except httpx.HTTPError:
            # Offline: apply directly to seed (same rules)
            sub = bank_seed.SUBSCRIPTIONS.get(pend.target_id)
            if not sub:
                return "block", "订阅不存在，未改动。", ["SUB_NOT_FOUND"], tools, pend.pending_id
            before = {k: sub[k] for k in ("amount_cny", "status", "debit_enabled", "next_debit_date")}
            if pend.action == "change_amount":
                sub["amount_cny"] = float(pend.payload["new_amount_cny"])
            elif pend.action == "pause_debit":
                sub["debit_enabled"] = False
                sub["status"] = "paused"
                sub["next_debit_date"] = None
            elif pend.action == "resume_debit":
                sub["debit_enabled"] = True
                sub["status"] = "active"
                sub["next_debit_date"] = sub.get("next_debit_date") or "2026-11-15"
            elif pend.action == "cancel_sub":
                sub["debit_enabled"] = False
                sub["status"] = "cancelled"
                sub["next_debit_date"] = None
            after = {k: sub[k] for k in ("amount_cny", "status", "debit_enabled", "next_debit_date")}
            ok, data = True, {"status": "posted", "before": before, "after": after, "pending_id": pend.pending_id}
        tools.append({"tool": "subscription_apply", "ok": ok, "data": data, "pending_id": pend.pending_id})
        if not ok:
            return "block", f"银行侧拒绝落账：{data}", ["SUBSCRIPTION_BANK_REJECT"], tools, pend.pending_id
        pend.after = data.get("after")
        return (
            "allow",
            f"已确认并执行订阅变更（{pend.action}），审计已记 pending_id={pend.pending_id}。",
            ["PENDING_CONFIRMED", "SUBSCRIPTION_APPLIED"],
            tools,
            pend.pending_id,
        )

    if re.fullmatch(r"取消|取消变更|不改了", u):
        latest = None
        for p in pa._PENDING.values():
            if p.session_id == session_id and p.status == "pending":
                latest = p
                break
        if latest is None:
            return "block", "没有可取消的待确认变更。", ["PENDING_NOT_FOUND"], tools, None
        code, pend = pa.cancel_pending(latest.pending_id, session_id=session_id)
        return "allow", f"已取消待确认变更（{code}）。", [code], tools, latest.pending_id

    # Write intents → PendingAction only
    sub = _find_sub_by_merchant(customer_id, utterance)
    if re.search(r"改成|改为|调整|改额|改到|设为", utterance) and (
        re.search(r"订阅|代扣|月费|Netflix|网飞|Spotify|乐刻|iCloud", utterance, re.I)
        or sub
    ):
        if sub is None:
            return "block", "请说明要改哪一个订阅商家（如 Netflix / Spotify / 乐刻）。", ["SUB_MERCHANT_MISSING"], tools, None
        new_amt = _parse_sub_new_amount(utterance)
        if new_amt is None:
            return "block", "请说明新的月费金额（例如：把 Netflix 月费改成 30）。", ["SUB_AMOUNT_MISSING"], tools, None
        before = {k: sub[k] for k in ("amount_cny", "status", "debit_enabled", "next_debit_date")}
        pend = pa.create_pending(
            session_id=session_id,
            customer_id=customer_id,
            action="change_amount",
            target_id=sub["subscription_id"],
            payload={"new_amount_cny": new_amt, "merchant": sub["merchant"]},
            before=before,
        )
        tools.append({"tool": "create_pending", "ok": True, "pending_id": pend.pending_id, "before": before})
        # Prove seed unchanged
        still = bank_seed.SUBSCRIPTIONS[sub["subscription_id"]]["amount_cny"]
        return (
            "block",
            f"已生成待确认变更：{sub['merchant']} 月费 {before['amount_cny']:.0f}→{new_amt:.0f} 元。"
            f"请回复「确认」执行，或「取消」。当前落账金额仍为 {still:.0f} 元（pending_id={pend.pending_id}）。",
            ["PENDING_CONFIRM_REQUIRED"],
            tools,
            pend.pending_id,
        )

    if re.search(r"暂停|停止代扣", utterance) and (sub or re.search(r"订阅|代扣|Netflix|Spotify|乐刻|iCloud", utterance, re.I)):
        if sub is None:
            return "block", "请说明要暂停哪一个订阅商家。", ["SUB_MERCHANT_MISSING"], tools, None
        before = {k: sub[k] for k in ("amount_cny", "status", "debit_enabled", "next_debit_date")}
        pend = pa.create_pending(
            session_id=session_id,
            customer_id=customer_id,
            action="pause_debit",
            target_id=sub["subscription_id"],
            payload={"merchant": sub["merchant"]},
            before=before,
        )
        tools.append({"tool": "create_pending", "ok": True, "pending_id": pend.pending_id})
        return (
            "block",
            f"已生成待确认：暂停 {sub['merchant']} 代扣。请回复「确认」或「取消」。",
            ["PENDING_CONFIRM_REQUIRED"],
            tools,
            pend.pending_id,
        )

    if re.search(r"取消订阅|退订", utterance):
        if sub is None:
            return "block", "请说明要取消哪一个订阅商家。", ["SUB_MERCHANT_MISSING"], tools, None
        before = {k: sub[k] for k in ("amount_cny", "status", "debit_enabled", "next_debit_date")}
        pend = pa.create_pending(
            session_id=session_id,
            customer_id=customer_id,
            action="cancel_sub",
            target_id=sub["subscription_id"],
            payload={"merchant": sub["merchant"]},
            before=before,
        )
        tools.append({"tool": "create_pending", "ok": True, "pending_id": pend.pending_id})
        return (
            "block",
            f"已生成待确认：取消订阅 {sub['merchant']}。请回复「确认」或「取消」。",
            ["PENDING_CONFIRM_REQUIRED"],
            tools,
            pend.pending_id,
        )

    # Read-only: list / bill insight
    subs = _list_subscriptions(customer_id)
    bills = _list_bills(customer_id)
    tools.append({"tool": "list_subscriptions", "ok": True, "count": len(subs)})
    tools.append({"tool": "list_bills", "ok": True, "count": len(bills)})
    anomalies = [b for b in bills if b.get("anomaly")]
    lines = [f"- {s['merchant']}：{s['amount_cny']:.0f} 元/月 · {s['status']}" for s in subs]
    note = ""
    if anomalies:
        a = anomalies[0]
        note = f"\n账单洞察：发现异常扣款 {a['merchant']} {a['amount_cny']:.0f} 元（{a.get('note','')}）。可提议改额/暂停，需二次确认。"
    return (
        "allow",
        "当前订阅一览：\n" + "\n".join(lines) + note,
        ["SUBSCRIPTION_LIST_OK"] + (["BILL_ANOMALY_HINT"] if anomalies else []),
        tools,
        None,
    )


def run_agent(
    utterance: str,
    customer_id: str = "cust_yw_001",
    mock_bank_url: str = "http://127.0.0.1:8000",
    audit: AuditLogger | None = None,
    session_id: str | None = None,
) -> AgentState:
    """Execute one turn. Demo path: 问理财 → 拦 / 放行；W1 含订阅确认门."""
    audit = audit or AuditLogger()
    rules = load_rules()
    sid = session_id or f"sess_{uuid.uuid4().hex[:10]}"
    state = AgentState(
        request_id=f"req_{uuid.uuid4().hex[:10]}",
        utterance=utterance,
        customer_id=customer_id,
        session_id=sid,
    )
    cust = _customer(customer_id)

    # Confirm/cancel short utterances reuse subscription session even if intent gate says chitchat
    force_sub = bool(re.fullmatch(r"确认|确认执行|好的确认|确认变更|取消|取消变更|不改了", utterance.strip()))
    if force_sub:
        # Prefer subscription path when a pending exists for this session
        has_pending = any(
            p.session_id == sid and p.status in {"pending", "expired"} for p in pa._PENDING.values()
        )
        if has_pending or force_sub:
            # Build a synthetic allowed verdict for subscription_manage
            from agent.gates import ComplianceVerdict, GateResult

            verdict = ComplianceVerdict(
                allowed=True,
                intent="subscription_manage",
                product_id=None,
                reason_codes=["SESSION_CONFIRM_UTTERANCE"],
                response_hint="",
                gates=[],
            )
        else:
            verdict = run_four_gates(utterance, cust, rules)
    else:
        verdict = run_four_gates(utterance, cust, rules)
    state.verdict = verdict
    state.intent = verdict.intent
    state.product_id = verdict.product_id
    state.plan = _plan_for_intent(verdict.intent)
    state.decision = "allow" if verdict.allowed else "block"

    if verdict.intent == "subscription_manage":
        # Four gates (esp. inject) still win; do not overwrite a block
        if not verdict.allowed:
            state.response = verdict.response_hint
            state.decision = "block"
        else:
            decision, response, xreasons, tools, pend_id = _subscription_turn(
                utterance, customer_id, sid, mock_bank_url
            )
            state.decision = decision
            state.response = response
            state.pending_id = pend_id
            state.tool_calls.extend(tools)
            verdict.reason_codes = list(verdict.reason_codes) + xreasons
            verdict.allowed = decision == "allow"
            if decision == "block":
                verdict.response_hint = response
    elif verdict.intent == "transfer":
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
            "session_id": state.session_id,
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
            "pending_id": state.pending_id,
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
