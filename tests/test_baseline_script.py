"""基线对照脚本必须能跑、且结论方向不能反。

`scripts/baseline_no_gates.py` 是评委最可能亲自复跑的那个脚本（它回答「加门到底有没有用」）。
如果它坏了或结论反了，比没有更糟。这里用少量行数做一个便宜的守卫：
真正跑一遍脚本，检查它输出的汇总 JSON 里「有门 > 无门」。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "evals" / "_baseline_no_gates.json"


def test_baseline_script_runs_and_gates_win():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "baseline_no_gates.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=600,
        env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    assert r.returncode == 0, r.stderr[-2000:]
    assert OUT.exists(), "脚本没有写出汇总 JSON"

    data = json.loads(OUT.read_text(encoding="utf-8"))
    s = data["summary"]
    assert s["scored"] > 100
    assert s["gated_pass"] > s["naive_pass"], (
        f'加了合规门反而更差：有门 {s["gated_pass"]} vs 无门 {s["naive_pass"]}'
    )
    # 有门组应接近满分（当前 168/171），显著偏离说明回归了
    assert s["gated_rate"] >= 90.0, s
