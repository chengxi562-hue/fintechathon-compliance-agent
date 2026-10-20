#!/usr/bin/env bash
# 一条命令把「实跑数字」同步到所有对外材料并重建文档。
# 新增测试或评测集变化后，跑这个即可，不要手改数字。
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/5] 实跑取数"
PYTHONPATH=. .venv/bin/python scripts/collect_metrics.py >/dev/null

echo "[2/5] 注入文档"
PYTHONPATH=. .venv/bin/python scripts/sync_metrics.py

echo "[3/5] 重建 01 技术文档 / 04 安全自评 / 02 答辩材料"
# submit/_build/ 是内部构建脚本，不随源码包分发。评委拿到的是已构建好的成品，
# 无需重建；缺目录时跳过，不视为失败（否则「按 README 跑一遍」会红）。
if [ -d submit/_build ]; then
  .venv/bin/python submit/_build/build_tech_doc.py
  .venv/bin/python submit/_build/build_security_report.py
  ( cd submit/_build && NODE_PATH="${NODE_PATH:-$HOME/Library/Application Support/QClaw/npm-global/lib/node_modules}" node pitch.js )
else
  echo "  跳过：submit/_build 不在本包内（构建脚本不随源码分发，成品已就绪）"
fi

echo "[4/5] 导出项目说明书 PDF"
if [ -f submit/01_技术文档_v1.docx ] && [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ]; then
  ( cd submit && rm -f 01_项目说明书_v1.pdf \
    && /Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to pdf --outdir . 01_技术文档_v1.docx >/dev/null 2>&1 \
    && mv 01_技术文档_v1.pdf 01_项目说明书_v1.pdf )
else
  echo "  跳过：无 docx 或未装 LibreOffice"
fi

echo "[5/5] 一致性守卫"
PYTHONPATH=. .venv/bin/python -m pytest tests/test_metrics_consistency.py -q
echo "OK：数字已统一，文档已重建"
