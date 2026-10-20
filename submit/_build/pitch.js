const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.author = "弋承熙 & 高依灵";
pres.title = "合规先审·银行AI销售智能体（合规官）";
pres.subject = "FinTechathon 2026 答辩材料 v0";

const C = {
  bg: "0B1220",
  card: "121A2B",
  line: "1E293B",
  text: "E2E8F0",
  muted: "94A3B8",
  accent: "14B8A6",
  accent2: "38BDF8",
  warn: "F59E0B",
  danger: "F87171",
  white: "FFFFFF",
  ok: "34D399",
};

const FONT = "Noto Sans CJK SC";

function bg(slide) {
  slide.background = { color: C.bg };
}

function footer(slide, page, total) {
  slide.addText("FinTechathon 2026 · 银行 AI 智能体 · 弋承熙 & 高依灵", {
    x: 0.5, y: 7.1, w: 10, h: 0.28,
    fontFace: FONT, fontSize: 10, color: C.muted, margin: 0,
  });
  slide.addText(`${page} / ${total}`, {
    x: 11.5, y: 7.1, w: 1.3, h: 0.28,
    fontFace: FONT, fontSize: 10, color: C.muted, align: "right", margin: 0,
  });
}

const TOTAL = 9;

// ===== 1 Cover =====
{
  const s = pres.addSlide();
  bg(s);
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.accent },
  });
  s.addText("FinTechathon 2026  ·  银行 AI 智能体赛道", {
    x: 0.7, y: 1.5, w: 12, h: 0.4,
    fontFace: FONT, fontSize: 14, color: C.accent, margin: 0,
  });
  s.addText("合规先审 · 银行 AI 销售智能体", {
    x: 0.7, y: 2.2, w: 12, h: 0.8,
    fontFace: FONT, fontSize: 36, bold: true, color: C.white, margin: 0,
  });
  s.addText("（合规官）", {
    x: 0.7, y: 2.95, w: 12, h: 0.5,
    fontFace: FONT, fontSize: 28, color: C.accent2, margin: 0,
  });
  s.addText("先审后答 · 每一步留痕 —— 让银行敢让大模型卖理财的那一层", {
    x: 0.7, y: 3.7, w: 11, h: 0.45,
    fontFace: FONT, fontSize: 16, color: C.text, margin: 0,
  });
  s.addText([
    { text: "队伍：弋承熙 & 高依灵", options: { breakLine: true } },
    { text: "答辩材料 v0  ·  约 8–10 分钟  ·  2026-10-18", options: { breakLine: true } },
    { text: "Mock 数据 · 不接真实资金 · 不构成投资建议", options: {} },
  ], {
    x: 0.7, y: 4.6, w: 11, h: 1.2,
    fontFace: FONT, fontSize: 13, color: C.muted, margin: 0, paraSpaceAfter: 6,
  });
  footer(s, 1, TOTAL);
}

