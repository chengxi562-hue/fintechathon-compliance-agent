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
