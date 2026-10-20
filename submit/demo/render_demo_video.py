#!/usr/bin/env python3
"""Render FinTechathon demo MP4 from HTML keyframes + ffmpeg."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
HTML = ROOT.resolve() / "index.html"
OUT_MP4 = ROOT.parent / "05_演示视频_v0.mp4"
OUT_MD = ROOT.parent / "05_演示视频说明.md"

# Keyframes: (filename, ?kf=, duration_seconds)
# Total target ~112s matching 分镜
KEYFRAMES = [
    ("01_s1.png", "s1", 8),
    ("02_s2a.png", "s2a", 5),
    ("03_s2b.png", "s2b", 13),
    ("04_s3a.png", "s3a", 5),
    ("05_s3b.png", "s3b", 15),
    ("06_s4a.png", "s4a", 4),
    ("07_s4b.png", "s4b", 12),
    ("08_s5a.png", "s5a", 4),
    ("09_s5b.png", "s5b", 5),
    ("10_s5c.png", "s5c", 4),
    ("11_s5d.png", "s5d", 7),
    ("12_s6a.png", "s6a", 4),
    ("13_s6b.png", "s6b", 10),
    ("14_s7.png", "s7", 10),
    ("15_s8.png", "s8", 6),
]
# 8+5+13+5+15+4+12+4+5+4+7+4+10+10+6 = 112


def chrome_shot(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # macOS Chrome 不在 PATH；优先用本机绝对路径，其次 CHROME 环境变量
    chrome = os.environ.get("CHROME") or (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome").exists()
        else "google-chrome"
    )
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--window-size=1920,1080",
        f"--screenshot={out}",
        "--virtual-time-budget=3000",
        "--run-all-compositor-stages-before-draw",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        url,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if not out.exists() or out.stat().st_size < 1000:
        print(r.stdout, r.stderr, file=sys.stderr)
        raise RuntimeError(f"screenshot failed: {out}")


def capture_all() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    base = HTML.as_uri()
    for name, kf, _dur in KEYFRAMES:
        url = f"{base}?kf={kf}"
        out = FRAMES / name
        print(f"capture {name} <- {kf}")
        chrome_shot(url, out)


def write_concat(list_path: Path) -> float:
    total = 0.0
    lines = []
    for name, _kf, dur in KEYFRAMES:
        p = FRAMES / name
        # 写相对路径：concat 清单会进公开仓库，绝不能带本机绝对路径
        lines.append(f"file '{p.name}'")
        lines.append(f"duration {dur}")
        total += dur
    # last file must be repeated without duration for concat demuxer
    last = FRAMES / KEYFRAMES[-1][0]
    lines.append(f"file '{last.name}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return total


def encode(list_path: Path, total: float) -> None:
    # Still image slideshow -> H.264 yuv420p
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path.relative_to(ROOT)),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart",
        "-t", str(total),
        str(OUT_MP4),
    ]
    print(" ".join(cmd))
    # concat 清单里是相对路径，必须在 demo 目录下执行 ffmpeg
    subprocess.run(cmd, check=True, cwd=ROOT)


def write_readme(total: float, size_mb: float) -> None:
    md = f"""# 05 演示视频说明

> 生成时间：2026-10-20 21:15｜来源：`docs/Demo分镜_一页纸_20261018.md` + `data/evals/_replay_demo.jsonl`

## 文件

| 项 | 值 |
|---|---|
| 视频 | `submit/05_演示视频_v0.mp4` |
| 时长 | **{total:.0f} 秒**（目标 112s） |
| 画幅 | 1920×1080 横屏 H.264 |
| 体积 | **{size_mb:.1f} MB**（平台上限 500MB） |
| 旁白 | 烧录字幕（无真人出镜） |
| 交互页 | `submit/demo/index.html`（`?kf=s2b` / `?freeze=2` / `?auto=1`） |

## 内容对齐

- 镜 2–6 输入句与审计面板内容**全部由当前代码实跑生成**（`run_agent` 逐条真跑，不是手写），2026-10-20 W2 重渲染。
- 镜 5 第二句（注入）：**注入门当场命中 `INJECT_DETECTED`**（上一版该句由金额门兜住、注入门未命中，W2 已修复；旁白如实说明「上一版这里漏了，今天补上了」）。
- 镜 4：旁白说「审计记了转账检查，金额在工具调用里」，不说「审计记了 100 元」。
- 镜 6：「风控已经批了」不构成系统权限，仍走软限/确认门。
- 镜 8：主动交底编码归一 / 中文品名 / 注入门；不编造拦截率。
- 全程角标：**Mock 数据 · 不接真实资金**。

## 合成方式

1. HTML 关键帧（Chrome headless 截图）
2. `ffmpeg` concat + libx264

复跑：

```bash
cd <repo-root>/submit/demo
python3 render_demo_video.py
```

## 上传

平台可选栏「演示视频」；由 computerUse 代传本文件绝对路径即可。
"""
    OUT_MD.write_text(md, encoding="utf-8")


def main() -> None:
    capture_all()
    list_path = FRAMES / "concat.txt"
    total = write_concat(list_path)
    encode(list_path, total)
    size_mb = OUT_MP4.stat().st_size / (1024 * 1024)
    # probe duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(OUT_MP4)],
        capture_output=True, text=True, check=True,
    )
    dur = float(json.loads(probe.stdout)["format"]["duration"])
    write_readme(dur, size_mb)
    print(f"OK mp4={OUT_MP4} duration={dur:.1f}s size={size_mb:.2f}MB")
    if dur < 90:
        raise SystemExit("duration < 90s")
    if size_mb > 500:
        raise SystemExit("file > 500MB")


if __name__ == "__main__":
    main()
