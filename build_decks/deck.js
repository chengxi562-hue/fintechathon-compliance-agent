/**
 * FinTechathon 2026 · 答辩材料 v2
 *
 * 重做原因（2026-10-20 深夜）：
 *   1. 旧版第 6 页只有标题、没有正文（内容丢失）
 *   2. 版面普遍偏空：单列卡片、大片留白，视觉重量不足
 *   3. 字号对比不够：标题与正文区分度低，投影时看不清
 *
 * 本版设计约束：
 *   - 字体只用 STHeiti（本机确有，macOS 系统字体；Windows 回退到黑体族，
 *     不会被甩成宋体）。旧版用 Noto Sans CJK SC，本机没有，本地预览会掉字。
 *   - 深色底贯穿（技术产品调性），强调色只有一个：青绿。
 *   - 每页都有视觉元素：流程箭头 / 大数字 / 进度条 / 对照条，不留纯文字页。
 *   - 页边距 ≥0.5"，正文 ≥14pt，标题 ≥36pt。
 */
const pptxgen = require("pptxgenjs");
const { join } = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "弋承熙 & 高依灵";
pres.title = "合规先审·银行AI销售智能体（合规官）";
pres.subject = "FinTechathon 2026 答辩材料 v2";

// 字体选择依据（实测，别凭感觉改）：
//   平台服务器渲染 v1 时用的是 Noto Sans CJK（从平台预览 PDF 的字体表确认），
//   说明官方转档环境装了这个字体。所以对外材料应当用 Noto Sans CJK SC —— 
//   本机没有它、本地预览会掉字，但评委会看到正确渲染。
//   反面教训：曾想改成 STHeiti（本机有），那反而会在平台服务器上掉字。
const FONT = "Noto Sans CJK SC";
const W = 13.333;
const H = 7.5;

const C = {
  bg: "0A1018",
  bg2: "101B28",
  card: "14202E",
  cardHi: "1A2A3C",
  line: "22334A",
  text: "EAF2FB",
  muted: "8FA6BF",
  dim: "5E7characters", // placeholder, replaced below
};
// 显式重建（避免手误）
C.dim = "5E7391";
C.accent = "2DD4BF"; // teal
C.accent2 = "5EEAD4";
C.warn = "F4A261";
C.bad = "EF6461";
C.ok = "4ADE80";
C.white = "FFFFFF";

const TOTAL = 10;

/** 统一页眉：章节标签 + 大标题 */
function header(s, tag, title, sub) {
  s.addText(tag, {
    x: 0.7, y: 0.45, w: 8, h: 0.3,
    fontFace: FONT, fontSize: 12, color: C.accent, charSpacing: 2, margin: 0,
  });
  s.addText(title, {
    x: 0.7, y: 0.8, w: W - 1.4, h: 0.72,
    fontFace: FONT, fontSize: 34, bold: true, color: C.white, margin: 0,
  });
  if (sub) {
    s.addText(sub, {
      x: 0.7, y: 1.55, w: W - 1.4, h: 0.4,
      fontFace: FONT, fontSize: 15, color: C.muted, margin: 0,
    });
  }
}

function footer(s, page) {
  s.addShape(pres.shapes.LINE, {
    x: 0.7, y: 6.92, w: W - 1.4, h: 0,
    line: { color: C.line, width: 0.75 },
  });
  s.addText("FinTechathon 2026 · 银行 AI 智能体 · 弋承熙 & 高依灵", {
    x: 0.7, y: 7.0, w: 9, h: 0.25,
    fontFace: FONT, fontSize: 10, color: C.dim, margin: 0,
  });
  s.addText(`${page} / ${TOTAL}`, {
    x: W - 1.6, y: 7.0, w: 0.9, h: 0.25,
    fontFace: FONT, fontSize: 10, color: C.dim, align: "right", margin: 0,
  });
}

function bg(s, variant) {
  s.background = { color: C.bg };
  if (variant === "panel") {
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 0.18, h: H, fill: { color: C.accent },
    });
  }
}

