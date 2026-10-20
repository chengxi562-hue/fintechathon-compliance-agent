"""对外材料里的数字必须与实际跑出来的一致。

这才是根因修复：单测数曾在 8 个文件里手写成 128/131/132/135 四种版本，
因为每次加测试都要手工改十几处，必然漏。现在由
  scripts/collect_metrics.py（实跑取数）→ scripts/sync_metrics.py（注入）
统一维护，本测试守住「注入真的生效了」。

历史快照文件（standup / W1 / W2 执行说明）是有意豁免的：它们记录当时的真实状态，
改掉等于篡改历史。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "data" / "evals" / "_metrics.json"

# 必须与 scripts/sync_metrics.py 的 TARGETS 保持一致
TARGETS = [
    "README.md",
    "docs/路演一页纸_20261018.md",
    "docs/平台提交核对清单_20261020.md",
    "submit/03_打包说明.md",
    "submit/06_平台提交字段草稿_20261020.md",
    "submit/07_高依灵_指标签字单_20261020.md",
    "submit/_build/build_tech_doc.py",
    "submit/_build/build_security_report.py",
    "submit/_build/pitch.js",
]

PASSED_RE = re.compile(r"\b(\d{2,4})\s*passed\b")


import pytest


def _metrics_or_skip() -> dict:
    """_metrics.json 是实跑产物、故意不入库。

    解压提交包后直接 pytest 时它不存在——这时应 skip（缺产物），
    而不是 fail（代码错）。跑过 collect_metrics.py 后再 pytest 才做真校验。
    """
    if not METRICS.exists():
        pytest.skip("data/evals/_metrics.json 未生成；先跑 scripts/collect_metrics.py")
    return json.loads(METRICS.read_text(encoding="utf-8"))


def test_counting_convention_is_declared():
    """口径必须显式声明：collect 与守卫必须用同一个排除清单，否则自指。"""
    import scripts.collect_metrics as cm

    assert "tests/test_metrics_consistency.py" in cm._COUNT_EXCLUDE


def test_metrics_json_exists():
    data = _metrics_or_skip()
    assert data["pytest_passed"] > 0


def test_no_stale_test_counts_in_submission_materials():
    expected = _metrics_or_skip()["pytest_passed"]
    offenders = []
    for rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in PASSED_RE.finditer(line):
                n = int(m.group(1))
                if n != expected:
                    offenders.append(f"{rel}:{i} 写成 {n}，实际 {expected}")
    assert not offenders, "数字漂移：\n" + "\n".join(offenders)


def test_historical_snapshots_are_not_rewritten():
    """历史快照不该被 sync 改写成今天的数字——那等于篡改记录。"""
    import scripts.sync_metrics as sm

    hist = {"docs/standup/20261020.md",
            "docs/W2_注入编码防御加固_执行说明_20261020.md",
            "docs/W1_跨场景闭环_执行说明_20261020.md"}
    assert hist.issubset(sm.HISTORICAL), "sync_metrics 的历史豁免清单被改动，需同步本测试"
    assert not (hist & set(sm.TARGETS)), "历史快照不允许出现在 sync 目标里"
