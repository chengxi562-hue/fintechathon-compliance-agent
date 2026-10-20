"""把所有「对外引用的数字」集中到一处，由脚本实跑生成，再注入文档。

起因（2026-10-20）：单测数字在 8 个文件里手写，先后出现过 128 / 131 / 132 / 135
四种互相矛盾的版本。每次加测试都要手工改十几处，必然漏。

做法：能跑出来的数字就实跑，跑不出来的（如人工确认状态）显式标"待确认"。
输出 data/evals/_metrics.json，再由 scripts/sync_metrics.py 注入文档。

用法：PYTHONPATH=. .venv/bin/python scripts/collect_metrics.py
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "evals" / "_metrics.json"


# 取数时排除守卫自身：
# test_metrics_consistency 会读取 _metrics.json 做比对，若把它也算进总数，
# 就会出现「收集→数字变→守卫发现不一致→再收集」的自指循环。
# 口径固定为「除本守卫外的全部测试」，collect 与守卫共用同一口径。
_COUNT_EXCLUDE = [
    "tests/test_metrics_consistency.py",
]


def _pytest_passed() -> int:
    """解析 pytest 汇总行，取真实通过数（不靠猜、不靠手填）。"""
    args = [sys.executable, "-m", "pytest", "-q", "--tb=no"]
    for path in _COUNT_EXCLUDE:
        args += ["--ignore", path]
    r = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    m = re.search(r"(\d+) passed", r.stdout)
    if not m:
        raise RuntimeError(f"pytest 汇总行解析失败：{r.stdout[-800:]}")
    return int(m.group(1))


def _eval_metrics() -> dict:
    path = ROOT / "data" / "evals" / "eval_v1_results.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    c = Counter(r["status"] for r in rows)
    block = [r for r in rows if r["expected_decision"] == "block"]
    allow = [r for r in rows if r["expected_decision"] == "allow"]
    block_ok = sum(1 for r in block if r["status"] == "P")
    allow_fail = sum(1 for r in allow if r["status"] == "F")
    inj_keys = ("注入", "越狱", "编码", "伪造", "角色", "偏好", "同义", "话术规避")
    inj = [r for r in block if any(k in r["attack_type"] for k in inj_keys)]
    inj_escape = sum(1 for r in inj if r["actual_decision"] == "allow")
    return {
        "total": len(rows),
        "pass": c["P"],
        "fail": c["F"],
        "skip": c["SKIP"],
        "pass_rate": round(c["P"] / len(rows) * 100, 1),
        "block_total": len(block),
        "block_pass": block_ok,
        "block_rate": round(block_ok / len(block) * 100, 1),
        "allow_total": len(allow),
        "allow_fail": allow_fail,
        "false_block_rate": round(allow_fail / len(allow) * 100, 1),
        "inject_total": len(inj),
        "inject_escape": inj_escape,
        "inject_escape_rate": round(inj_escape / len(inj) * 100, 1),
    }


def _adv_metrics() -> dict:
    md = (ROOT / "docs" / "对抗评测集_v0_20261018.md").read_text(encoding="utf-8")
    expect: dict[str, str] = {}
    for line in md.splitlines():
        m = re.match(r"^\|\s*([A-Z]\d\d)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|", line)
        if not m:
            continue
        e = m.group(4).strip().lower()
        v = "block" if e.startswith("block") else ("allow" if e.startswith("allow") else None)
        if v:
            expect[m.group(1)] = v
    probe = {r["id"]: r for r in json.loads(
        (ROOT / "data" / "evals" / "_probe_adv_v0.json").read_text(encoding="utf-8"))}
    have = [(k, v) for k, v in expect.items() if k in probe]
    ok = sum(1 for k, v in have if probe[k]["decision"] == v)
    return {"total": len(have), "pass": ok, "fail": len(have) - ok,
            "rate": round(ok / len(have) * 100, 1)}


def _baseline() -> dict:
    p = ROOT / "data" / "evals" / "_baseline_no_gates.json"
    return json.loads(p.read_text(encoding="utf-8"))["summary"]


def main() -> int:
    data = {
        "pytest_passed": _pytest_passed(),
        "eval_v1": _eval_metrics(),
        "adversarial": _adv_metrics(),
        "baseline_no_gates": _baseline(),
        "submission_files": {
            "technical_doc_pdf": "submit/01_项目说明书_v1.pdf",
            "defense_ppt": "submit/02_答辩材料_v1.pptx",
            "source_zip": "submit/03_源代码与部署_v1.zip",
            "security_report": "submit/04_安全自评报告_v1.docx",
            "demo_video": "submit/05_演示视频_v0.mp4",
        },
        "manual_pending": {
            "yiling_signoff": "未签（需本人）",
            "platform_upload": "未上传（需登录）",
        },
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
