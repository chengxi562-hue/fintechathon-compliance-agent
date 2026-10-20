"""Four-gate compliance engine: intent → product match → suitability → script."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from agent.normalize import del33t, match_script_violations, normalize_text



ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "configs" / "compliance_rules.yaml"


@dataclass
class GateResult:
    name: str
    passed: bool
    reason_codes: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceVerdict:
    allowed: bool
    intent: str
    product_id: Optional[str]
    gates: list[GateResult]
    reason_codes: list[str]
    response_hint: str


def load_rules(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path or DEFAULT_RULES)
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


_BUY_VERBS = re.compile(r"买|申购|认购|购入|下单|(?i:buy|subscrib\w*|purchas\w*)")
# M06：明确指向具体目录产品并要求「改成/换成/要那个」= 实际是购买意图
_SWITCH_TO_PRODUCT = re.compile(r"改成|改为|换成|改一下|要那种|就要|来一份|来一个")
_NEG_BUY = re.compile(r"(不|别|勿|无需|不要|不用)\s*买|(?i:don'?t\s*buy|do\s*not\s*buy)")
_TRANSFER_VERBS = re.compile(
    r"转账|转到|转给|转出|转走|转去|转进|转为|转成|打款|付给|汇款|划转"
    r"|转\s*-?\d|转\s*[零一二两三四五六七八九十百千万亿]"
)
_NEG_TRANSFER = re.compile(r"(不用|不要|无需|别|不需)\s*(要)?\s*转账?")


def classify_intent(utterance: str) -> str:
    # 先解码再分类：品名被 URL/unicode/base64 编码时仍要能命中（G04/G10/C 组）
    u = normalize_text(utterance)
    # 否定式「不用/不要/无需转账」→ 不得判 transfer（B05）
    neg_transfer = bool(_NEG_TRANSFER.search(u))

    # 实体优先：目录中文品名或 WB_* 编号命中 → 定 wealth 意图
    # （R01/R03/R04/R06/R07/S09/M02/M06/D06/B05/N02/N05 根因）
    names = _catalog_norm_names()
    has_catalog_name = any(name in u for name in names)
    has_id = bool(re.search(r"WB_[A-Za-z0-9_]*\d", u, re.I))
    neg_buy = bool(_NEG_BUY.search(u))

    if has_catalog_name or has_id:
        if (not neg_buy) and _BUY_VERBS.search(u):
            return "wealth_purchase"
        # 指明具体产品并要求「改成/换成它」→ 购买（M06）；仍走四门，R2 买 R4 会被适当性拦
        if (not neg_buy) and _SWITCH_TO_PRODUCT.search(u) and re.search(r"不是|改|换", u):
            return "wealth_purchase"
        return "wealth_inquire"

    if (not neg_buy) and re.search(r"申购|认购", u):
        return "wealth_purchase"
    if not neg_transfer and _TRANSFER_VERBS.search(u):
        return "transfer"
    if re.search(r"余额|账户", u):
        return "account_balance"
    # 订阅写/查优先于账单洞察（「先别转账，帮我看看订阅」仍走 subscription_manage）
    if re.search(
        r"订阅|代扣|月费|Netflix|网飞|奈飞|Spotify|乐刻|iCloud|退订|暂停代扣",
        u,
        re.I,
    ):
        return "subscription_manage"
    # W1 跨场景：账单/外卖/支出分析 → bill_insight（先于纯 wealth_inquire，避免 Script E 跳过账单）
    if re.search(
        r"账单|外卖|支出分析|花太多|这个月花了|花了多少|消费分析|账单洞察|异常扣款|餐饮周?支出"
        r"|扣款|消费明细|钱被谁收|是谁收的",
        u,
    ):
        return "bill_insight"
    if (not neg_buy) and _BUY_VERBS.search(u) and re.search(r"理财|基金|货基|债", u):
        return "wealth_purchase"
    # 「最安全/绝对安全」询安 → 走 chitchat，由话术门拦截，禁止顺带推品（S09）
    if re.search(r"最安全|绝对安全|哪里最安全|放哪.*安全", u):
        return "chitchat"
    if re.search(r"理财|基金|收益|货基|短债|稳健", u):
        return "wealth_inquire"
    return "chitchat"


def suggest_product(utterance: str, risk_score: int, rules: dict[str, Any]) -> Optional[str]:
    """Pick a catalog product; prefer highest allowed under risk_score."""
    allow = rules["gates"]["product_match"]["catalog_allowlist"]
    mins = rules["gates"]["suitability"]["min_risk_score_by_product"]
    # Prefer aggressive ask → high risk product (will be blocked by suitability if mismatch)
    if re.search(r"最高|高收益|进取|股票|激进", utterance):
        cand = "WB_EQ_MIX_003"
        return cand if cand in allow else None
    if re.search(r"货基|灵活|随取", utterance):
        return "WB_CASH_001"
    if re.search(r"短债|稳健|债", utterance):
        return "WB_BOND_002"
    # Default: best product customer can hold
    eligible = [pid for pid in allow if mins.get(pid, 99) <= risk_score]
    if not eligible:
        return allow[0] if allow else None
    # pick highest min_risk among eligible (more yield within band)
    return max(eligible, key=lambda p: mins.get(p, 0))


# ---------- 显式产品解析（P0-4） ----------


_EN_ALIASES = {
    "aggressive mixed fof": "WB_EQ_MIX_003",
    "aggressivemixedfof": "WB_EQ_MIX_003",
    "mixed fof": "WB_EQ_MIX_003",
    "stable bond 90": "WB_BOND_002",
    "webank flexible cash": "WB_CASH_001",
}


def _catalog_norm_names() -> dict[str, str]:
    """归一化后的 product name -> product_id（与 normalize_text 口径一致）。"""
    return {normalize_text(k): v for k, v in _catalog_names().items()}


def _catalog_names() -> dict[str, str]:
    """product name -> product_id, from seed data（含英文别名，供 G01–G03 用）。"""
    from mock_bank import data as bank_seed

    names = {p["name"]: pid for pid, p in bank_seed.PRODUCTS.items()}
    names.update(_EN_ALIASES)
    return names


def parse_explicit_product(utterance: str, rules: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Return (product_id, unknown_token).

    Exact, case-sensitive catalog ID match first; then longest catalog-name match.
    If a product-like token (ID-ish / suspect name) appears but resolves to no
    catalog entry, return it as unknown_token — caller MUST block, never
    silently substitute another product.
    """
    allow = set(rules["gates"]["product_match"].get("catalog_allowlist", []))
    # 保留原样大小写：目录 ID 精确匹配，`WB_Bond_002` 这类错写必须判未知产品而非静默纠正
    id_tokens = re.findall(r"WB_[A-Za-z0-9_]*\d", utterance)
    unknown_ids = [t for t in id_tokens if t not in allow]
    if unknown_ids:
        return None, unknown_ids[0]
    if id_tokens:
        return id_tokens[0], None
    names = _catalog_norm_names()
    norm = normalize_text(utterance)
    for name in sorted(names, key=len, reverse=True):
        if name in norm:
            return names[name], None
    for sus in rules["gates"]["product_match"].get("suspect_names", []):
        if sus in utterance:
            return None, sus
    # W12 族：明确指向目录外的产品写法（「XX银行理财 999」），一律视为未知产品
    for pat in rules["gates"]["product_match"].get("off_catalog_product_patterns", []):
        m = re.search(pat, utterance)
        if m:
            return None, m.group(0)
    return None, None


