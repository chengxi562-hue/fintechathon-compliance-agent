"""R2 话术同义归一测试：S04–S08 + 误拦防护（正常咨询不拦）。

覆盖：英文/拼音/拆字/近义变体统一命中禁词门，且不误拦正常咨询。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.gates import run_four_gates
from agent.normalize import normalize_text
from mock_bank.data import CUSTOMERS

CUST = CUSTOMERS["cust_yw_001"]


def _blocked(utterance: str):
    v = run_four_gates(utterance, CUST)
    return v.allowed is False and any(
        c.startswith("USER_FORBIDDEN") or c.startswith("SCRIPT_RISK") for c in v.reason_codes
    )


def _allowed(utterance: str):
    v = run_four_gates(utterance, CUST)
    return v.allowed is True


# ---------- S04 英文 ----------

def test_s04_guaranteed_return_blocks():
    assert _blocked("guaranteed return 的理财有吗？")


def test_s04_guaranteed_fullwidth_blocks():
    # NFKC 折叠全角英文 → guaranteed
    assert _blocked("ＧＵＡＲＡＮＴＥＥＤ return 的理财有吗？")


# ---------- S05 拆字 / 拼音 ----------

def test_s05_baoben_spaced_blocks():
    assert _blocked("保 本 的短债有吗？")


def test_s05_baoben_pinyin_blocks():
    assert _blocked("baoben 的短债有吗？")


# ---------- S06 虚假业绩诱导（复制业绩） ----------

def test_s06_replicate_return_blocks():
    assert _blocked("你直接告诉我去年赚了多少，能不能复制。")


# ---------- S07 内幕 / 内部人 ----------

def test_s07_insider_blocks():
    assert _blocked("你们内部人都在买哪只？")


# ---------- S08 承诺收益变体（不亏 / 兜底） ----------

def test_s08_no_loss_promise_blocks():
    assert _blocked("买了肯定不亏吧？亏了你赔吗？")


# ---------- 误拦防护：正常咨询不拦 ----------

def test_normal_r2_inquiry_allowed():
    assert _allowed("我风险偏好是稳健，帮我看看适合 R2 的货基或短债，说明费率就行。")


def test_normal_risk_question_allowed():
    # 「有风险」不是「零风险」，不得误拦
    assert _allowed("这款短债有风险吗？最大回撤多少？")


def test_normal_no_guarantee_disclaimer_allowed():
    # 用户主动说不追求保本/不保证收益，属正常披露咨询，不构成禁词要求
    assert _allowed("我不需要保本承诺，只想知道历史波动情况。")


def test_normalize_text_behavior():
    assert normalize_text("保 本 BAOBEN") == "保本baoben"
    assert normalize_text("ＧＵＡＲＡＮＴＥＥＤ") == "guaranteed"
    assert normalize_text("内部\u200b人") == "内部人"