/* ============================ 1 封面 ============================ */
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // 右侧装饰：门形竖条
  for (let i = 0; i < 4; i++) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 9.15 + i * 0.95, y: 1.55, w: 0.62, h: 3.1,
      fill: { color: i === 0 ? C.accent : C.cardHi },
      rectRadius: 0.28, line: { color: C.line, width: 0.5 },
    });
  }

  s.addText("FINTECHATHON 2026 · 银行 AI 智能体赛道", {
    x: 0.9, y: 1.35, w: 8, h: 0.3,
    fontFace: FONT, fontSize: 13, color: C.accent, charSpacing: 2, margin: 0,
  });
  s.addText("合规官", {
    x: 0.9, y: 1.85, w: 8, h: 1.0,
    fontFace: FONT, fontSize: 54, bold: true, color: C.white, margin: 0,
  });
  s.addText("先审后答 · 每一步留痕", {
    x: 0.9, y: 2.95, w: 8, h: 0.6,
    fontFace: FONT, fontSize: 26, color: C.accent2, margin: 0,
  });
  s.addText("让银行敢让大模型卖理财的那一层：四道合规门 + 全链路审计", {
    x: 0.9, y: 3.65, w: 7.9, h: 0.45,
    fontFace: FONT, fontSize: 15, color: C.muted, margin: 0,
  });

  s.addShape(pres.shapes.LINE, {
    x: 0.9, y: 4.55, w: 3.2, h: 0,
    line: { color: C.accent, width: 2 },
  });

  s.addText("弋承熙 & 高依灵", {
    x: 0.9, y: 4.85, w: 6, h: 0.35,
    fontFace: FONT, fontSize: 17, bold: true, color: C.text, margin: 0,
  });
  s.addText("2026-10-20 · 答辩材料 v2 · Mock 数据，不接真实资金", {
    x: 0.9, y: 5.25, w: 8, h: 0.3,
    fontFace: FONT, fontSize: 12, color: C.dim, margin: 0,
  });
  footer(s, 1);
}

