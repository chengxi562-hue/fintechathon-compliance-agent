# -*- coding: utf-8 -*-
"""Build 01_技术文档_v0.docx for FinTechathon platform submit."""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

OUT = Path(__file__).resolve().parents[1] / "submit" / "01_技术文档_v1.docx"

doc = Document()
# page margins
for section in doc.sections:
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

def set_run_font(run, size=11, bold=False, color=None, name="SimHei"):
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = name
    r = run._element
    rPr = r.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn("w:eastAsia"), name)
    if color:
        run.font.color.rgb = RGBColor(*color)

def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        set_run_font(run, size={1: 18, 2: 14, 3: 12}.get(level, 11), bold=True, name="SimHei")
    return h

def add_p(text, size=11, bold=False, space_after=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.25
    return p

def add_bullets(items, size=10.5):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(it)
        set_run_font(run, size=size)
        p.paragraph_format.space_after = Pt(2)

def add_table(headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        set_run_font(run, size=10, bold=True)
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = t.rows[r_i + 1].cells[c_i]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            set_run_font(run, size=9.5)
    doc.add_paragraph()

# ---- Cover ----
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run("FinTechathon 2026 · 银行 AI 智能体赛道")
set_run_font(r, size=12, color=(0x55, 0x55, 0x55))

t2 = doc.add_paragraph()
t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t2.add_run("技术文档 v1")
set_run_font(r, size=28, bold=True)

t3 = doc.add_paragraph()
t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t3.add_run("合规先审 · 银行 AI 销售智能体（合规官）")
set_run_font(r, size=16, bold=True)

meta = [
    "队伍：弋承熙 & 高依灵",
    "作品主体：队伍独立完成（AI 工具辅助编程）；数据处理与评测口径经队伍复核",
    "文档日期：2026-10-20（Asia/Shanghai）",
    "阶段：W1 完成（四场景 + Demo Web）+ 注入/编码防御加固",
    "许可证：MIT",
    "声明：Demo 使用 Mock 账户与合成数据；不接真实资金；不构成投资建议。",
]
for m in meta:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(m)
    set_run_font(r, size=10, color=(0x44, 0x44, 0x44))

doc.add_paragraph()

# ---- 1 概述 ----
add_heading("1. 概述", 1)
add_heading("1.1 一句话", 2)
add_p("不做「会聊天的理财客服」，做「先审后答、可审计、能过自动评测」的银行销售 Agent。")
add_p("四道合规门：意图 → 产品匹配 → 适当性 → 话术；工具层（Mock Bank）仅在四门全过后调用；每次决策写入 JSONL 审计。")

add_heading("1.2 问题背景", 2)
add_p("银行把销售触点交给大模型，出错成本不是「答得不好」，而是卖错人、说错话、转错钱：")
add_table(
    ["失效类型", "现实形态", "后果"],
    [
        ["适当性失守", "R2 客户被推荐 R4 产品", "投诉、监管处罚、举证失败"],
        ["违规话术", "「保本」「稳赚」「刚兑」", "销售误导，消保红线"],
        ["越权资金动作", "大额/陌生收款人、提示词注入绕限", "直接资损"],
        ["不可审计", "只有聊天记录，无决策轨迹", "事后无法自证"],
    ],
)

add_heading("1.3 设计原则", 2)
add_bullets([
    "规则先行，模型后置：确定性 YAML 规则管「能不能」，LLM 只管「怎么说」。当前版本未接入任何 LLM（requirements.txt 无 LLM 依赖、代码无模型调用），拦/放行完全由规则引擎决定，故无 Key 也可完整演示。",
    "默认拒绝：产品不在目录、金额说不清、意图不确定 → 澄清或拦截，绝不静默执行。",
    "可回放：每个决策有 request_id + 四门明细 + 原因码，审计日志可逐条重放。",
    "双闸：Agent 四道门 + Mock Bank 侧独立限额/适当性兜底，即使门被绕过直打 API 也会被拦。",
])

# ---- 2 架构 ----
add_heading("2. 系统架构", 1)
add_heading("2.1 总体数据流", 2)
add_p(
    "User utterance → Intent classify → Plan（显式步骤）→ Compliance Gate ×4（YAML）"
    " → Tools（Mock Bank HTTP，仅 allowed）→ Explain + Audit JSONL",
    size=10.5,
)
add_p("agent/graph.py 按未来 LangGraph 节点切分，当前用纯 Python 状态机实现，不依赖任何 LLM 或外部服务即可完整演示拦/放行与二次确认。")

add_heading("2.2 模块划分", 2)
add_table(
    ["模块", "路径", "职责"],
    [
        ["合规引擎", "agent/gates.py", "四道门 + 意图分类 + 产品解析 + 注入/授权范围检测"],
        ["状态机", "agent/graph.py", "run_agent：意图→计划→门控→工具→解释"],
        ["话术归一", "agent/normalize.py", "同音/变体禁词匹配，防「保本」绕过"],
        ["确认门", "agent/pending_action.py", "W1 订阅改额/代扣 PendingAction（未确认不落账）"],
        ["Mock Bank", "mock_bank/", "FastAPI：客户/账户/转账/理财；第二道闸"],
        ["规则表", "configs/compliance_rules.yaml", "版本化规则（v0.1.0，27 条注入模式）"],
        ["审计", "audit/logger.py", "JSONL 追加：ts/request_id/gates/decision/…"],
        ["评测", "data/evals/ + scripts/", "评测集 v1（173 条）+ 对抗集（111 条）+ probe runner"],
        ["测试", "tests/", "pytest，当前 141 passed（含代理隔离回归）"],
    ],
)

add_heading("2.3 Mock Bank API（节选）", 2)
add_table(
    ["Method", "Path", "说明"],
    [
        ["GET", "/health", "健康检查"],
        ["GET", "/v1/customers/{id}", "客户（含 risk_score）"],
        ["GET", "/v1/accounts/{id}", "账户余额"],
        ["GET", "/v1/wealth/products", "理财目录 allowlist"],
        ["POST", "/v1/transfers", "转账（大额确认 + 银行侧白名单/日限）"],
        ["POST", "/v1/wealth/purchase", "申购（银行侧适当性兜底）"],
    ],
)
add_p("Seed 客户：cust_yw_001（林晓晴，R2，深圳白领）。产品：WB_CASH_001 / WB_BOND_002 / WB_EQ_MIX_003。")

add_heading("2.4 部署拓扑（Demo）", 2)
add_bullets([
    "本机：uvicorn mock_bank.app:app --port 8000 + python scripts/demo_wealth_ask.py",
    "Docker Compose：docker compose up --build（Mock Bank → :8000）",
    "环境变量见 .env.example（仅 MOCK_BANK_URL / AUDIT_DIR / COMPLIANCE_RULES；无真实密钥）。",
])

# ---- 3 算法 ----
add_heading("3. 核心算法与门控逻辑", 1)
add_heading("3.1 意图分类", 2)
add_p("规则优先的确定性分类（非 LLM）：")
add_bullets([
    "否定极性：如「不用转账」不得判 transfer。",
    "实体优先：目录中文品名或 WB_* ID 命中 → wealth_inquire / wealth_purchase。",
    "转账动词 / 余额 / 订阅 / 询安（「最安全」→ chitchat，由话术门拦，禁止顺带推品）。",
    "默认 chitchat。",
])

add_heading("3.2 四道合规门", 2)
add_table(
    ["门", "输入要点", "失败时行为"],
    [
        ["Gate1 意图/注入", "utterance + inject/auth_scope 模式", "block；间接注入标 via:indirect"],
        ["Gate2 产品匹配", "catalog_allowlist + 显式解析", "幻觉品名/未知 ID → reject，不做近名纠正"],
        ["Gate3 适当性", "customer.risk_score vs product.min_risk", "购买越级 block；咨询可降级警示（不拦）"],
        ["Gate4 话术", "forbidden_phrases + 归一化匹配", "命中「保本/稳赚/…」→ block；放行强制披露"],
    ],
)

add_heading("3.3 金额解析", 2)
add_p("支持阿拉伯数字、千分位、万/千/亿单位、中文数词（五千/三万五）；多笔金额合计；≤0 判 TRANSFER_AMOUNT_INVALID。")

add_heading("3.4 转账决策", 2)
add_bullets([
    "缺金额 → TRANSFER_AMOUNT_MISSING",
    "≥ whitelist_only_above（默认 5 万）且非本人账户 → TRANSFER_WHITELIST_REQUIRED",
    "≥ require_confirm_above（默认 5 千）→ pending_confirm",
    "日累计软限（默认 2 万，对外）→ TRANSFER_SOFT_LIMIT",
])

add_heading("3.5 产品解析", 2)
add_p("先精确匹配目录 ID（大小写敏感），再最长中文品名匹配；出现疑似品名但不在目录 → 必须 block，禁止静默替换为近名产品。")

# ---- 4 安全 ----
add_heading("4. 安全设计", 1)
add_heading("4.1 威胁模型（Demo 范围）", 2)
add_bullets([
    "提示词注入 / 越狱试图绕过合规门",
    "幻觉产品名诱导推荐目录外产品",
    "越权：代客、横向查询、篡改风险测评",
    "直打银行 API 绕过 Agent 门",
    "密钥泄漏（本仓库不存放真实 LLM Key / 生产凭据）",
])

add_heading("4.2 控制措施", 2)
add_table(
    ["控制", "实现", "当前实测"],
    [
        ["注入检测", "YAML inject_patterns 27 条 + indirect_inject_patterns + 否定引用保护", "注入/编码族逃逸 0/45"],
        ["编码归一（W2）", "HTML 实体 / URL 编码 / unicode 转义 / base64 片段 / 零宽 / 空格拆词 / leetspeak 统一先解码再匹配", "编码归一族 12/12"],
        ["授权范围", "auth_scope：代客 / 亲属 / 其他客户 / 别人他人 / 自述财力越级 一律拦", "横向越权 6/6"],
        ["目录硬约束", "catalog_allowlist + off_catalog_product_patterns；禁止静默近名替换", "目录外品名 全拦"],
        ["话术归一", "normalize_text + 同音/拼音/英文变体 + leetspeak", "话术规避 全拦"],
        ["澄清门（W2）", "gate_clarify：房贷/随便推荐/全部身家/VIP 施压 → 先澄清不执行", "模糊意图族 全拦"],
        ["防幻觉附和（W2）", "BILL_CLAIM_UNVERIFIED：账单里没有的金额先否认再列真实数据", "账单幻觉 拦下"],
        ["前文指代（W2）", "TRANSFER_CONTEXT_MISSING：无待确认单时不凭「刚才那笔」执行", "多轮 M 组 11/11"],
        ["银行第二道闸", "转账白名单硬拦、日累计软限、申购适当性 403；确认阈值与 Agent 侧同一比较符", "双闸直打 API 仍 403"],
        ["确认门", "PendingAction：未 confirmed 禁止写订阅/代扣，未确认前银行侧状态一字未动", "全链路可复跑"],
        ["审计留痕", "每请求 JSONL：gate_results / reason_codes / tool_calls；Demo Web 面板读取真实文件尾行", "6 条真实样本可回放"],
        ["环境健壮性（W2）", "环回 Mock Bank 调用强制 trust_env=False，系统代理不得劫持 127.0.0.1", "新增 3 条回归测试"],
        ["密钥纪律", ".gitignore 排除 .env/.venv；提交包仅含 .env.example", "源码包抽检 0 命中"],
    ],
)

add_heading("4.3 已知缺口（如实披露）", 2)
add_p("基于 2026-10-20 21:00 实跑（口径待依灵最终确认，指标定义见 docs/指标定义_v1_20261018.md）：")
add_bullets([
    "注入/编码族逃逸已从 90.5% 降至 0/45；应拦拦截率 98.4%（123/125）、误拦率 2.2%（1/46）、评测集通过率 97.1%（168/173）。",
    "仍失败 3 条已逐条披露：E10（转 5,000）与 T23（转五千）属评测集自身口径冲突（E01「转 5000」期望放行、金额相同）；B01 未指明改哪个订阅，选择先问清再动。",
    "注入词表覆盖中/英/日 + 编码族，韩/法/俄等语种尚未覆盖；审计缺 actor_role / rules_version 字段（P1-3）。",
    "官方自动评测口径【未核验】；自建 runner 可在细则公布后适配。",
])

# ---- 5 评测 ----
add_heading("5. 评测与质量保障", 1)
add_heading("5.1 当前实测（2026-10-20 21:00，同一台机、同一提交）", 2)
add_table(
    ["指标", "当前值", "口径"],
    [
        ["单测", "141 passed", "pytest -q，含代理隔离回归"],
        ["评测集 v1", "168/173 = 97.1%", "严格按 expected_decision 判定（另 2 条 SKIP）"],
        ["应拦拦截率", "123/125 = 98.4%", "期望 block 的用例实际被拦下"],
        ["误拦率", "1/46 = 2.2%", "该放行的被误拦（目标 ≤ 5%）"],
        ["注入/编码族逃逸率", "0/45 = 0%", "注入、越狱、编码绕过、伪造指令族（目标 ≤ 20%）"],
        ["对抗集", "108/111 = 97.3%", "111 条有明确期望的对抗用例"],
    ],
)
add_heading("5.2 关键修复（W2，2026-10-20）", 2)
add_bullets([
    "编码归一：HTML 实体 / URL 编码 / unicode 转义 / base64 片段 / 零宽字符 / 空格拆词 / leetspeak 统一先解码再匹配——编码绕过族从 3/12 提升到 12/12。",
    "越狱话术：注入模式 17→27 条（DAN mode、forget your instructions、伪造管理员、阈值改 0 等）。",
    "横向越权：补「别人/他人/其他客户」，V 组 6/6 全拦（此前 0/6）。",
    "自述财力越级：「我年收入 50 万，直接给我 R5」不再当成普通咨询。",
    "模糊意图澄清：新增第 5 道门 gate_clarify，「房贷怎么还划算」「全部身家/梭哈」「我是 VIP」一律先澄清。",
    "防幻觉附和：账单里不存在的金额先否认再列真实数据（BILL_CLAIM_UNVERIFIED）；无前文指代不执行（TRANSFER_CONTEXT_MISSING）。",
    "环境健壮性：Mock Bank 走环回时强制 trust_env=False——系统代理会把 127.0.0.1 请求转成 502，导致每次「确认订阅」被误判为银行拒单。",
])
add_heading("5.3 对照实验：加门 vs 不加门", 2)
add_p(
    "评委最常问「加这些门到底比不加好多少」。同一份评测集跑了两组：A 有门（四道门+澄清门+银行侧双闸），"
    "B 无门（只做意图分类就调工具，只靠银行侧兜底，模拟「没做合规层的朴素 bot」）。"
)
add_table(
    ["指标", "A 有门", "B 无门", "差距"],
    [
        ["总体正确（171 条有明确期望）", "168 / 171 = 98.2%", "75 / 171 = 43.9%", "+93 条"],
        ["应拦拦截（125 条）", "123", "32", "+91"],
        ["误拦（46 条 allow）", "1", "3", "相当"],
    ],
)
add_p(
    "差距集中在「银行侧物理上判断不了」的类别：禁用语变体、编码绕过、横向越权、提示注入、多轮施压、账单幻觉——"
    "无门组在这些类别几乎全灭。原因是银行 API 只看到一次合法工具调用，话术与授权问题在它之前就已经发生。",
    size=10.5,
)
add_p("完整报告：docs/评测报告_有无合规门对照_20261020.md；原始数据：data/evals/_baseline_no_gates.json。", size=9.5)

add_heading("5.4 延迟与可部署性", 2)
add_p(
    "评审看可落地性会问延迟。本机单线程实测 800 次（含审计 JSONL 同步写盘，不含网络与 LLM）。数字随机器与负载波动，跑 scripts/bench_latency.py 可自行复现："
)
add_table(
    ["用例", "均值", "p95", "说明"],
    [
        ["放行-咨询（走产品查询）", "4.52 ms", "4.93 ms", "最重路径"],
        ["拦截-保本话术", "1.90 ms", "2.26 ms", "纯规则"],
        ["拦截-注入", "1.88 ms", "2.20 ms", "含编码归一"],
        ["放行-小额转账", "2.56 ms", "2.23 ms", "含金额解析"],
        ["合计 800 次", "2–3 ms 量级", "< 5 ms", "偶发 ~100ms（首次写盘，未剔除）"],
    ],
)
add_p(
    "口径说明：不含真实 LLM 推理（当前版本未接 LLM）、不含网络往返。接 LLM 后真实端到端延迟由模型决定"
    "（通常 300ms–2s），本数字只代表合规门这一层的固定开销——也就是说加这层门不会成为延迟瓶颈。"
    "两个离群值（124ms / 25ms）是首次写盘抖动，未剔除。",
    size=10,
)
add_p("完整报告：docs/工程指标_延迟与可部署性_20261020.md；脚本：scripts/bench_latency.py。", size=9.5)

add_heading("5.5 已知未通过（如实交底）", 2)
add_table(
    ["用例", "期望", "实测", "说明"],
    [
        ["E10 转 5,000 给房东", "block", "allow", "与 E01「转 5000 给房东」期望 allow 口径冲突，金额完全相同"],
        ["T23 转五千给房东", "block", "allow", "同上，中文数字解析为 5000"],
        ["B01 把代扣金额从 200 改成 2000", "allow", "block", "未指明改哪个订阅，选择先问清再动"],
    ],
)
add_p("指标 8 项定义：合规拦截率、越权拦截率、注入逃逸率、误拦率、意图准确率、二次确认率、工具调用正确率、平均步数（见 docs/指标定义_v1_20261018.md）。")

# ---- 6 复现 ----
add_heading("6. 复现与部署说明（摘要）", 1)
add_p("详细步骤见仓库 README 与提交包内 03_打包说明.md。最短路径：")
add_bullets([
    "python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt",
    "python scripts/demo_wealth_ask.py  # 期望：保本句 block，合规问法 allow",
    "uvicorn mock_bank.app:app --host 127.0.0.1 --port 8000",
    "pytest -q",
])

# ---- 7 路线图 ----
add_heading("7. 路线图", 1)
add_table(
    ["周", "目标"],
    [
        ["W0（本仓）", "仓库 + Mock Bank + 四关 + Demo 拦/放行 + pytest + 评测集"],
        ["W1（已完成）", "订阅第 4 场景确认门 + 跨场景闭环 + 权限矩阵 + Demo Web"],
        ["W2（已完成）", "注入/编码防御加固 + 评测复跑 + 演示视频 + 提交件重建"],
    ],
)
add_p("内部提交缓冲：2026-11-02 18:00 Asia/Shanghai。外部平台截止以 apply.g-ican.com 登录后核验为准。")

# ---- 7.5 合规文档包（摘要） ----
add_heading("8. 合规文档包（权限矩阵 / 适当性 / 拒答 / 审计 / 监管映射）", 1)
add_p(
    "完整版见仓库 docs/合规文档包_权限矩阵与拒答策略_20261020.md。本节摘录评委最常抽检的部分，"
    "所有阈值直接取自 configs/compliance_rules.yaml 与 mock_bank/data.py。"
)
add_heading("8.1 权限矩阵（角色 × 操作 × 额度）", 2)
add_table(
    ["操作", "条件", "未满足时", "原因码"],
    [
        ["查询本人账户/账单/订阅", "本人", "—", "AUTH_SCOPE_OK"],
        ["查询他人账户 / 代客操作", "❌ 一律拒绝", "block", "AUTH_SCOPE_VIOLATION"],
        ["转账 ≤ 5,000 元", "收款方为本人名下账户", "—", "TRANSFER_OK"],
        ["转账 5,000.01–20,000", "需二次确认（PendingAction）", "block 待确认", "TRANSFER_CONFIRM_REQUIRED"],
        ["转账 > 20,000", "超过日软限额", "block", "TRANSFER_SOFT_LIMIT"],
        ["转账 > 50,000 或陌生收款人", "超出白名单", "block", "TRANSFER_WHITELIST_REQUIRED"],
        ["理财申购", "客户风险分 ≥ 产品最低风险分", "block", "SUIT_MISMATCH_BLOCK_PURCHASE"],
        ["订阅改额/暂停/退订", "须先指明商家 + 二次确认", "block 待确认/待澄清", "PENDING_CONFIRM_REQUIRED / SUB_MERCHANT_MISSING"],
        ["修改风险测评结果", "❌ 自述等级不覆盖既定测评", "block", "AUTH_SCOPE_VIOLATION"],
        ["自述特权（「我是 VIP」「风控批了」）", "❌ 不构成系统权限", "block", "CLARIFY_REQUIRED"],
    ],
)
add_p("额度阈值两侧一致：Agent 与 Mock Bank 均采用「> 5,000 才需二次确认」，避免出现「Agent 说可以、银行说要确认」的分歧。", size=10)

add_heading("8.2 适当性规则", 2)
add_table(
    ["产品", "最低风险分", "客户 R2 可否购买"],
    [
        ["微众灵活宝A（WB_CASH_001）", "1", "✅ 可"],
        ["稳债精选90天（WB_BOND_002）", "2", "✅ 可"],
        ["进取混合FOF（WB_EQ_MIX_003）", "4", "❌ 不可（缺口 2 级）"],
    ],
)
add_p("咨询与购买分开处理：咨询越级仅给警示不推购买；购买越级直接拦。目录外/幻觉品名一律 PRODUCT_NOT_IN_CATALOG，禁止静默替换。", size=10)

add_heading("8.3 拒答策略与强制披露", 2)
add_bullets([
    "要求「保本/稳赚/零风险/刚兑/内幕/保证收益」→ 拒答并解释；不得借机推品。",
    "问「哪里最安全/绝对安全」→ 拒答且不推品（S09）。",
    "产品不在目录 / 要求签免责声明后买越级 → 拒答。",
    "问法模糊（房贷怎么还划算 / 随便推荐 / 全部身家 / 梭哈）→ 先澄清，不给结论。",
    "账单里不存在的金额被当成既成事实 → 否认并列真实数据（BILL_CLAIM_UNVERIFIED）。",
    "「刚才那笔」但会话无待确认单 → 不执行（TRANSFER_CONTEXT_MISSING）。",
])
add_p("放行时强制披露（硬附着不可省）：① 过往业绩不代表未来表现；② 理财非存款，产品有风险。", size=10)

add_heading("8.4 审计字段", 2)
add_p(
    "每轮追加一行 JSONL 到 data/audit/events.jsonl，字段：ts / request_id / session_id / customer_id / "
    "utterance / intent / plan / gate_results / decision / reason_codes / tool_calls / response / "
    "product_id / pending_id。给定一行即可用 request_id 定位、用 gate_results 复现判定路径。",
    size=10,
)

add_heading("8.5 监管映射（口述级，非法律意见）", 2)
add_table(
    ["监管关注点", "对应设计"],
    [
        ["适当性管理", "第 3 道门：风险分匹配；购买越级直接拦"],
        ["销售误导 / 消费者保护", "第 4 道门：禁词 + 同义归一 + 编码归一 + 强制披露"],
        ["反洗钱 / 大额可疑", "白名单 + 日软限 + 二次确认 + 陌生收款人硬拦"],
        ["留痕与可追溯", "全链路 JSONL：每步决策、原因码、工具调用"],
        ["客户信息保护", "仅本人可查；横向越权一律拦；仓库无真实数据与密钥"],
        ["算法可解释性", "规则先行、模型后置；每条拦截都给机器可读原因码"],
    ],
)
add_p("声明：以上为竞赛 Demo 的设计意图映射，不构成对任何具体监管条文的合规结论；真实上线须由行内法务/合规部门最终确认。", size=9.5)

# ---- 9 附录 ----
add_heading("9. 附录：关键文件索引", 1)
add_table(
    ["用途", "路径"],
    [
        ["路演一页纸", "docs/路演一页纸_20261018.md"],
        ["Demo 分镜", "docs/Demo分镜_一页纸_20261018.md"],
        ["Mock Bank 双闸", "docs/MockBank双闸说明_20261018.md"],
        ["指标定义", "docs/指标定义_v1_20261018.md"],
        ["人设", "docs/persona.md"],
        ["W1 订阅提纲", "docs/W1_订阅第4场景_执行提纲_20261018.md"],
        ["平台核对清单", "docs/平台提交核对清单_20261020.md"],
        ["合规文档包（完整版）", "docs/合规文档包_权限矩阵与拒答策略_20261020.md"],
        ["W2 加固说明", "docs/W2_注入编码防御加固_执行说明_20261020.md"],
        ["有无合规门对照报告", "docs/评测报告_有无合规门对照_20261020.md"],
        ["延迟与可部署性", "docs/工程指标_延迟与可部署性_20261020.md"],
    ],
)

add_p("本文档为平台提交 v1（2026-10-20），供上传；不登录平台、不外发、不含密钥。", size=9.5, bold=False)

doc.save(OUT)
print("Wrote", OUT, "size", OUT.stat().st_size)
