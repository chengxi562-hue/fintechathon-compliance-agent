"""延迟基准脚本要能跑，且结论不能假。

这个脚本的数字会被写进技术文档和路演材料。如果它坏了还输出好看的数，
比没有更糟。这里的守卫很便宜：只跑小样本，检查 schema 与量级。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "evals" / "_bench_latency.json"


def test_bench_runs_and_numbers_are_plausible():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "bench_latency.py"), "--n", "5"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    assert r.returncode == 0, r.stderr[-2000:]
    data = json.loads(OUT.read_text(encoding="utf-8"))
    s = data["summary"]

    assert s["n_total"] == 20  # 4 cases x 5
    # 规则门应当是毫秒级：低于 0.1ms 说明根本没跑，高于 5s 说明哪里卡住了
    assert 0.1 < s["mean_ms"] < 5000, s
    assert s["p95_ms"] >= s["mean_ms"] * 0.5, s
    assert s["note"], "口径说明不能为空"
    assert len(data["per_case"]) == 4