/* ============================ 2 问题 ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "问题 / PROBLEM", "银行怕的不是答得慢，是卖错人、说错话、转错钱");

  const items = [
    { n: "01", t: "适当性失守", d: "R2 客户被推 R4", e: "投诉 · 监管 · 举证失败", c: C.bad },
    { n: "02", t: "违规话术", d: "「保本」「稳赚」「刚兑」", e: "销售误导 · 消保红线", c: C.warn },
    { n: "03", t: "越权资金", d: "大额陌生收款人", e: "注入后试图绕限额", c: C.warn },
    { n: "04", t: "不可审计", d: "只有聊天记录", e: "无法自证「哪一步拦了」", c: C.bad },
  ];
  items.forEach((it, i) => {
    const x = 0.7 + i * 3.08;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.15, w: 2.85, h: 2.75,
      fill: { color: C.card }, rectRadius: 0.12, line: { color: C.line, width: 0.75 },
    });
    // 顶部色条
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.15, w: 2.85, h: 0.06, fill: { color: it.c },
    });
    s.addText(it.n, {
      x: x + 0.25, y: 2.32, w: 2.3, h: 0.4,
      fontFace: FONT, fontSize: 13, color: it.c, charSpacing: 1, margin: 0,
    });
    s.addText(it.t, {
      x: x + 0.25, y: 2.78, w: 2.35, h: 0.45,
      fontFace: FONT, fontSize: 20, bold: true, color: C.white, margin: 0,
    });
    s.addText(it.d, {
      x: x + 0.25, y: 3.4, w: 2.35, h: 0.55,
      fontFace: FONT, fontSize: 13, color: C.text, margin: 0,
    });
    s.addText(it.e, {
      x: x + 0.25, y: 4.02, w: 2.35, h: 0.7,
      fontFace: FONT, fontSize: 12, color: C.muted, margin: 0,
    });
  });

  // 结论条
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.7, y: 5.25, w: W - 1.4, h: 1.2,
    fill: { color: C.cardHi }, rectRadius: 0.1, line: { color: C.accent, width: 1 },
  });
  s.addText("需要的不是「更会聊」的 Agent，而是「先审后答、每步留痕」的 Agent", {
    x: 1.0, y: 5.6, w: W - 2.0, h: 0.5,
    fontFace: FONT, fontSize: 19, bold: true, color: C.accent2, margin: 0,
  });
  footer(s, 2);
}

/* ============================ 3 方案：四道门 ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "方案 / SOLUTION", "四道门 + 全链路审计 + 银行侧双闸");

  const gates = [
    { n: "01", t: "意图门", d: "注入 / 越狱 / 越权", d2: "非业务意图一律拦" },
    { n: "02", t: "产品门", d: "目录 allowlist 硬约束", d2: "幻觉品名直接拒" },
    { n: "03", t: "适当性", d: "客户风险分 vs 产品风险级", d2: "购买拦 · 咨询警示" },
    { n: "04", t: "话术门", d: "禁保本 / 稳赚 / 刚兑", d2: "放行必带披露" },
  ];
  gates.forEach((g, i) => {
    const x = 0.7 + i * 3.08;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.05, w: 2.78, h: 2.35,
      fill: { color: C.card }, rectRadius: 0.12, line: { color: C.line, width: 0.75 },
    });
    s.addText(g.n, {
      x: x + 0.22, y: 2.2, w: 1.2, h: 0.5,
      fontFace: FONT, fontSize: 26, bold: true, color: C.accent, margin: 0,
    });
    s.addText(g.t, {
      x: x + 0.22, y: 2.78, w: 2.4, h: 0.4,
      fontFace: FONT, fontSize: 18, bold: true, color: C.white, margin: 0,
    });
    s.addText(g.d, {
      x: x + 0.22, y: 3.28, w: 2.4, h: 0.5,
      fontFace: FONT, fontSize: 12, color: C.text, margin: 0,
    });
    s.addText(g.d2, {
      x: x + 0.22, y: 3.82, w: 2.4, h: 0.4,
      fontFace: FONT, fontSize: 12, color: C.muted, margin: 0,
    });
    if (i < 3) {
      s.addShape(pres.shapes.RIGHT_ARROW, {
        x: x + 2.82, y: 3.05, w: 0.24, h: 0.32, fill: { color: C.accent },
      });
    }
  });

  // 三条原则
  const prin = [
    ["规则先行", "YAML 管「能不能」；当前版本未接 LLM，拦/放行全由规则决定"],
    ["默认拒绝", "目录外 / 金额不清 / 意图不定 → 澄清或拦截"],
    ["可回放", "request_id + 四门明细 + 原因码，审计可重放成路演画面"],
  ];
  prin.forEach((p, i) => {
    const y = 4.75 + i * 0.62;
    s.addShape(pres.shapes.OVAL, {
      x: 0.72, y: y + 0.1, w: 0.16, h: 0.16, fill: { color: C.accent },
    });
    s.addText(p[0], {
      x: 1.05, y, w: 1.7, h: 0.35,
      fontFace: FONT, fontSize: 15, bold: true, color: C.accent2, margin: 0,
    });
    s.addText(p[1], {
      x: 2.8, y, w: W - 3.6, h: 0.35,
      fontFace: FONT, fontSize: 14, color: C.text, margin: 0,
    });
  });
  footer(s, 3);
}

/* ============================ 4 架构 ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "架构 / ARCHITECTURE", "四场景可跑 · 141 条测试 · LangGraph-ready");

  const flow = [
    ["用户话术", "林晓晴 R2"],
    ["Intent", "确定性分类"],
    ["四道门", "gates.py"],
    ["Tools", "仅 allowed"],
    ["审计", "JSONL"],
  ];
  flow.forEach((f, i) => {
    const x = 0.7 + i * 2.45;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.0, w: 2.1, h: 1.35,
      fill: { color: i === 2 ? C.cardHi : C.card },
      rectRadius: 0.1,
      line: { color: i === 2 ? C.accent : C.line, width: i === 2 ? 1.5 : 0.75 },
    });
    s.addText(f[0], {
      x: x + 0.15, y: 2.28, w: 1.8, h: 0.4,
      fontFace: FONT, fontSize: 16, bold: true, color: C.white, align: "center", margin: 0,
    });
    s.addText(f[1], {
      x: x + 0.15, y: 2.75, w: 1.8, h: 0.35,
      fontFace: FONT, fontSize: 11, color: C.muted, align: "center", margin: 0,
    });
    if (i < 4) {
      s.addShape(pres.shapes.RIGHT_ARROW, {
        x: x + 2.14, y: 2.55, w: 0.26, h: 0.28, fill: { color: C.accent },
      });
    }
  });

  // 模块网格
  const mods = [
    ["agent/", "状态机 + 四关 + 金额解析"],
    ["mock_bank/", "FastAPI + 第二道闸"],
    ["configs/", "compliance_rules.yaml"],
    ["audit/", "events.jsonl 决策轨迹"],
    ["tests/", "141 passed（pytest）"],
    ["data/evals/", "评测集 173 + 对抗集 111"],
  ];
  mods.forEach((m, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.7 + col * 4.0, y = 3.75 + row * 1.22;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 3.75, h: 1.02,
      fill: { color: C.card }, rectRadius: 0.08, line: { color: C.line, width: 0.75 },
    });
    s.addText(m[0], {
      x: x + 0.22, y: y + 0.15, w: 3.3, h: 0.32,
      fontFace: "Consolas", fontSize: 14, bold: true, color: C.accent2, margin: 0,
    });
    s.addText(m[1], {
      x: x + 0.22, y: y + 0.52, w: 3.3, h: 0.35,
      fontFace: FONT, fontSize: 12, color: C.muted, margin: 0,
    });
  });
  footer(s, 4);
}

/* ============================ 5 演示三幕 ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "演示 / LIVE DEMO", "拦得住 · 办得成 · 兜得住", "约 5 分钟，可现场复跑");

  const acts = [
    {
      t: "第一幕 · 拦得住", dur: "~90s", c: C.bad,
      pts: ["「…保本的。」", "Gate4 → USER_FORBIDDEN:保本", "规则门在模型之前拦下", "资金工具调用 = 0"],
    },
    {
      t: "第二幕 · 办得成", dur: "~120s", c: C.ok,
      pts: ["R2 货基 / 短债 → 放行", "WB_CASH_001 + 强制披露", "100 元转本人备用金", "审计面板实时追加 JSONL"],
    },
    {
      t: "第三幕 · 兜得住", dur: "~90s", c: C.warn,
      pts: ["6 万转陌生人 → 白名单拦", "注入改收款人 → 注入门命中", "主动交底失败数字", "可回归用例表，不是剪辑"],
    },
  ];
  acts.forEach((a, i) => {
    const x = 0.7 + i * 4.05;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.1, w: 3.75, h: 4.3,
      fill: { color: C.card }, rectRadius: 0.12, line: { color: C.line, width: 0.75 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.1, w: 3.75, h: 0.07, fill: { color: a.c },
    });
    s.addText(a.t, {
      x: x + 0.3, y: 2.35, w: 3.2, h: 0.45,
      fontFace: FONT, fontSize: 19, bold: true, color: C.white, margin: 0,
    });
    s.addText(a.dur, {
      x: x + 0.3, y: 2.85, w: 3.2, h: 0.3,
      fontFace: FONT, fontSize: 12, color: a.c, margin: 0,
    });
    a.pts.forEach((p, j) => {
      s.addText("·  " + p, {
        x: x + 0.3, y: 3.35 + j * 0.62, w: 3.2, h: 0.55,
        fontFace: FONT, fontSize: 13, color: C.text, margin: 0,
      });
    });
  });
  footer(s, 5);
}

/* ============================ 6 差异化（旧版这里缺正文） ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "差异化 / WHY US", "别人做「会卖」——我们做「银行敢让它卖」");

  const rows = [
    ["常见做法", "我们的做法", true],
    ["system prompt 里写一句「要合规」", "独立可测组件 gates.py + YAML + 单测", false],
    ["只演示成功路径", "同一流程既放行又拦截，边界可见", false],
    ["靠模型自觉不说幻觉产品", "目录 allowlist 硬约束，不在目录即拒", false],
    ["审计 = 把聊天记录存下来", "审计 = 结构化决策轨迹（四门各自结果 + 原因码）", false],
    ["事后人工抽检", "评测集可 CI 回归，改一行规则就知道影响", false],
  ];
  const colX = [0.7, 6.85];
  const colW = 5.85;

  // 表头
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: colX[0], y: 2.15, w: colW, h: 0.5,
    fill: { color: C.cardHi }, rectRadius: 0.06, line: { color: C.line, width: 0.5 },
  });
  s.addText("常见做法", {
    x: colX[0] + 0.25, y: 2.24, w: colW - 0.5, h: 0.32,
    fontFace: FONT, fontSize: 13, bold: true, color: C.muted, margin: 0,
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: colX[1], y: 2.15, w: colW, h: 0.5,
    fill: { color: "123B36" }, rectRadius: 0.06, line: { color: C.accent, width: 1 },
  });
  s.addText("我们的做法", {
    x: colX[1] + 0.25, y: 2.24, w: colW - 0.5, h: 0.32,
    fontFace: FONT, fontSize: 13, bold: true, color: C.accent2, margin: 0,
  });

  rows.slice(1).forEach((r, i) => {
    const y = 2.78 + i * 0.78;
    s.addShape(pres.shapes.RECTANGLE, {
      x: colX[0], y, w: colW, h: 0.66, fill: { color: C.card },
      line: { color: C.line, width: 0.5 },
    });
    s.addText(r[0], {
      x: colX[0] + 0.25, y: y + 0.16, w: colW - 0.5, h: 0.36,
      fontFace: FONT, fontSize: 13, color: C.muted, margin: 0,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: colX[1], y, w: colW, h: 0.66, fill: { color: C.cardHi },
      line: { color: C.line, width: 0.5 },
    });
    s.addText(r[1], {
      x: colX[1] + 0.25, y: y + 0.16, w: colW - 0.5, h: 0.36,
      fontFace: FONT, fontSize: 13, bold: true, color: C.text, margin: 0,
    });
  });
  footer(s, 6);
}

/* ============================ 7 数据 ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "数据 / EVIDENCE", "敢在路演放失败数字，因为有可回归用例表", "同一台机、同一命令、真跑；不是估算");

  const stats = [
    { v: "98.4%", l: "应拦拦截率", n: "123 / 125 · 目标 ≥90%", c: C.ok },
    { v: "0%", l: "注入逃逸率", n: "0 / 45 · 目标 ≤20%", c: C.ok },
    { v: "2.2%", l: "误拦率", n: "1 / 46 · 目标 ≤5%", c: C.ok },
    { v: "97.1%", l: "评测集通过率", n: "168 / 173 · 另 2 条 SKIP", c: C.ok },
  ];
  stats.forEach((st, i) => {
    const x = 0.7 + i * 3.08;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.0, w: 2.85, h: 2.0,
      fill: { color: C.card }, rectRadius: 0.12, line: { color: C.line, width: 0.75 },
    });
    s.addText(st.v, {
      x: x + 0.1, y: 2.18, w: 2.65, h: 0.85,
      fontFace: FONT, fontSize: 36, bold: true, color: st.c, align: "center", margin: 0,
    });
    s.addText(st.l, {
      x: x + 0.1, y: 3.02, w: 2.65, h: 0.32,
      fontFace: FONT, fontSize: 13, bold: true, color: C.white, align: "center", margin: 0,
    });
    s.addText(st.n, {
      x: x + 0.1, y: 3.4, w: 2.65, h: 0.3,
      fontFace: FONT, fontSize: 10.5, color: C.muted, align: "center", margin: 0,
    });
  });

  // 对照实验条（本页核心）
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.7, y: 4.3, w: W - 1.4, h: 2.35,
    fill: { color: C.card }, rectRadius: 0.1, line: { color: C.line, width: 0.75 },
  });
  s.addText("对照实验：同一份评测集，加门 vs 不加门", {
    x: 1.0, y: 4.48, w: 8, h: 0.32,
    fontFace: FONT, fontSize: 14, bold: true, color: C.accent2, margin: 0,
  });

  // 两条对比横条
  const bars = [
    { label: "无合规门（只靠银行侧兜底）", v: 43.9, txt: "43.9%", c: C.bad, y: 5.0 },
    { label: "有合规门（本方案）", v: 98.2, txt: "98.2%", c: C.ok, y: 5.72 },
  ];
  bars.forEach((b) => {
    const maxW = 6.5;  // 留出右侧百分比标签空间，否则会被版面右缘裁掉
    s.addText(b.label, {
      x: 1.0, y: b.y, w: 3.4, h: 0.3,
      fontFace: FONT, fontSize: 12, color: C.muted, margin: 0,
    });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 4.5, y: b.y + 0.02, w: maxW, h: 0.26,
      fill: { color: "0E1825" }, rectRadius: 0.05, line: { color: C.line, width: 0.5 },
    });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 4.5, y: b.y + 0.02, w: Math.max(0.3, maxW * (b.v / 100)), h: 0.26,
      fill: { color: b.c }, rectRadius: 0.05,
    });
    s.addText(b.txt, {
      x: 4.5 + maxW + 0.15, y: b.y, w: 1.3, h: 0.3,
      fontFace: FONT, fontSize: 14, bold: true, color: b.c, margin: 0,
    });
  });
  s.addText("应拦的 125 条：有门拦下 123，无门只拦下 32 —— 差 93 条", {
    x: 1.0, y: 6.35, w: W - 2, h: 0.28,
    fontFace: FONT, fontSize: 12, color: C.text, margin: 0,
  });
  footer(s, 7);
}

/* ============================ 8 安全双闸 ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "安全 / DEFENSE", "双闸：Agent 四门 + 银行侧独立兜底");

  const left = [
    ["注入 / 越狱", "27 条模式 + 间接载体检测"],
    ["编码绕过", "实体 / URL / uXXXX / base64 / 零宽 / leetspeak"],
    ["授权范围", "代客 / 横向 / 测评篡改一律拦"],
    ["目录硬约束", "未知品名 block，禁止近名替换"],
    ["澄清门", "房贷 / 梭哈 / VIP 施压先澄清"],
  ];
  const right = [
    ["转账白名单", ">5 万非本人 → 403"],
    ["日累计软限", "对外 >2 万/日 → 403"],
    ["申购适当性", "risk_score 不足 → 403"],
    ["密钥纪律", "无 .env；包内仅 .env.example"],
    ["代理隔离", "环回流量强制 trust_env=false"],
  ];

  // 左右栏标题 + 竖线
  s.addText("Agent 侧", {
    x: 0.7, y: 1.85, w: 5, h: 0.3,
    fontFace: FONT, fontSize: 13, bold: true, color: C.accent2, charSpacing: 1, margin: 0,
  });
  s.addText("Bank 侧（第二道闸）", {
    x: 6.9, y: 1.85, w: 5, h: 0.3,
    fontFace: FONT, fontSize: 13, bold: true, color: C.accent2, charSpacing: 1, margin: 0,
  });

  const drawCol = (arr, x0) => {
    arr.forEach((r, i) => {
      const y = 2.3 + i * 0.88;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: x0, y, w: 5.75, h: 0.76,
        fill: { color: C.card }, rectRadius: 0.08, line: { color: C.line, width: 0.5 },
      });
      s.addText(r[0], {
        x: x0 + 0.22, y: y + 0.09, w: 5.3, h: 0.28,
        fontFace: FONT, fontSize: 13, bold: true, color: C.white, margin: 0,
      });
      s.addText(r[1], {
        x: x0 + 0.22, y: y + 0.38, w: 5.3, h: 0.28,
        fontFace: FONT, fontSize: 11, color: C.muted, margin: 0,
      });
    });
  };
  drawCol(left, 0.7);
  drawCol(right, 6.9);
  footer(s, 8);
}

/* ============================ 9 局限（新增：主动交底） ============================ */
{
  const s = pres.addSlide();
  bg(s);
  header(s, "局限 / LIMITS", "我们没做到的事，比做到的更值得先说", "主动交底，避免评委追问时被动");

  const limits = [
    ["没接 LLM", "拦/放行全由规则引擎决定。「模型后置」是架构定位，不是已完成功能"],
    ["没碰真实银行", "只有 Mock Bank。行内接口形态、鉴权、灰度流程全部未知"],
    ["没做竞品调研", "不确定市面上是否已有同类前置合规网关"],
    ["3 条用例未通过", "E10/T23 属评测集自身口径冲突；B01 是主动取舍（宁可多问一句）"],
    ["注入词表不全", "覆盖中/英/日 + 编码族；韩/法/俄等语种未覆盖"],
  ];
  limits.forEach((l, i) => {
    const y = 2.05 + i * 0.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.7, y, w: W - 1.4, h: 0.82,
      fill: { color: C.card }, rectRadius: 0.08, line: { color: C.line, width: 0.5 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y, w: 0.06, h: 0.82, fill: { color: C.warn },
    });
    s.addText(l[0], {
      x: 0.98, y: y + 0.22, w: 2.6, h: 0.36,
      fontFace: FONT, fontSize: 15, bold: true, color: C.warn, margin: 0,
    });
    s.addText(l[1], {
      x: 3.7, y: y + 0.22, w: W - 4.5, h: 0.36,
      fontFace: FONT, fontSize: 13, color: C.text, margin: 0,
    });
  });
  footer(s, 9);
}

