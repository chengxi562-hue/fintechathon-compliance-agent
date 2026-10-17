"""R2 话术同义归一：NFKC + 去空白 + 大小写折叠 + 中英/拼音同义表。

归一化后所有禁词匹配都在「无空白、小写、半角」文本上进行，
使「保 本」「BAOBEN」「guaranteed return」「内部人」「肯定不亏」等变体
统一命中禁词门（gate_script），且不误拦正常咨询。

无外部依赖；gates.gate_script 调用 normalize_text + match_script_violations。
"""

from __future__ import annotations

import re
import unicodedata

# 零宽 / 不可见字符（防拆字、视觉欺骗、零宽拼接）
_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """NFKC → 小写 → 去零宽 → 去所有空白。

    NFKC 折叠全角英文字母（ＧＵＡＲＡＮＴＥＥＤ → guaranteed）与兼容字符；
    去空白使「保 本」→「保本」、英文短语「guaranteed return」→「guaranteedreturn」。
    """
    t = unicodedata.normalize("NFKC", text)
    t = _ZERO_WIDTH.sub("", t)
    t = t.lower()
    t = _WHITESPACE.sub("", t)
    return t


# 禁词同义表：canonical 禁词 -> 归一化后的同义 / 拼音 / 英文变体（均已小写、去空白）。
# 命中任一变体即视为命中 canonical 禁词（USER_FORBIDDEN / SCRIPT_RISK）。
SYNONYM_GROUPS: dict[str, tuple[str, ...]] = {
    "保本": ("保本", "baoben", "保底", "本金保障"),
    "内幕": ("内幕", "内部人", "内部消息", "内部人员", "insider"),
    "保证收益": ("保证收益", "guaranteed", "肯定不亏", "不会亏", "不亏"),
    "稳赚": ("稳赚", "稳赚不赔", "只赚不赔", "包赚"),
    "零风险": ("零风险", "无风险", "norisk", "riskfree", "risk-free", "zerorisk"),
    "刚兑": ("刚兑", "刚性兑付", "刚兑保本"),
}

# 正则变体：非简单子串匹配（需跨字符 / 可选中间字 / 前后文）。
# label 用于生成 SCRIPT_RISK:<label> 原因码。
VARIANT_PATTERNS: dict[str, re.Pattern[str]] = {
    # S06「能不能复制」：业绩/收益/赚等 + 复制（或反向），承诺业绩可复制
    "承诺业绩": re.compile(
        r"(赚|收益|业绩|回报|年化).{0,8}复制|复制.{0,8}(赚|收益|业绩|回报|年化)"
    ),
    # S08「亏了你赔吗」：兜底 / 包赔承诺
    "不亏兜底": re.compile(r"亏了.{0,3}赔|包赔"),
}


def variants_for(phrase: str) -> tuple[str, ...]:
    """展开禁词为归一化后的全部变体；无同义表时退化为其自身归一化。"""
    norm = normalize_text(phrase)
    group = SYNONYM_GROUPS.get(phrase)
    if group is None:
        return (norm,)
    seen: list[str] = []
    for v in (norm, *group):
        if v not in seen:
            seen.append(v)
    return tuple(seen)


def match_script_violations(
    norm: str,
    user_demands: list[str],
    forbidden_phrases: list[str],
) -> list[str]:
    """在归一化文本上匹配话术禁词，返回原因码列表（空 = 未命中）。"""
    reasons: list[str] = []
    for phrase in user_demands:
        for v in variants_for(phrase):
            idx = norm.find(v)
            if idx >= 0 and not _negated(norm, idx):
                reasons.append(f"USER_FORBIDDEN:{phrase}")
                break
    for phrase in forbidden_phrases:
        for v in variants_for(phrase):
            idx = norm.find(v)
            if idx >= 0 and not _negated(norm, idx):
                if f"USER_FORBIDDEN:{phrase}" not in reasons:
                    reasons.append(f"SCRIPT_RISK:{phrase}")
                break
    for label, pat in VARIANT_PATTERNS.items():
        if pat.search(norm):
            code = f"SCRIPT_RISK:{label}"
            if code not in reasons:
                reasons.append(code)
    return reasons


# 否定前缀：用户明确「不需要/不追求」某禁词时，不视为要求禁词（正常披露咨询）
_NEGATION = re.compile(r"(不需要|不用|不要|无需|不追求|不要求|不承诺)$")


def _negated(norm: str, idx: int) -> bool:
    """命中位置前紧邻否定前缀（如「不需要保本」）则视为否定语气，不算命中。"""
    prefix = norm[max(0, idx - 8):idx]
    return bool(_NEGATION.search(prefix))