def gate_auth_scope(utterance: str, customer: dict[str, Any], rules: dict[str, Any]) -> GateResult:
    """横向越权/代客/测评篡改：本人 only，客服/亲属自述不授权。"""
    g = rules.get("gates", {}).get("auth_scope", {})
    hits: list[str] = []
    # 自述财力/自评等级/签免责 这类「口头授权」也必须按原样与解码后两种形态匹配
    haystacks = [utterance, normalize_text(utterance)]
    for group in ("scope_patterns", "self_service_patterns", "delegation_patterns"):
        for pat in g.get(group, []):
            for hay in haystacks:
                if re.search(pat, hay):
                    hits.append(f"{group}:{pat}")
                    break
    if hits:
        return GateResult("auth_scope", False, ["AUTH_SCOPE_VIOLATION"], {"hits": hits})
    return GateResult("auth_scope", True, ["AUTH_SCOPE_OK"], {})



_INJECT_QUOTED_NEGATION = re.compile(r"(不要|别|无需|不用|禁止)执行?「[^」]*」")


_NEG_PREFIX = re.compile(r"(不要|别|不用|无需|不|禁止|莫|勿)\s*$")


def _inject_negated(pattern: str, haystack: str) -> bool:
    """匹配到注入特征，但紧邻前文是否定语气（「别承诺收益」）→ 不算注入。"""
    for m in re.finditer(pattern, haystack):
        if _NEG_PREFIX.search(haystack[max(0, m.start() - 6):m.start()]):
            return True
    return False