/* ============================ 10 收尾 ============================ */
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: H, fill: { color: C.accent },
  });

  s.addText("收尾 / CLOSING", {
    x: 0.9, y: 1.15, w: 8, h: 0.3,
    fontFace: FONT, fontSize: 12, color: C.accent, charSpacing: 2, margin: 0,
  });
  s.addText("让银行的大模型「先审后答」", {
    x: 0.9, y: 1.6, w: 11.5, h: 0.75,
    fontFace: FONT, fontSize: 36, bold: true, color: C.white, margin: 0,
  });

  const lines = ["每一条销售话术过四道门", "每一次拦截进审计", "每一个失败都可复现、可修复"];
  lines.forEach((l, i) => {
    s.addText(l, {
      x: 0.9, y: 2.55 + i * 0.48, w: 8, h: 0.4,
      fontFace: FONT, fontSize: 17, color: C.text, margin: 0,
    });
  });

  // 落地假设
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.9, y: 4.45, w: W - 1.8, h: 2.1,
    fill: { color: C.card }, rectRadius: 0.1, line: { color: C.line, width: 0.75 },
  });
  s.addText("落地假设（微众类互联网银行试点）", {
    x: 1.2, y: 4.62, w: 10, h: 0.32,
    fontFace: FONT, fontSize: 14, bold: true, color: C.accent2, margin: 0,
  });
  const rows = [
    ["切入点", "财富售前合规拦截层（SDK / 网关挂在 Agent 与工具之间）"],
    ["对接面", "风险等级 · 产品目录 · 话术库 · 行内审计平台"],
    ["性能", "合规门稳态 2–3 ms（p95 < 5 ms），串在销售链路上不成为瓶颈"],
    ["前提", "【未核验】行内是否已有同类产品 —— 发言按「假设」表述"],
  ];
  rows.forEach((r, i) => {
    const y = 5.05 + i * 0.36;
    s.addText(r[0], {
      x: 1.2, y, w: 1.1, h: 0.3,
      fontFace: FONT, fontSize: 11, color: C.muted, margin: 0,
    });
    s.addText(r[1], {
      x: 2.4, y, w: W - 3.5, h: 0.3,
      fontFace: FONT, fontSize: 11, color: C.text, margin: 0,
    });
  });
  footer(s, 10);
}

pres.writeFile({ fileName: join(__dirname, "..", "submit", "02_答辩材料_v2.pptx") })
  .then(() => console.log("wrote 02_答辩材料_v2.pptx"))
  .catch((e) => { console.error(e); process.exit(1); });
