# 交付件构建脚本

答辩 PPT / 技术文档 / 安全自评的生成源码。`submit/_build/` 是这些脚本的运行时目录，
但它被 .gitignore 排除（成品二进制不随源码包分发）——所以源码在这里留一份，保证可复现。

| 文件 | 产出 | 依赖 |
|---|---|---|
| `deck.js` | `submit/02_答辩材料_v2.pptx`（10 页） | `pptxgenjs` |
| `build_tech_doc.py` | `submit/01_技术文档_v1.docx` | `python-docx` |
| `build_security_report.py` | `submit/04_安全自评报告_v1.docx` | `python-docx` |

```bash
# 答辩 PPT
cd build_decks && NODE_PATH="$(npm root -g)" node deck.js

# 技术文档 / 安全自评（需先激活含 python-docx 的环境）
python build_decks/build_tech_doc.py
python build_decks/build_security_report.py
```

**字体注意**：deck.js 用 `Noto Sans CJK SC`，因为平台服务器渲染环境装的是这个字体。
本机（macOS）没有它，本地预览会掉字，但评委看到的是正确渲染。