def _inject_scan_text(utterance: str) -> str:
    """I01: 引用式否定语气 — 用户引用攻击文本并要求不要执行时，不算注入。"""
    return _INJECT_QUOTED_NEGATION.sub("", utterance)


def gate_intent(utterance: str, intent: str, rules: dict[str, Any]) -> GateResult:
    g = rules["gates"]["intent"]
    # 扫描两遍：原文 + 解码归一文本（HTML 实体 / URL / \\uXXXX / base64 / 零宽 / 空格拆词）。
    # 编码绕过族（C01/C03/C05/C06/C07/C09）靠这一步覆盖，而不是为每种编码各写一条正则。
    scans = [_inject_scan_text(utterance), _inject_scan_text(normalize_text(utterance))]
    for pat in g.get("inject_patterns", []):
        for scan in scans:
            if _inject_negated(pat, scan):
                continue
            if re.search(pat, scan):
                return GateResult("intent", False, ["INJECT_DETECTED"], {"intent": intent, "via": "direct"})
    for pat in g.get("indirect_inject_patterns", []):
        for scan in scans:
            if re.search(pat, scan):
                return GateResult("intent", False, ["INJECT_DETECTED"], {"intent": intent, "via": "indirect"})
    if intent not in g.get("allowed_intents", []):
        return GateResult("intent", False, ["INTENT_NOT_ALLOWED"], {"intent": intent})
    return GateResult("intent", True, ["INTENT_OK"], {"intent": intent})


def gate_product_match(product_id: Optional[str], rules: dict[str, Any], need_product: bool) -> GateResult:
    g = rules["gates"]["product_match"]
    allow = set(g.get("catalog_allowlist", []))
    if not need_product:
        return GateResult("product_match", True, ["PRODUCT_N_A"], {"product_id": product_id})
    if not product_id:
        return GateResult("product_match", False, ["PRODUCT_MISSING"], {})
    if product_id not in allow and g.get("reject_unknown_product", True):
        return GateResult("product_match", False, ["PRODUCT_NOT_IN_CATALOG"], {"product_id": product_id})
    return GateResult("product_match", True, ["PRODUCT_OK"], {"product_id": product_id})


def gate_suitability(
    intent: str,
    product_id: Optional[str],
    customer_risk: int,
    rules: dict[str, Any],
) -> GateResult:
    g = rules["gates"]["suitability"]
    if not product_id:
        return GateResult("suitability", True, ["SUIT_N_A"], {})
    mins = g.get("min_risk_score_by_product", {})
    need = int(mins.get(product_id, 99))
    mismatch = customer_risk < need
    details = {
        "customer_risk_score": customer_risk,
        "product_min_risk_score": need,
        "mismatch": mismatch,
    }
    if not mismatch:
        return GateResult("suitability", True, ["SUIT_OK"], details)
    if intent == "wealth_purchase" and g.get("block_purchase_if_mismatch", True):
        return GateResult("suitability", False, ["SUIT_MISMATCH_BLOCK_PURCHASE"], details)
    if intent == "wealth_inquire" and g.get("block_inquire_if_mismatch", False):
        return GateResult("suitability", False, ["SUIT_MISMATCH_BLOCK_INQUIRE"], details)
    # inquire mismatch: pass gate but flag for soft warning in response
    return GateResult("suitability", True, ["SUIT_MISMATCH_WARN"], details)


def gate_clarify(utterance: str, rules: dict[str, Any]) -> Optional[GateResult]:
    """模糊/越权资金动作的问法，必须先澄清或拒绝，不得直接给动作。

    覆盖评测集 X07（房贷怎么还划算）/ W19（全部身家）/ M05（VIP 施压）等：
    这类问法没有明确产品、金额或授权依据，直接放行等于默许执行。
    """
    pats = rules.get("clarify", {}).get("ambiguous_patterns", [])
    norm = normalize_text(utterance)
    for pat in pats:
        if re.search(pat, utterance) or re.search(pat, norm):
            return GateResult("clarify", False, ["CLARIFY_REQUIRED"], {"pattern": pat})
    # 身份/权限自述施压（VIP / 老客户 / 特批）不得成为绕过依据
    if re.search(r"我是\s*(VIP|vip|白金|黑金|老客户|大客户)|特批|内部员工", utterance):
        return GateResult("clarify", False, ["CLARIFY_REQUIRED"], {"pattern": "self-claimed-privilege"})
    return None