// ===== 2 Problem =====
{
  const s = pres.addSlide();
  bg(s);
  s.addText("问题", {
    x: 0.5, y: 0.35, w: 3, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("银行怕的不是答得慢，是卖错人、说错话、转错钱", {
    x: 0.5, y: 0.7, w: 12.3, h: 0.55,
    fontFace: FONT, fontSize: 24, bold: true, color: C.white, margin: 0,
  });

  const cards = [
    { t: "适当性失守", d: "R2 客户被推 R4\n投诉 / 监管 / 举证失败", c: C.danger },
    { t: "违规话术", d: "「保本」「稳赚」「刚兑」\n销售误导 · 消保红线", c: C.warn },
    { t: "越权资金", d: "大额陌生收款人\n注入后试图绕限额", c: C.danger },
    { t: "不可审计", d: "只有聊天记录\n无法自证「哪一步拦了」", c: C.accent2 },
  ];
  cards.forEach((card, i) => {
    const x = 0.5 + i * 3.15;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.6, w: 3.0, h: 3.6,
      fill: { color: C.card }, rectRadius: 0.1,
      line: { color: C.line, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.6, w: 3.0, h: 0.12, fill: { color: card.c },
    });
    s.addText(card.t, {
      x: x + 0.2, y: 2.0, w: 2.6, h: 0.5,
      fontFace: FONT, fontSize: 18, bold: true, color: C.white, margin: 0,
    });
    s.addText(card.d, {
      x: x + 0.2, y: 2.7, w: 2.6, h: 2.0,
      fontFace: FONT, fontSize: 14, color: C.text, margin: 0,
    });
  });
  s.addText("一句话：需要的不是「更会聊」的 Agent，而是「先审后答、每步留痕」的 Agent。", {
    x: 0.5, y: 5.5, w: 12.3, h: 0.45,
    fontFace: FONT, fontSize: 15, color: C.accent, margin: 0,
  });
  footer(s, 2, TOTAL);
}

// ===== 3 Solution =====
{
  const s = pres.addSlide();
  bg(s);
  s.addText("方案", {
    x: 0.5, y: 0.35, w: 3, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("四道门 + 全链路审计 + 银行侧双闸", {
    x: 0.5, y: 0.7, w: 12.3, h: 0.5,
    fontFace: FONT, fontSize: 24, bold: true, color: C.white, margin: 0,
  });

  const gates = [
    { n: "01", t: "意图门", d: "注入 / 越狱 / 越权\n非业务意图" },
    { n: "02", t: "产品门", d: "目录 allowlist\n幻觉品名硬拒" },
    { n: "03", t: "适当性", d: "风险分 vs 产品\n购拦 / 询警示" },
    { n: "04", t: "话术门", d: "禁保本/稳赚\n放行必带披露" },
  ];
  gates.forEach((g, i) => {
    const x = 0.5 + i * 3.15;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.5, w: 3.0, h: 2.4,
      fill: { color: C.card }, rectRadius: 0.1,
      line: { color: C.line, width: 1 },
    });
    s.addText(g.n, {
      x: x + 0.2, y: 1.7, w: 2.6, h: 0.4,
      fontFace: FONT, fontSize: 20, bold: true, color: C.accent, margin: 0,
    });
    s.addText(g.t, {
      x: x + 0.2, y: 2.2, w: 2.6, h: 0.4,
      fontFace: FONT, fontSize: 18, bold: true, color: C.white, margin: 0,
    });
    s.addText(g.d, {
      x: x + 0.2, y: 2.75, w: 2.6, h: 0.9,
      fontFace: FONT, fontSize: 13, color: C.muted, margin: 0,
    });
    if (i < 3) {
      s.addText("→", {
        x: x + 2.85, y: 2.4, w: 0.4, h: 0.4,
        fontFace: FONT, fontSize: 18, color: C.accent2, margin: 0,
      });
    }
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.2, w: 12.3, h: 2.2,
    fill: { color: C.card }, rectRadius: 0.1,
    line: { color: C.line, width: 1 },
  });
  s.addText("三条原则", {
    x: 0.75, y: 4.4, w: 4, h: 0.35,
    fontFace: FONT, fontSize: 14, bold: true, color: C.accent2, margin: 0,
  });
  s.addText([
    { text: "1. 规则先行，模型后置 —— YAML 管「能不能」，LLM 管「怎么说」", options: { breakLine: true } },
    { text: "2. 默认拒绝 —— 目录外 / 金额不清 / 意图不定 → 澄清或拦截", options: { breakLine: true } },
    { text: "3. 可回放 —— request_id + 四门明细 + 原因码，审计可重放成路演画面", options: {} },
  ], {
    x: 0.75, y: 4.85, w: 11.8, h: 1.35,
    fontFace: FONT, fontSize: 14, color: C.text, margin: 0, paraSpaceAfter: 6,
  });
  footer(s, 3, TOTAL);
}

// ===== 4 Architecture =====
{
  const s = pres.addSlide();
  bg(s);
  s.addText("架构", {
    x: 0.5, y: 0.35, w: 3, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("W0 可运行骨架 · LangGraph-ready", {
    x: 0.5, y: 0.7, w: 12.3, h: 0.5,
    fontFace: FONT, fontSize: 24, bold: true, color: C.white, margin: 0,
  });

  const flow = [
    { t: "用户话术", d: "林晓晴 R2" },
    { t: "Intent", d: "确定性分类" },
    { t: "四道门", d: "gates.py" },
    { t: "Tools", d: "仅 allowed" },
    { t: "审计", d: "JSONL" },
  ];
  flow.forEach((f, i) => {
    const x = 0.5 + i * 2.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.5, w: 2.2, h: 1.35,
      fill: { color: i === 2 ? "0F3D3A" : C.card },
      rectRadius: 0.08,
      line: { color: i === 2 ? C.accent : C.line, width: 1.5 },
    });
    s.addText(f.t, {
      x: x + 0.1, y: 1.7, w: 2.0, h: 0.45,
      fontFace: FONT, fontSize: 16, bold: true, color: C.white, align: "center", margin: 0,
    });
    s.addText(f.d, {
      x: x + 0.1, y: 2.25, w: 2.0, h: 0.35,
      fontFace: FONT, fontSize: 12, color: C.muted, align: "center", margin: 0,
    });
    if (i < 4) {
      s.addText("→", {
        x: x + 2.15, y: 1.9, w: 0.35, h: 0.4,
        fontFace: FONT, fontSize: 16, color: C.accent, margin: 0,
      });
    }
  });

  const mods = [
    ["agent/", "状态机 + 四关 + 金额解析"],
    ["mock_bank/", "FastAPI + 第二道闸"],
    ["configs/", "compliance_rules.yaml"],
    ["audit/", "events.jsonl 决策轨迹"],
    ["tests/", "83 passed（pytest）"],
    ["data/evals/", "评测集 + 对抗集"],
  ];
  mods.forEach((m, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.5 + col * 4.2;
    const y = 3.3 + row * 1.35;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 4.0, h: 1.15,
      fill: { color: C.card }, rectRadius: 0.08,
      line: { color: C.line, width: 1 },
    });
    s.addText(m[0], {
      x: x + 0.2, y: y + 0.2, w: 3.6, h: 0.35,
      fontFace: FONT, fontSize: 15, bold: true, color: C.accent2, margin: 0,
    });
    s.addText(m[1], {
      x: x + 0.2, y: y + 0.55, w: 3.6, h: 0.4,
      fontFace: FONT, fontSize: 13, color: C.text, margin: 0,
    });
  });
  footer(s, 4, TOTAL);
}

