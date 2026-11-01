"""LangGraph-ready agent skeleton.

W0: plain Python state machine mirroring nodes we will map to LangGraph later:
  User → Intent → Plan → ComplianceGate(4) → Tools → Explain+Audit

Swap `run_agent` internals for a compiled StateGraph without changing call sites.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

import httpx

from agent.gates import ComplianceVerdict, GateResult, load_rules, run_four_gates, suggest_product
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
    if intent == "bill_insight":
        return [
            "classify_intent",
            "bill_insight",
            "suggest_product",
            "propose_transfer_optional",
            "audit",
        ]
    return ["classify_intent", "run_four_compliance_gates", "respond", "audit"]


# Local Mock Bank always lives on loopback. httpx honours the operator's system
# proxy by default (macOS HTTPProxy/SOCKSProxy), which turns a healthy
# 127.0.0.1:8000 Mock Bank into HTTP 502 and makes every confirmed write look
# like a bank rejection. Never let a proxy carry loopback traffic.
_HTTP_TIMEOUT = 3.0
_DEFAULT_BANK_URL = "http://127.0.0.1:8000"


def _local_http_get(url: str) -> "httpx.Response":
    return httpx.get(url, timeout=_HTTP_TIMEOUT, trust_env=False)


def _local_http_post(url: str, payload: dict[str, Any]) -> "httpx.Response":
    return httpx.post(url, json=payload, timeout=_HTTP_TIMEOUT, trust_env=False)


def _fetch_product(mock_bank_url: str, product_id: str) -> dict[str, Any] | None:
    try:
        r = _local_http_get(f"{mock_bank_url.rstrip('/')}/v1/wealth/products/{product_id}")
        if r.status_code == 200:
            return r.json()
    except httpx.HTTPError:
        pass
    # Offline fallback to seed
    return bank_seed.PRODUCTS.get(product_id)



_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}


def _cn_num(seg: str) -> float | None:
    """Parse a Chinese-numeral segment like 五千 / 三万五 / 十二 / 两个亿.

    Returns None if no CN numerals. 「个」is a measure word (两个亿) and is skipped.
    """
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
        elif ch == "个":
            continue
        else:
            return None
    return float(total + cur)


_AMOUNT_UNIT = r"个亿元|个亿|亿元|亿|个万元|万元|个万|万|千元|千|元|块钱|块"
_UNIT_MULT = {
    "个亿元": 1e8,
    "个亿": 1e8,
    "亿元": 1e8,
    "亿": 1e8,
    "个万元": 1e4,
    "万元": 1e4,
    "个万": 1e4,
    "万": 1e4,
    "千元": 1e3,
    "千": 1e3,
    "元": 1.0,
    "块钱": 1.0,
    "块": 1.0,
}


def _parse_amount_tokens(utterance: str) -> list[float]:
    """Extract amounts. Grouped digits are read first so "5,000" is 5000, not 5.

    Thousands separators and Chinese numerals are normalized to the same number
    a plain literal would be. Callers compare that number once; notation does
    not choose a different threshold.
    """
    tokens: list[float] = []

    def _flush(m: re.Match[str]) -> str:
        unit = m.group(2) or ""
        raw = m.group(1).replace(",", "").replace("，", "")
        tokens.append(float(raw) * _UNIT_MULT.get(unit, 1.0))
        return " "

    # Grouped digits first, so "5,000" is 5000 and not 5.
    grouped = rf"(-?\d{{1,3}}(?:[,，]\d{{3}})+(?:\.\d+)?)\s*({_AMOUNT_UNIT})?"
    u = re.sub(grouped, _flush, utterance)
    plain = rf"(-?\d+(?:\.\d+)?)\s*({_AMOUNT_UNIT})?"
    u = re.sub(plain, _flush, u)
    cn_pat = r"([零一二两三四五六七八九十百千万亿个]+)"
    for m in re.finditer(cn_pat, u):
        v = _cn_num(m.group(1))
        if v is not None:
            tokens.append(v)
    return tokens


def _parse_amounts(utterance: str) -> list[float]:
    """Extract all transfer amounts (CNY) with unit normalization.

    Handles 万/万元/亿/千 multipliers, thousands separators (25,000 / 5,000),
    Chinese numerals (五千 / 三万五千 / 两个亿), and negative numbers (kept
    signed so the caller can reject <= 0 as TRANSFER_AMOUNT_INVALID).
    """
    return _parse_amount_tokens(utterance)


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
    amounts = _parse_amounts(utterance)
    amount = sum(amounts) if amounts else None
    reasons: list[str] = []
    n_amounts = len(amounts)
    count_note = f"（共 {n_amounts} 笔，合计 {amount:.0f} 元）" if n_amounts > 1 and amount is not None else ""
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
    # 同一数值只走这一条：恰好等于阈值放行，严格大于才确认。
    # 与 Mock Bank 同一比较符。5,000 / 五千 / 5000.00 归一后与明文 5000 相同。
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


_CONFIRM = re.compile(r"确认|确认执行|好的确认|确认变更|确认转账")
_CANCEL = re.compile(r"取消|取消变更|不改了|取消转账|不转了|拒绝|不确认")


def _transfer_turn(
    utterance: str, customer_id: str, session_id: str, rules: dict,
) -> tuple[str, str, list[str], list[dict[str, Any]], Optional[str]]:
    """R7 demo: freeze the proposal, then confirm into the in-process Mock Bank."""
    from fastapi import HTTPException
    from mock_bank.app import TransferRequest, create_transfer

    tools = []
    u = utterance.strip()
    if _CONFIRM.fullmatch(u) or _CANCEL.fullmatch(u):
        pend = pa.latest_for_session(session_id)
        if pend is None or pend.action != "transfer":
            return "block", "当前没有待确认的转账。", ["PENDING_NOT_FOUND"], tools, None
        if pend.customer_id != customer_id:
            return "block", "确认单不属于当前客户。", ["PENDING_CUSTOMER_MISMATCH"], tools, pend.pending_id
        if _CANCEL.fullmatch(u):
            code, _ = pa.cancel_pending(pend.pending_id, session_id=session_id)
            ok = code == "PENDING_CANCELLED"
            return "allow" if ok else "block", f"转账取消结果：{code}；未执行转账。", [code], tools, pend.pending_id
        # Recheck the original request against current policy before consuming confirmation.
        original = pend.payload["utterance"]
        verdict = run_four_gates(original, _customer(customer_id), rules)
        _, _, reasons = _transfer_decision(original, rules)
        if not verdict.allowed or reasons != ["TRANSFER_CONFIRM_REQUIRED"]:
            return "block", "原转账请求未通过当前合规检查，未执行。", ["TRANSFER_RECHECK_FAILED"], tools, pend.pending_id
        dest = bank_seed.ACCOUNTS.get(pend.target_id)
        if not dest or dest["customer_id"] != customer_id:
            return "block", "收款账户已不属于本客户，未执行。", ["TRANSFER_RECIPIENT_MISMATCH"], tools, pend.pending_id
        code, _ = pa.confirm_pending(pend.pending_id, session_id=session_id)
        if code != "PENDING_CONFIRMED":
            return "block", f"转账确认失败：{code}；未执行。", [code], tools, pend.pending_id
        # Local simulation only; reuse the bank's independent checks, never an HTTP bank URL.
        try:
            data = create_transfer(TransferRequest(
                customer_id=customer_id,
                from_account_id=pend.payload["from_account_id"],
                to_account_id=pend.target_id,
                amount_cny=pend.payload["amount_cny"],
                confirmed=True,
                memo=f"demo pending_id={pend.pending_id}",
            ))
        except HTTPException as exc:
            tools.append({"tool": "transfer_apply", "ok": False, "detail": exc.detail, "pending_id": pend.pending_id})
            return "block", "Mock Bank 拒绝，未落账；请重新发起请求。", ["TRANSFER_BANK_REJECT"], tools, pend.pending_id
        pend.after = dict(bank_seed.ACCOUNTS[pend.payload["from_account_id"]])
        tools.append({"tool": "transfer_apply", "ok": True, "data": data, "pending_id": pend.pending_id})
        return "allow", "已确认并完成 Mock Bank 演示转账（仅内存模拟），审计已记录。", ["PENDING_CONFIRMED", "TRANSFER_APPLIED"], tools, pend.pending_id

    # M03：引用「刚才那笔 / 接着上一笔 / 同上」等前文指代，但会话里没有任何待确认单
    # → 不能凭上下文缺失直接执行，必须先澄清。
    if re.search(r"接着(刚才|上面|上|之前)(那笔|的|一笔)?|刚才那笔|上一笔|同上|还是那笔", utterance):
        if pa.latest_for_session(session_id) is None:
            return (
                "block",
                "我没有找到您说的上一笔转账（本会话没有待确认单）。请重新说明金额与收款账户，我不会凭指代直接执行。",
                ["TRANSFER_CONTEXT_MISSING"],
                tools,
                None,
            )

    decision, response, reasons = _transfer_decision(utterance, rules)
    tools.append({"tool": "transfer_check", "ok": decision == "allow", "amount": _parse_transfer_amount(utterance), "reasons": reasons})
    if reasons != ["TRANSFER_CONFIRM_REQUIRED"]:
        return decision, response, reasons, tools, None
    # Only the existing, explicitly named own-account demo recipient is resolvable.
    accounts = [a for a in bank_seed.ACCOUNTS.values() if a["customer_id"] == customer_id]
    src = next((a for a in accounts if a["type"] == "demand"), None)
    dest = next((a for a in accounts if a["type"] == "demand_backup"), None)
    if not src or not dest or not re.search(r"(?:到|给)(?:自己|本人)?的?(?:活期)?备用金", utterance):
        return "block", response + "尚未解析到收款账户，不能确认执行；演示仅支持本人活期备用金。", reasons + ["TRANSFER_RECIPIENT_MISSING"], tools, None
    if len(_parse_amounts(utterance)) != 1:
        return "block", "多笔转账不能合并为一个收款确认单，请逐笔说明。", reasons + ["TRANSFER_BATCH_UNSUPPORTED"], tools, None
    pend = pa.create_pending(
        session_id=session_id, customer_id=customer_id, action="transfer", target_id=dest["account_id"],
        payload={"utterance": utterance, "amount_cny": _parse_transfer_amount(utterance), "from_account_id": src["account_id"]},
        before=dict(src),
    )
    tools.append({"tool": "create_pending", "ok": True, "pending_id": pend.pending_id})
    return "block", response + "已生成本人活期备用金转账确认单，请回复「确认」或「取消」；当前未转账。", reasons, tools, pend.pending_id



def _list_subscriptions(customer_id: str) -> list[dict[str, Any]]:
    return [s for s in bank_seed.SUBSCRIPTIONS.values() if s["customer_id"] == customer_id]


def _list_bills(customer_id: str) -> list[dict[str, Any]]:
    return [b for b in bank_seed.BILLS if b["customer_id"] == customer_id]


_MERCHANT_ALIASES = {
    "网飞": "Netflix",
    "奈飞": "Netflix",
    "健身": "乐刻健身",
    "苹果云": "iCloud+",
}
_SUB_READ = re.compile(r"查看|查一下|看看|多少|列表|哪些|有哪些|什么订阅")


def _find_sub_by_merchant(customer_id: str, utterance: str) -> dict[str, Any] | None:
    subs = _list_subscriptions(customer_id)
    u = utterance.lower()
    for s in subs:
        name = str(s.get("merchant", "")).lower()
        if name and name in u:
            return s
    for alias, merchant in _MERCHANT_ALIASES.items():
        if alias.lower() in u:
            for s in subs:
                if s.get("merchant") == merchant:
                    return s
    return None


def _explicit_subscriptions(customer_id: str, utterance: str) -> list[dict[str, Any]]:
    """Merchants the user actually named. Amount is never a name."""
    subs = _list_subscriptions(customer_id)
    u = utterance.lower()
    hits: dict[str, dict[str, Any]] = {}

    def add(sub: dict[str, Any]) -> None:
        hits[str(sub["subscription_id"])] = sub

    for sub in subs:
        name = str(sub.get("merchant", ""))
        low = name.lower()
        bare = low.replace("+", "")
        if low and (low in u or (bare != low and bare in u)):
            add(sub)
        for alias, merchant in _MERCHANT_ALIASES.items():
            if merchant == name and alias.lower() in u:
                add(sub)
    for sub in subs:
        if sub["subscription_id"] in hits:
            continue
        low = str(sub.get("merchant", "")).lower().replace("+", "")
        if not low:
            continue
        min_len = 4 if re.search(r"[a-z0-9]", low) else 2
        for size in range(len(low), min_len - 1, -1):
            pref = low[:size]
            if pref not in u:
                continue
            owners = [
                s for s in subs
                if str(s.get("merchant", "")).lower().replace("+", "").startswith(pref)
            ]
            if len(owners) == 1:
                add(sub)
            break
    return list(hits.values())


def _is_merchant_supplement(utterance: str, matches: list[dict[str, Any]]) -> bool:
    """A follow-up that names one merchant, rather than a read or a guess."""
    if len(matches) != 1 or _SUB_READ.search(utterance):
        return False
    # A follow-up that already states the new amount is a new instruction.
    if re.search(_AMOUNT_VERB, utterance) and _parse_sub_new_amount(utterance) is not None:
        return False
    if re.search(r"是|改|商家|就|补充|指定|这个|订阅", utterance):
        return True
    sub = matches[0]
    compact = re.sub(r"[\s，。！？、,.：:]", "", utterance).lower()
    keys = {
        str(sub["merchant"]).lower(),
        str(sub["merchant"]).lower().replace("+", ""),
    }
    for alias, merchant in _MERCHANT_ALIASES.items():
        if merchant == sub["merchant"]:
            keys.add(alias.lower())
    return compact in keys


def _bind_merchant_supplement(
    utterance: str,
    customer_id: str,
    session_id: str,
    tools: list[dict[str, Any]],
) -> tuple[str, str, list[str], list[dict[str, Any]], Optional[str]] | None:
    """Write an explicitly named merchant onto the open debit change."""
    latest = pa.latest_for_session(session_id)
    if (
        latest is None
        or latest.status != "pending"
        or latest.customer_id != customer_id
        or latest.action != "change_amount"
        or not latest.payload.get("unresolved_merchant")
    ):
        return None
    if _SUB_READ.search(utterance):
        return None
    matches = _explicit_subscriptions(customer_id, utterance)
    if len(matches) > 1:
        return (
            "block",
            "这句话点到了不止一个订阅商家，我不会从中挑选。请只说一个商家（如 Netflix / 乐刻）。",
            ["SUB_MERCHANT_AMBIGUOUS"],
            tools,
            latest.pending_id,
        )
    if not _is_merchant_supplement(utterance, matches):
        return None
    sub = matches[0]
    before = {k: sub[k] for k in ("amount_cny", "status", "debit_enabled", "next_debit_date")}
    code, pend = pa.bind_pending_merchant(
        latest.pending_id,
        session_id=session_id,
        target_id=sub["subscription_id"],
        merchant=str(sub["merchant"]),
        before=before,
    )
    if code != "PENDING_MERCHANT_BOUND" or pend is None:
        return "block", f"无法绑定商家：{code}。订阅未改动。", [code], tools, latest.pending_id
    tools.append({
        "tool": "bind_pending_merchant",
        "ok": True,
        "pending_id": pend.pending_id,
        "merchant": sub["merchant"],
    })
    new_amt = pend.payload.get("new_amount_cny")
    shown_new = f"{float(new_amt):.0f}" if isinstance(new_amt, (int, float)) else "?"
    current = float(sub["amount_cny"])
    return (
        "block",
        (
            f"已把待确认的代扣改额绑定到 {sub['merchant']}，新月费 {shown_new} 元"
            f"（当前仍为 {current:.0f} 元）。请回复「确认」或「取消」。"
            f"尚未落账（pending_id={pend.pending_id}）。"
        ),
        ["PENDING_CONFIRM_REQUIRED"],
        tools,
        pend.pending_id,
    )


_DIGIT_AMOUNT = r"-?\d{1,3}(?:[,，]\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?"
_CN_AMOUNT = r"[零一二两三四五六七八九十百千万亿个]+"
_AMOUNT_TOKEN = rf"(?:{_DIGIT_AMOUNT}|{_CN_AMOUNT})(?:\s*(?:{_AMOUNT_UNIT}))?"
_FROM_TO_CHANGE = r"改成|改为|调整为|改到|调成|变成"
_AMOUNT_VERB = r"改成|改为|调整为|调整|改额|改到|设为|变成"


def _coerce_amount(token: str) -> float | None:
    """One amount, whatever notation: 2000 / 2,000 / 2，000 / 二千 / 2千."""
    m = re.fullmatch(
        rf"({_DIGIT_AMOUNT}|{_CN_AMOUNT})\s*({_AMOUNT_UNIT})?",
        token.strip(),
    )
    if not m:
        return None
    raw, unit = m.group(1), m.group(2) or ""
    if re.search(r"[零一二两三四五六七八九十百千万亿个]", raw):
        base = _cn_num(raw)
        if base is None:
            return None
    else:
        base = float(raw.replace(",", "").replace("，", ""))
    return base * _UNIT_MULT.get(unit, 1.0)


def _parse_sub_new_amount(utterance: str) -> float | None:
    m = re.search(rf"(?:{_AMOUNT_VERB})\s*({_AMOUNT_TOKEN})", utterance)
    if m:
        value = _coerce_amount(m.group(1))
        if value is not None:
            return value
    amounts = _parse_amounts(utterance)
    return amounts[-1] if amounts else None


def _parse_from_to(utterance: str) -> tuple[float | None, float | None]:
    """Parse 「从 200 改成 2,000」 / 「从两百改成两千」. Missing side stays None."""
    m = re.search(
        rf"从\s*({_AMOUNT_TOKEN})\s*(?:{_FROM_TO_CHANGE})\s*({_AMOUNT_TOKEN})",
        utterance,
    )
    if not m:
        return None, None
    return _coerce_amount(m.group(1)), _coerce_amount(m.group(2))


def _subscription_confirm_above() -> float:
    cfg = load_rules().get("subscription") or {}
    return float(cfg.get("require_confirm_above_cny", 1000))


def _sub_change_needs_confirm(old: float | None, new: float) -> bool:
    """A debit change strictly above the configured threshold must be confirmed."""
    limit = _subscription_confirm_above()
    if new > limit:
        return True
    if old is not None and abs(new - old) > limit:
        return True
    return False


# Payee change is a role synonym next to a rewrite synonym, not one sentence.
_PAYEE_ROLE = re.compile(
    r"收款人|收款方|收款对象|收款账户|收款账号|收款帐号|收钱的人|收钱人"
    r"|对方(?:的)?(?:账户|账号|帐号|卡号|卡)?"
    r"|卡号|(?:账|帐)号|(?:账|帐)户"
    r"|打给|付给|汇给|转给"
)
_PAYEE_REWRITE = re.compile(
    r"换成|改为|改成|改到|改一下|换一下|换个|换一个|换了|换人"
    r"|不要|别给|不是|另给"
)
_PENDING_DOMAIN = {
    "transfer": "transfer",
    "change_amount": "subscription_manage",
    "pause_debit": "subscription_manage",
    "resume_debit": "subscription_manage",
    "cancel_sub": "subscription_manage",
}


def _payee_rewritten(utterance: str) -> bool:
    """True when a recipient-role word sits next to a rewrite word."""
    for match in _PAYEE_ROLE.finditer(utterance):
        start = max(0, match.start() - 12)
        end = min(len(utterance), match.end() + 12)
        if _PAYEE_REWRITE.search(utterance[start:end]):
            return True
    return False


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
    if _CONFIRM.fullmatch(u):
        # Use latest pending for this session
        latest = pa.latest_for_session(session_id)
        if latest is None:
            return "block", "当前没有待确认的订阅变更，请先说明要改哪一项。", ["PENDING_NOT_FOUND"], tools, None
        merchant_unbound = latest.action == "change_amount" and (
            not latest.target_id
            or latest.target_id not in bank_seed.SUBSCRIPTIONS
            or latest.payload.get("unresolved_merchant")
        )
        if latest.status == "pending" and merchant_unbound:
            return (
                "block",
                "待确认的代扣改额还没有绑定商家，未改动。请说明要改哪一个订阅后再确认。",
                ["SUB_MERCHANT_MISSING"],
                tools,
                latest.pending_id,
            )
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
            r = _local_http_post(
                f"{mock_bank_url.rstrip('/')}/v1/subscriptions/{pend.target_id}/apply",
                payload,
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

    if _CANCEL.fullmatch(u):
        latest = pa.latest_for_session(session_id)
        if latest is None:
            return "block", "没有可取消的待确认变更。", ["PENDING_NOT_FOUND"], tools, None
        code, pend = pa.cancel_pending(latest.pending_id, session_id=session_id)
        return "allow" if code == "PENDING_CANCELLED" else "block", f"待确认变更取消结果：{code}。", [code], tools, latest.pending_id

    # Write intents → PendingAction only. Never pick a merchant from the amount.
    # Merchant supplements are bound in run_agent before this turn is dispatched.
    sub = _find_sub_by_merchant(customer_id, utterance)
    if re.search(r"改成|改为|调整|改额|改到|设为|变成", utterance) and (
        re.search(r"订阅|代扣|月费|Netflix|网飞|Spotify|乐刻|iCloud", utterance, re.I)
        or sub
    ):
        old_amt, parsed_new = _parse_from_to(utterance)
        new_amt = parsed_new if parsed_new is not None else _parse_sub_new_amount(utterance)
        if sub is None:
            # Material change with no merchant: do not guess a subscription.
            # Record a confirmation and leave every debit amount untouched.
            if new_amt is not None and _sub_change_needs_confirm(old_amt, new_amt):
                before_amounts = {
                    s["subscription_id"]: s["amount_cny"] for s in _list_subscriptions(customer_id)
                }
                pend = pa.create_pending(
                    session_id=session_id,
                    customer_id=customer_id,
                    action="change_amount",
                    target_id="",
                    payload={
                        "new_amount_cny": new_amt,
                        "old_amount_cny": old_amt,
                        "merchant": None,
                        "unresolved_merchant": True,
                    },
                    before={"subscriptions": before_amounts},
                )
                tools.append({
                    "tool": "create_pending",
                    "ok": True,
                    "pending_id": pend.pending_id,
                    "merchant": None,
                })
                shown_old = f"{old_amt:.0f}→" if old_amt is not None else ""
                return (
                    "allow",
                    (
                        f"代扣改额 {shown_old}{new_amt:.0f} 元已超过 "
                        f"{_subscription_confirm_above():.0f} 元确认阈值，已记入待确认，"
                        "但还没有绑定商家，因此不会落账。"
                        "请补充商家（如 Netflix / 乐刻）后回复「确认」或「取消」。"
                        f"（pending_id={pend.pending_id}）"
                    ),
                    ["PENDING_CONFIRM_REQUIRED"],
                    tools,
                    pend.pending_id,
                )
            return "block", "请说明要改哪一个订阅商家（如 Netflix / Spotify / 乐刻）。", ["SUB_MERCHANT_MISSING"], tools, None
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


_TAKEOUT_KEYS = ("外卖", "美团", "饿了么", "餐饮")


def _bill_insight_turn(
    utterance: str,
    customer_id: str,
    rules: dict,
) -> tuple[str, str, list[str], list[dict[str, Any]], Optional[str]]:
    """W1 cross-scene: readonly bill insight + optional wealth suggest. Zero fund writes."""
    tools: list[dict[str, Any]] = []
    bills = _list_bills(customer_id)
    tools.append({"tool": "list_bills", "ok": True, "count": len(bills)})

    def _is_takeout(b: dict[str, Any]) -> bool:
        if b.get("status") == "insight" or float(b.get("amount_cny") or 0) <= 0:
            return False
        blob = f"{b.get('merchant', '')}{b.get('note', '')}{b.get('category', '')}"
        return any(k in blob for k in _TAKEOUT_KEYS)

    takeout = [b for b in bills if _is_takeout(b)]
    takeout_sum = sum(float(b.get("amount_cny") or 0) for b in takeout)
    anomalies = [b for b in bills if b.get("anomaly")]
    month_total = sum(
        float(b.get("amount_cny") or 0)
        for b in bills
        if str(b.get("posted_at", "")).startswith("2026-10")
    )

    # B03: 用户声称的金额若在账单中不存在，不得编造或默认附和，必须先否认再给真实数据
    # 只在「断言这笔钱已经扣过」的语境下核对，避免把「转 300 元去备用金」当成既成扣款
    # 只认「断言已被扣款」的措辞；「怎么多了 3000 元」是询问归因（X08 期望 allow），不算断言
    asserted = re.findall(
        r"(?:扣款|扣了|被扣|消费了|花了我)[^\d]{0,6}(\d{3,})\s*元"
        r"|(\d{3,})\s*元[^\d]{0,6}(?:扣款|扣了|被扣)",
        utterance,
    )
    claimed = [float(a or b) for a, b in asserted]
    missing = [c for c in claimed if not any(abs(float(b.get("amount_cny") or 0) - c) < 0.01 for b in bills)]
    if missing:
        amt = "、".join(f"{m:.0f}" for m in missing)
        lines: list[str] = [
            f"【账单核验】我在您的账单记录里没有找到 {amt} 元的扣款，"
            "因此无法确认这笔交易的真实性；以下只列实际存在的账单，不做推测。"
        ]
    else:
        lines = ["【账单洞察】本月相关支出摘要："]
    if takeout:
        lines.append(f"- 外卖/餐饮相关合计约 {takeout_sum:.0f} 元（{len(takeout)} 笔）")
        for b in takeout[:4]:
            lines.append(f"  · {b.get('merchant')} {float(b.get('amount_cny') or 0):.0f} 元")
    else:
        lines.append("- 暂无外卖类账单明细；可结合订阅与日常消费再看预算。")
    if month_total:
        lines.append(f"- 本月已入账账单合计约 {month_total:.0f} 元（含订阅等）")
    if anomalies:
        a = anomalies[0]
        lines.append(
            f"- 异常扣款提示：{a.get('merchant')} {float(a.get('amount_cny') or 0):.0f} 元"
            f"（{a.get('note', '')}）"
        )

    reasons = ["BILL_INSIGHT_OK"]
    # Soft product hint when user asks about 货基/挪钱 — no purchase/transfer write
    if re.search(r"货基|挪|理财|基金|短债|稳健", utterance):
        cust = _customer(customer_id)
        pid = suggest_product(utterance, int(cust.get("risk_score", 1)), rules) or "WB_CASH_001"
        # Prefer cash MM for Script E「挪一点去货基」
        if re.search(r"货基", utterance):
            pid = "WB_CASH_001"
        prod = bank_seed.PRODUCTS.get(pid) or {}
        tools.append({"tool": "suggest_product", "ok": True, "product_id": pid, "write": False})
        reasons.append("PRODUCT_HINT")
        hint = (
            "\n【理财建议·非承诺】若希望把闲钱挪向货基，可参考目录产品"
            f"{prod.get('name', pid)}（{pid}）：流动性 {prod.get('liquidity', '—')}，"
            f"{prod.get('expected_yield_hint', '收益率仅供参考')}。"
            "过往业绩不代表未来表现；理财非存款，产品有风险；本轮仅为洞察建议，"
            "未发起申购或转账。若要划转具体金额（如「把 300 元转到备用金」），请明确金额后走确认门。"
        )
        lines.append(hint)
    else:
        lines.append("\n如需理财产品说明或划转备用金，请补充风险偏好或具体金额。")

    # Hard rule: insight-only — never emit fund-write tools
    write_tools = {"transfer_apply", "subscription_apply", "wealth_purchase_apply", "purchase_apply"}
    assert not any(t.get("tool") in write_tools for t in tools)

    if missing:
        # 用户声称的扣款不存在：不确认、不附和（默认拒绝），但把真实账单摆出来
        return "block", "\n".join(lines), reasons + ["BILL_CLAIM_UNVERIFIED"], tools, None

    return "allow", "\n".join(lines), reasons, tools, None



def _default_bank_url() -> str:
    """Resolve the Mock Bank base URL once, at call time.

    ``.env.example`` has advertised ``MOCK_BANK_URL`` since W0, but the value was
    never actually read — every caller silently used the hard-coded default. That
    also made the test suite depend on a coincidence: if a Mock Bank happened to be
    listening on 127.0.0.1:8000, the confirmation tests took the HTTP branch, wrote
    to *that* process, and then asserted against local seed memory (2 failures).
    Reading the env var makes the URL configurable and lets tests pin an unused port.
    """
    return os.environ.get("MOCK_BANK_URL") or _DEFAULT_BANK_URL


def run_agent(
    utterance: str,
    customer_id: str = "cust_yw_001",
    mock_bank_url: str | None = None,
    audit: AuditLogger | None = None,
    session_id: str | None = None,
) -> AgentState:
    """Execute one turn. Demo path: 问理财 → 拦 / 放行；W1 含订阅确认门."""
    mock_bank_url = mock_bank_url or _default_bank_url()
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

    # Short replies follow the latest action's type; terminal actions cannot fall back to older ones.
    short_reply = bool(_CONFIRM.fullmatch(utterance.strip()) or _CANCEL.fullmatch(utterance.strip()))
    pending = pa.latest_for_session(sid) if short_reply else None
    if short_reply:
        verdict = ComplianceVerdict(
            allowed=True, intent="transfer" if pending and pending.action == "transfer" else "subscription_manage",
            product_id=None, reason_codes=["SESSION_CONFIRM_UTTERANCE"], response_hint="", gates=[],
        )
    else:
        verdict = run_four_gates(utterance, cust, rules)
    state.verdict = verdict
    state.intent = verdict.intent
    state.product_id = verdict.product_id
    state.plan = _plan_for_intent(verdict.intent)
    state.decision = "allow" if verdict.allowed else "block"

    # A later turn drops the open confirmation when it changes intent, payee,
    # clarifies, or replaces the write. Confirm only reaches the latest one.
    new_write = verdict.intent == "transfer" or (
        verdict.intent == "subscription_manage"
        and re.search(r"改成|改为|调整|改额|改到|设为|暂停|停止代扣|取消订阅|退订", utterance)
    )
    payee_changed = _payee_rewritten(utterance)
    if not short_reply:
        previous = pa.latest_for_session(sid)
        stale_reason: str | None = None
        if previous and previous.customer_id == customer_id and previous.status == "pending":
            # Naming the missing merchant continues this debit change.
            supplementing = (
                previous.action == "change_amount"
                and previous.payload.get("unresolved_merchant")
                and verdict.allowed
                and _is_merchant_supplement(
                    utterance, _explicit_subscriptions(customer_id, utterance),
                )
            )
            if supplementing:
                stale_reason = None
            elif previous.action == "transfer" and payee_changed:
                stale_reason = "payee_changed"
            elif "CLARIFY_REQUIRED" in verdict.reason_codes:
                stale_reason = "clarification"
            elif verdict.intent != _PENDING_DOMAIN.get(previous.action):
                stale_reason = "intent_changed"
            elif new_write:
                stale_reason = "superseded_by_new_request"
        if stale_reason and previous is not None:
            code, _ = pa.cancel_pending(previous.pending_id, session_id=sid)
            state.tool_calls.append({
                "tool": "cancel_pending",
                "reason": stale_reason,
                "code": code,
                "pending_id": previous.pending_id,
            })
    # A new transfer that already names an amount is a fresh order, not a reuse of the old confirmation.
    new_transfer_order = verdict.intent == "transfer" and _parse_transfer_amount(utterance) is not None
    payee_clarify = payee_changed and verdict.allowed and not new_transfer_order
    # Bind before intent dispatch: an alias like 「健身」 may not classify as subscription_manage.
    supplement_result = None
    if not short_reply and not payee_clarify and verdict.allowed:
        supplement_result = _bind_merchant_supplement(utterance, customer_id, sid, [])

    if short_reply and (pending is None or pending.customer_id != customer_id):
        code = "PENDING_NOT_FOUND" if pending is None else "PENDING_CUSTOMER_MISMATCH"
        state.decision = "block"
        state.response = "当前会话没有属于本客户的确认单，未执行任何变更。"
        verdict.allowed = False
        verdict.reason_codes.append(code)
        verdict.response_hint = state.response
    elif short_reply and pending.action != "transfer" and utterance.strip() in {"确认转账", "取消转账", "不转了"}:
        state.decision = "block"
        state.response = "当前确认单是订阅变更，不是转账；未执行任何变更。"
        verdict.allowed = False
        verdict.reason_codes.append("PENDING_ACTION_MISMATCH")
        verdict.response_hint = state.response
    elif supplement_result is not None:
        decision, response, xreasons, tools, pend_id = supplement_result
        state.intent = "subscription_manage"
        state.decision = decision
        state.response = response
        state.pending_id = pend_id
        state.tool_calls.extend(tools)
        verdict.reason_codes = list(verdict.reason_codes) + xreasons
        verdict.allowed = decision == "allow"
        if decision == "block":
            verdict.response_hint = response
    elif payee_clarify:
        state.decision = "block"
        state.response = (
            "确认只对当时的金额和收款人有效。收款人一变，原确认就作废，我不会按新收款人执行。"
            "请重新说明金额和收款账户。"
        )
        verdict.allowed = False
        verdict.reason_codes = list(verdict.reason_codes) + ["CLARIFY_REQUIRED"]
        verdict.response_hint = state.response
    elif verdict.intent == "subscription_manage":
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
    elif verdict.intent == "bill_insight":
        if not verdict.allowed:
            state.response = verdict.response_hint
            state.decision = "block"
        else:
            decision, response, xreasons, tools, pend_id = _bill_insight_turn(
                utterance, customer_id, rules
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
            decision, response, xreasons, tools, pend_id = _transfer_turn(utterance, customer_id, sid, rules)
            state.decision = decision
            state.response = response
            state.pending_id = pend_id
            state.tool_calls.extend(tools)
            verdict.reason_codes = list(verdict.reason_codes) + xreasons
            # Keep ComplianceVerdict.allowed in sync with transfer limit gate
            verdict.allowed = decision == "allow"
            if decision == "block":
                verdict.response_hint = response
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