def gate_script(utterance: str, rules: dict[str, Any]) -> GateResult:
    g = rules["gates"]["script"]
    # R2：归一化（NFKC/去空白/大小写）后再匹配，命中中英/拼音同义变体即拦
    norm = normalize_text(utterance)
    reasons = match_script_violations(
        norm,
        g.get("user_forbidden_demands", []),
        g.get("forbidden_phrases", []),
    )
    if not reasons:
        # leetspeak 同形替换（G09）：gu4r4nteed r3turn → guaranteed return
        reasons = match_script_violations(
            del33t(norm),
            g.get("user_forbidden_demands", []),
            g.get("forbidden_phrases", []),
        )
    if reasons:
        # Block when user insists on forbidden guarantees / risky framing
        return GateResult("script", False, reasons, {"blocked": True})
    return GateResult("script", True, ["SCRIPT_OK"], {})


def run_four_gates(
    utterance: str,
    customer: dict[str, Any],
    rules: dict[str, Any] | None = None,
    forced_product_id: Optional[str] = None,
) -> ComplianceVerdict:
    rules = rules or load_rules()
    intent = classify_intent(utterance)
    need_product = intent in {"wealth_inquire", "wealth_purchase"}
    product_id = forced_product_id
    unknown_product: Optional[str] = None
    if need_product and not product_id:
        explicit, unknown_product = parse_explicit_product(utterance, rules)
        if explicit:
            product_id = explicit
        elif unknown_product is None:
            product_id = suggest_product(utterance, int(customer.get("risk_score", 1)), rules)
    elif not need_product and not product_id:
        # Still resolve mentions so unknown product tokens outside wealth intents are caught
        _, unknown_product = parse_explicit_product(utterance, rules)

    g0 = gate_auth_scope(utterance, customer, rules)
    g1 = gate_intent(utterance, intent, rules)
    if unknown_product is not None and g1.passed:
        # 疑似产品名/编号未命中目录：直接拦，禁止静默替换
        g2 = GateResult("product_match", False, ["PRODUCT_NOT_IN_CATALOG"], {"unknown": unknown_product})
        g3 = gate_suitability(intent, None, int(customer.get("risk_score", 1)), rules)
    else:
        g2 = gate_product_match(product_id, rules, need_product)
        g3 = gate_suitability(intent, product_id if g2.passed else None, int(customer.get("risk_score", 1)), rules)
    g4 = gate_script(utterance, rules)
    g5 = gate_clarify(utterance, rules)

    gates = [g0, g1, g2, g3, g4] + ([g5] if g5 is not None else [])
    # Special: inquire + mismatch warn is allowed; purchase mismatch fails g3
    # Script fail on 保本 should block even inquire
    allowed = all(g.passed for g in gates)
    reason_codes: list[str] = []
    for g in gates:
        reason_codes.extend(g.reason_codes)

    if not allowed:
        if any(c.startswith("USER_FORBIDDEN") or c.startswith("SCRIPT_RISK") for c in reason_codes):
            hint = (
                "无法按「保本/稳赚」等方式承诺收益。理财非存款、产品有风险。"
                "如需查询，请说明您的风险偏好（例如稳健 R2），我可介绍目录内合适产品。"
            )
        elif "SUIT_MISMATCH_BLOCK_PURCHASE" in reason_codes:
            hint = "该产品风险等级高于您的适当性测评结果，已拦截购买。可改看稳健型货基或短债。"
        elif "INJECT_DETECTED" in reason_codes:
            hint = "检测到异常指令，已拒绝执行。"
        elif "AUTH_SCOPE_VIOLATION" in reason_codes:
            hint = "仅可办理本人名下业务；客服/亲属自述不构成授权，已拦截。"
        elif "CLARIFY_REQUIRED" in reason_codes:
            hint = (
                "这个问法还不够明确，我不直接给结论或执行动作。"
                "请说明具体产品（目录内）、金额与用途，我再按四道合规门处理。"
            )
        elif "PRODUCT_NOT_IN_CATALOG" in reason_codes:
            hint = "您提到的产品不在我行产品目录内，无法介绍或办理；请以官方目录为准。"
        else:
            hint = "合规门未通过，已拦截本次操作。"
    else:
        if "SUIT_MISMATCH_WARN" in reason_codes:
            hint = (
                f"产品 {product_id} 风险偏高，仅作说明、不构成推荐购买。"
                "过往业绩不代表未来表现；理财非存款，产品有风险。"
            )
        elif need_product:
            hint = (
                f"可为您介绍目录产品 {product_id}。"
                "过往业绩不代表未来表现；理财非存款，产品有风险。"
            )
        else:
            hint = "合规检查通过，可继续办理。"

    return ComplianceVerdict(
        allowed=allowed,
        intent=intent,
        product_id=product_id,
        gates=gates,
        reason_codes=reason_codes,
        response_hint=hint,
    )
