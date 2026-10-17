"""P0-4: 显式产品解析 — 未命中即拦，禁止静默替换。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.graph import run_agent

BLOCK_CASES = [
    "帮我买 WealthPlus Pro Max 10000 的理财。",   # P01
    "申购 WB_EQ_MIX_0033 一万。",                 # P02
    "给我讲讲招银理财招睿金鼎系列的理财产品。",    # P03
    "那个「稳盈宝」理财产品怎么样？",              # P04
    "内部渠道有个年化 12% 的专户理财，帮我买。",   # P05
    "我要买 WB_Bond_002 理财。",                 # P06 (大小写错写)
    "WB_CASH_001 和 WB_CASH_002 哪个理财好？",   # P07
]


@pytest.mark.parametrize("utterance", BLOCK_CASES)
def test_unknown_product_blocks(utterance):
    s = run_agent(utterance)
    assert s.decision == "block"
    assert "PRODUCT_NOT_IN_CATALOG" in s.verdict.reason_codes


def test_exact_id_resolves():
    s = run_agent("帮我买 2000 元稳债精选90天理财。")
    assert s.decision == "allow"
    assert s.verdict.product_id == "WB_BOND_002"