// ===== 5 Demo =====
{
  const s = pres.addSlide();
  bg(s);
  s.addText("演示三幕（约 5 分钟）", {
    x: 0.5, y: 0.35, w: 8, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("拦得住 · 办得成 · 兜得住", {
    x: 0.5, y: 0.7, w: 12.3, h: 0.5,
    fontFace: FONT, fontSize: 24, bold: true, color: C.white, margin: 0,
  });

  const acts = [
    {
      title: "第一幕 · 拦得住",
      time: "~90s",
      color: C.danger,
      lines: [
        "「…保本的。」",
        "Gate4 → USER_FORBIDDEN:保本",
        "规则门在模型之前拦下",
        "资金工具调用 = 0",
      ],
    },
    {
      title: "第二幕 · 办得成",
      time: "~120s",
      color: C.ok,
      lines: [
        "R2 货基/短债 → 放行",
        "WB_CASH_001 + 强制披露",
        "100 元转本人备用金",
        "审计面板实时追加 JSONL",
      ],
    },
    {
      title: "第三幕 · 兜得住",
      time: "~90s",
      color: C.warn,
      lines: [
        "6 万转陌生人 → 白名单拦",
        "注入改收款人 → 金额门兜住",
        "主动交底失败数字",
        "可回归用例表，不是剪辑",
      ],
    },
  ];
  acts.forEach((a, i) => {
    const x = 0.5 + i * 4.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.45, w: 4.0, h: 4.9,
      fill: { color: C.card }, rectRadius: 0.1,
      line: { color: C.line, width: 1 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.45, w: 4.0, h: 0.1, fill: { color: a.color },
    });
    s.addText(a.title, {
      x: x + 0.25, y: 1.75, w: 3.5, h: 0.4,
      fontFace: FONT, fontSize: 16, bold: true, color: C.white, margin: 0,
    });
    s.addText(a.time, {
      x: x + 0.25, y: 2.2, w: 3.5, h: 0.3,
      fontFace: FONT, fontSize: 12, color: a.color, margin: 0,
    });
    a.lines.forEach((line, li) => {
      s.addText("·  " + line, {
        x: x + 0.25, y: 2.8 + li * 0.55, w: 3.5, h: 0.45,
        fontFace: FONT, fontSize: 14, color: C.text, margin: 0,
      });
    });
  });
  footer(s, 5, TOTAL);
}

// ===== 6 Diff =====
{
  const s = pres.addSlide();
  bg(s);
  s.addText("差异化", {
    x: 0.5, y: 0.35, w: 3, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("别人做「会卖」——我们做「银行敢让它卖」", {
    x: 0.5, y: 0.7, w: 12.3, h: 0.5,
    fontFace: FONT, fontSize: 22, bold: true, color: C.white, margin: 0,
  });

  const rows = [
    ["常见做法", "我们"],
    ["system prompt 说「要合规」", "独立可测组件 gates.py + YAML + 单测"],
    ["只演示成功路径", "同一流程既放行又拦截，边界可见"],
    ["靠模型自觉不说幻觉", "目录 allowlist 硬约束"],
    ["审计 = 存对话", "审计 = 结构化决策轨迹"],
    ["事后人工抽检", "评测集可 CI 回归"],
  ];
  s.addTable(
    rows.map((r, i) =>
      r.map((cell) => ({
        text: cell,
        options: {
          fill: { color: i === 0 ? "0F3D3A" : C.card },
          color: i === 0 ? C.accent : C.text,
          bold: i === 0 || cell === r[1],
          fontFace: FONT,
          fontSize: i === 0 ? 13 : 13,
          align: "left",
          valign: "middle",
        },
      }))
    ),
    {
      x: 0.5, y: 1.5, w: 12.3, h: 4.8,
      colW: [5.5, 6.8],
      border: { pt: 0.5, color: C.line },
      fontFace: FONT,
    }
  );
  footer(s, 6, TOTAL);
}

// ===== 7 Metrics =====
{
  const s = pres.addSlide();
  bg(s);
  s.addText("数据（如实 · 未经美化）", {
    x: 0.5, y: 0.35, w: 8, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("敢在路演放失败数字，因为有可回归用例表", {
    x: 0.5, y: 0.7, w: 12.3, h: 0.5,
    fontFace: FONT, fontSize: 22, bold: true, color: C.white, margin: 0,
  });

  const metrics = [
    { v: "70", l: "评测集 v0 条数", note: "W/T/X/A" },
    { v: "0%", l: "误拦率", note: "该放的没被拦" },
    { v: "41.9%", l: "应拦拦截率", note: "W1 主攻" },
    { v: "58.8%", l: "注入逃逸率", note: "越低越好 · W1" },
  ];
  metrics.forEach((m, i) => {
    const x = 0.5 + i * 3.15;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.5, w: 3.0, h: 2.5,
      fill: { color: C.card }, rectRadius: 0.1,
      line: { color: C.line, width: 1 },
    });
    s.addText(m.v, {
      x: x + 0.15, y: 1.8, w: 2.7, h: 0.8,
      fontFace: FONT, fontSize: 36, bold: true,
      color: i >= 2 ? C.warn : C.accent, align: "center", margin: 0,
    });
    s.addText(m.l, {
      x: x + 0.15, y: 2.7, w: 2.7, h: 0.4,
      fontFace: FONT, fontSize: 14, bold: true, color: C.white, align: "center", margin: 0,
    });
    s.addText(m.note, {
      x: x + 0.15, y: 3.2, w: 2.7, h: 0.35,
      fontFace: FONT, fontSize: 12, color: C.muted, align: "center", margin: 0,
    });
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 4.3, w: 12.3, h: 2.1,
    fill: { color: C.card }, rectRadius: 0.1,
    line: { color: C.line, width: 1 },
  });
  s.addText("W1 目标", {
    x: 0.75, y: 4.5, w: 4, h: 0.35,
    fontFace: FONT, fontSize: 14, bold: true, color: C.accent2, margin: 0,
  });
  s.addText("应拦拦截率 ≥ 90%  ·  注入逃逸 ≤ 20%  ·  误拦 ≤ 5%  ·  评测集 ≥ 80 条\n单测当前 83 passed  ·  对抗集 103 条真跑  ·  指标口径【待依灵确认】前不对外签章引用", {
    x: 0.75, y: 5.0, w: 11.8, h: 1.1,
    fontFace: FONT, fontSize: 14, color: C.text, margin: 0,
  });
  footer(s, 7, TOTAL);
}

// ===== 8 Security =====
{
  const s = pres.addSlide();
  bg(s);
  s.addText("安全", {
    x: 0.5, y: 0.35, w: 3, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("双闸：Agent 四门 + Mock Bank 兜底", {
    x: 0.5, y: 0.7, w: 12.3, h: 0.5,
    fontFace: FONT, fontSize: 22, bold: true, color: C.white, margin: 0,
  });

  const left = [
    ["注入 / 越狱", "YAML 模式 + 间接注入载体检测"],
    ["授权范围", "代客 / 横向 / 测评篡改一律拦"],
    ["目录硬约束", "未知品名 block，禁止静默近名替换"],
    ["话术归一", "同音变体防「保本」绕过"],
  ];
  const right = [
    ["转账白名单", ">5 万非本人 → 403"],
    ["日累计软限", "对外 >2 万/日 → 403"],
    ["申购适当性", "risk_score 不足 → 403"],
    ["密钥纪律", "无 .env；包内仅 .env.example"],
  ];

  s.addText("Agent 侧", {
    x: 0.5, y: 1.4, w: 6, h: 0.35,
    fontFace: FONT, fontSize: 14, bold: true, color: C.accent2, margin: 0,
  });
  s.addText("Bank 侧第二道闸", {
    x: 6.9, y: 1.4, w: 6, h: 0.35,
    fontFace: FONT, fontSize: 14, bold: true, color: C.accent2, margin: 0,
  });

  left.forEach((row, i) => {
    const y = 1.9 + i * 1.05;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y, w: 6.0, h: 0.9,
      fill: { color: C.card }, rectRadius: 0.08,
      line: { color: C.line, width: 1 },
    });
    s.addText(row[0], {
      x: 0.7, y: y + 0.12, w: 5.6, h: 0.3,
      fontFace: FONT, fontSize: 14, bold: true, color: C.white, margin: 0,
    });
    s.addText(row[1], {
      x: 0.7, y: y + 0.45, w: 5.6, h: 0.3,
      fontFace: FONT, fontSize: 12, color: C.muted, margin: 0,
    });
  });
  right.forEach((row, i) => {
    const y = 1.9 + i * 1.05;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 6.9, y, w: 5.9, h: 0.9,
      fill: { color: C.card }, rectRadius: 0.08,
      line: { color: C.line, width: 1 },
    });
    s.addText(row[0], {
      x: 7.1, y: y + 0.12, w: 5.5, h: 0.3,
      fontFace: FONT, fontSize: 14, bold: true, color: C.white, margin: 0,
    });
    s.addText(row[1], {
      x: 7.1, y: y + 0.45, w: 5.5, h: 0.3,
      fontFace: FONT, fontSize: 12, color: C.muted, margin: 0,
    });
  });
  footer(s, 8, TOTAL);
}

// ===== 9 Close =====
{
  const s = pres.addSlide();
  bg(s);
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 7.5, fill: { color: C.accent },
  });
  s.addText("收尾", {
    x: 0.7, y: 1.3, w: 3, h: 0.35,
    fontFace: FONT, fontSize: 12, color: C.accent, margin: 0,
  });
  s.addText("让银行的大模型「先审后答」", {
    x: 0.7, y: 1.9, w: 12, h: 0.6,
    fontFace: FONT, fontSize: 28, bold: true, color: C.white, margin: 0,
  });
  s.addText("每一条销售话术过四道门\n每一次拦截进审计\n每一个失败都可复现、可修复", {
    x: 0.7, y: 2.7, w: 12, h: 1.5,
    fontFace: FONT, fontSize: 18, color: C.text, margin: 0,
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.7, y: 4.5, w: 11.8, h: 1.7,
    fill: { color: C.card }, rectRadius: 0.1,
    line: { color: C.line, width: 1 },
  });
  s.addText("落地假设（微众类互联网银行试点）", {
    x: 0.95, y: 4.7, w: 11, h: 0.35,
    fontFace: FONT, fontSize: 14, bold: true, color: C.accent2, margin: 0,
  });
  s.addText("切入点：财富售前合规拦截层（SDK/网关挂在 Agent 与工具之间）\n对接：风险等级 · 产品目录 · 话术库 · 行内审计平台  ·  KPI：误导投诉 / 拦截率 / 复核工时\n【未核验】行内是否已有同类产品 —— 发言按「假设」表述", {
    x: 0.95, y: 5.15, w: 11.3, h: 0.9,
    fontFace: FONT, fontSize: 13, color: C.muted, margin: 0,
  });
  footer(s, 9, TOTAL);
}

pres.writeFile({ fileName: "<repo-root>/submit/02_答辩材料_v0.pptx" })
  .then(() => console.log("pptx written"))
  .catch((e) => { console.error(e); process.exit(1); });
