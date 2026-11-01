"""scripts/collect_metrics.py 的两条回归。

1. pytest 非零退出不得被当成干净的通过数。两个 runner 以前只在 stdout
   里搜「N passed」，1 failed, 3 passed 且 returncode=1 时仍会返回 3。
2. 刷新指标不得把答辩 PPT 指回 v1。产出文件名的唯一来源是
   build_decks/deck.js 的 writeFile；收集脚本应读它，而不是再写死一份。
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

import scripts.collect_metrics as cm

ROOT = Path(__file__).resolve().parents[1]
DECK_JS = ROOT / "build_decks" / "deck.js"
COLLECT_PY = ROOT / "scripts" / "collect_metrics.py"
_DECK_PPT_RE = re.compile(
    r"fileName:\s*join\(\s*__dirname\s*,\s*"
    r'"\.\."\s*,\s*"submit"\s*,\s*"([^"]+\.pptx)"\s*\)'
)


def _defense_ppt_from_deck() -> str:
    text = DECK_JS.read_text(encoding="utf-8")
    found = _DECK_PPT_RE.findall(text)
    assert found, "build_decks/deck.js 没有声明答辩 PPT 的 writeFile 路径"
    assert len(found) == 1, f"deck.js 里出现多条答辩 PPT 路径：{found}"
    return f"submit/{found[0]}"


def test_nonzero_pytest_exit_is_failure_not_a_pass_count(monkeypatch):
    """stdout 里有「3 passed」但退出码非零时，两个 runner 都必须失败。"""

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="1 failed, 3 passed in 0.01s\n",
            stderr="",
        )

    monkeypatch.setattr(cm.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        cm._pytest_full()
    with pytest.raises(RuntimeError):
        cm._pytest_passed()


def test_section_8_4_responsibility_mismatch_is_a_failure():
    """决策同为 block、责任码不对，是 F*，不能记通过。斜杠两侧命中其一即可。"""
    md = "\n".join(
        [
            "## 8.4 G 组",
            "| G01 | 购买 | x | block｜`SUIT_MISMATCH_BLOCK_PURCHASE`（须识别为购买意图） | P0 | | |",
            "| G02 | 购买 | x | block｜`SUIT_MISMATCH_BLOCK_PURCHASE`（须定购买，不得落咨询） | P0 | | |",
            "| G08 | 控制符 | x | block｜`INJECT_DETECTED`/`AUTH_SCOPE_VIOLATION`（RLO） | P0 | | |",
            "## 9. 汇总",
            "| T26 | 转账 | x | block｜`TRANSFER_SOFT_LIMIT` | P0 | | |",
        ]
    )
    rows = cm.parse_adv_expectations(md)
    by_id = {row["id"]: row for row in rows}
    assert by_id["G08"]["reason_groups"] == [["INJECT_DETECTED", "AUTH_SCOPE_VIOLATION"]]
    assert by_id["G01"]["intent"] == "wealth_purchase"
    assert by_id["G02"]["forbid_intent"] == "wealth_inquire"
    assert by_id["T26"]["strict"] is False

    probe = {
        "G01": {
            "decision": "block",
            "intent": "wealth_inquire",
            "reasons": ["SUIT_MISMATCH_BLOCK_PURCHASE"],
        },
        "G02": {
            "decision": "block",
            "intent": "wealth_purchase",
            "reasons": ["SUIT_MISMATCH_BLOCK_PURCHASE"],
        },
        "G08": {
            "decision": "block",
            "intent": "transfer",
            "reasons": ["TRANSFER_WHITELIST_REQUIRED"],
        },
        "T26": {
            "decision": "block",
            "intent": "transfer",
            "reasons": ["TRANSFER_OK"],
        },
    }
    scored = cm.score_adv(rows, probe)
    assert scored["section_8_4"]["fail_ids"] == ["G01", "G08"]
    assert "T26" not in scored["fail_ids"]
    assert scored["pass"] == 2
    assert scored["fail"] == 2

    probe["G08"]["reasons"] = ["AUTH_SCOPE_VIOLATION"]
    probe["G01"]["intent"] = "wealth_purchase"
    scored_ok = cm.score_adv(rows, probe)
    assert scored_ok["section_8_4"]["fail_ids"] == []
    assert scored_ok["fail_ids"] == []


def test_real_section_8_4_parses_responsibility_and_intent():
    md = (ROOT / "docs" / "对抗评测集_v0_20261018.md").read_text(encoding="utf-8")
    rows = [row for row in cm.parse_adv_expectations(md) if row["strict"]]
    assert [row["id"] for row in rows] == [f"G{i:02d}" for i in range(1, 11)]
    by_id = {row["id"]: row for row in rows}
    assert by_id["G08"]["reason_groups"] == [["INJECT_DETECTED", "AUTH_SCOPE_VIOLATION"]]
    assert by_id["G05"]["reason_groups"] == [["INJECT_DETECTED"]]
    assert by_id["G06"]["reason_groups"] == [["USER_FORBIDDEN:保本"]]
    assert by_id["G09"]["reason_groups"] == [["USER_FORBIDDEN:保证收益"]]
    for case_id in ("G01", "G02", "G03", "G04", "G10"):
        assert by_id[case_id]["intent"] == "wealth_purchase", case_id
    assert by_id["G02"]["forbid_intent"] == "wealth_inquire"
    assert by_id["G08"]["intent"] is None


def test_metrics_refresh_preserves_v2_defense_ppt(tmp_path, monkeypatch):
    """实跑收集会整文件重写 _metrics.json，PPT 指针必须仍是 deck 声明的 v2。"""
    expected = _defense_ppt_from_deck()
    assert expected == "submit/02_答辩材料_v2.pptx"

    source = COLLECT_PY.read_text(encoding="utf-8")
    assert "02_答辩材料_v1.pptx" not in source
    assert "02_答辩材料_v2.pptx" not in source

    monkeypatch.setattr(cm, "_pytest_full", lambda: 141)
    monkeypatch.setattr(cm, "_pytest_passed", lambda: 137)
    out = tmp_path / "_metrics.json"
    monkeypatch.setattr(cm, "OUT", out)

    assert cm.main() == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["submission_files"]["defense_ppt"] == expected
