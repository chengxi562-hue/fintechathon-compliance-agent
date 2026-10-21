"""把 data/evals/_metrics.json 的数字注入各文档，消灭手写漂移。

用途：`python scripts/collect_metrics.py && python scripts/sync_metrics.py`
      → 所有材料里的「135 passed」「97.1%」等由脚本统一改写。

设计取舍：
- 只替换**已知的、确定性的**数字模式，不做模糊匹配（避免误伤历史记录）。
- 历史快照类文件（standup、W1/W2 执行说明）**不动**：它们记录的是当时的真实状态，
  改掉等于篡改历史。这是有意的例外，不是遗漏。
- 幂等：多次运行结果一致。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "data" / "evals" / "_metrics.json"


def load_metrics() -> dict:
    """惰性读取：模块导入时不得要求 _metrics.json 存在。

    _metrics.json 是实跑快照（仓库里有一份，便于克隆后直接核对）。如果顶层就读，
    任何 import 这个模块的代码（包括测试）在没有该文件时都会直接崩——
    2026-10-20 实测：评委解压提交包后直接 pytest，会有 3 条测试因此失败。
    """
    if not METRICS_PATH.exists():
        raise FileNotFoundError(
            f"缺少 {METRICS_PATH.relative_to(ROOT)}；先跑 "
            f"`PYTHONPATH=. python scripts/collect_metrics.py` 生成。"
        )
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))



# 模块级占位；真实值在 main() 里由 load_metrics() 填充。
# 不在顶层读文件：导入时不强制已经有快照，
# 顶层读会让任何 import（含测试）在无该文件时崩掉。
PY = PY_FULL = EV = ADV = BL = None

# 历史快照：只记录当时状态，不随数字变化而改写
HISTORICAL = {
    "docs/standup/20261020.md",
    "docs/W2_注入编码防御加固_执行说明_20261020.md",
    "docs/W1_跨场景闭环_执行说明_20261020.md",
}

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

# 任何「N passed」统一成当前真实数（排除历史快照文件）
PASSED_RE = re.compile(r"\b(\d{2,4})\s*passed\b")


def sync_file(rel: str) -> int:
    p = ROOT / rel
    if not p.exists():
        print(f"  ! 缺失 {rel}")
        return 0
    s = orig = p.read_text(encoding="utf-8")

    # 对外材料引用「全量」通过数（含守卫），这是观众看到的口径
    s = PASSED_RE.sub(lambda m: f"{PY_FULL} passed", s)

    # 评测集汇总（只在明确写「P…/F…」的地方改，模式稳定）
    s = re.sub(r"P\s*\d{2,3}\s*/\s*F\s*\d{1,3}\s*/\s*SKIP\s*\d",
               f"P{EV['pass']} / F{EV['fail']} / SKIP{EV['skip']}", s)
    s = re.sub(r"\*\*P(\d{2,3})\s*/\s*F(\d{1,3})\s*/\s*SKIP(\d)\*\*",
               f"**P{EV['pass']} / F{EV['fail']} / SKIP{EV['skip']}**", s)

    # 对抗集（格式：108/111）
    s = re.sub(r"\b\d{2,3}\s*/\s*111\b", f"{ADV['pass']}/{ADV['total']}", s)
    # 对抗集（格式：108 通过 / 3 未通过）
    s = s.replace("108 通过", f"{ADV['pass']} 通过").replace("3 未通过", f"{ADV['fail']} 未通过")

    # 基线对照
    s = s.replace("43.9%", f"{BL['naive_rate']}%").replace("98.2%", f"{BL['gated_rate']}%")

    # 「N 条测试」这类汉字数词也要跟着走，否则 row 内部会自相矛盾
    s = re.sub(r"\b\d{2,4}\s*条测试\b", f"{PY_FULL} 条测试", s)

    if s != orig:
        p.write_text(s, encoding="utf-8")
        return sum(1 for a, b in zip(orig.splitlines(), s.splitlines()) if a != b)
    return 0


def main() -> int:
    global M, PY, PY_FULL, EV, ADV, BL
    M = load_metrics()
    PY = str(M["pytest_passed"])
    PY_FULL = str(M["pytest_total_passed"])
    EV = M["eval_v1"]
    ADV = M["adversarial"]
    BL = M["baseline_no_gates"]
    print(f"目标数字：pytest(对外)={PY_FULL} pytest(内部比对)={PY} 评测集={EV['pass']}/{EV['total']} "
          f"对抗集={ADV['pass']}/{ADV['total']} 基线={BL['gated_rate']}% vs {BL['naive_rate']}%")
    total = 0
    for rel in TARGETS:
        n = sync_file(rel)
        total += n
        print(f"  {'改了 %d 处' % n if n else '无变化  '} {rel}")
    print(f"\n合计改动 {total} 行")
    print("\n历史快照（有意不改）：")
    for h in sorted(HISTORICAL):
        print(f"  - {h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
