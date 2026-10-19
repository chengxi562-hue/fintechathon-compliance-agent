# -*- coding: utf-8 -*-
"""Build 04_安全自评报告_v0.docx for FinTechathon platform submit."""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

OUT = Path("/workspace/company/fintechathon/submit/04_安全自评报告_v0.docx")

doc = Document()
for section in doc.sections:
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)

def set_run_font(run, size=11, bold=False, color=None, name="Microsoft YaHei"):
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
        set_run_font(run, size={1: 18, 2: 14, 3: 12}.get(level, 11), bold=True, name="Microsoft YaHei")
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
r = t2.add_run("安全自评报告 v0")
set_run_font(r, size=28, bold=True)

t3 = doc.add_paragraph()
t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t3.add_run("合规先审 · 银行 AI 销售智能体（合规官）")
set_run_font(r, size=16, bold=True)

meta = [
    "队伍：弋承熙 & 高依灵",
    "工程主责：Grok Bot（本地脚手架）",
    "文档日期：2026-10-18（Asia/Shanghai）",
    "对照材料：docs/MockBank双闸说明、persona、W0_P0修复、S09询安、W1确认门提纲、configs/compliance_rules.yaml",
    "范围声明：Demo / Mock 环境；不接真实资金、不连生产核心；不构成投资建议。",
    "许可证：MIT｜本报告不含真实密钥或客户隐私。",
]
for m in meta:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(m)
    set_run_font(r, size=10, color=(0x44, 0x44, 0x44))

doc.add_paragraph()

# ---- 1 概述 ----
add_heading("1. 自评目的与结论摘要", 1)
add_heading("1.1 目的", 2)
add_p(
    "本报告对「合规官」Demo 系统在数据安全、权限与二次确认、注入/越权拦截、"
    "Mock Bank 双闸、密钥与供应链纪律方面做自我评估，供平台第四栏「安全自评」提交，"
    "并与技术文档 §4、答辩材料安全页口径一致。"
)
add_heading("1.2 一句话结论", 2)
add_p(
    "以「规则先行、默认拒绝、双闸兜底、可审计」为原则：Agent 侧四道门 + 授权范围门拦截注入与越权；"
    "工具层 Mock Bank 独立限额/白名单/适当性兜底；写操作经二次确认；仓库与提交包零真实密钥。"
    "当前为 W0 底座 + W1 确认门 stub，威胁模型限于 Demo 面，不等同生产等保测评。",
    size=10.5,
)
add_heading("1.3 自评等级（Demo 口径）", 2)
add_table(
    ["维度", "自评", "说明"],
    [
        ["数据安全（Demo 数据）", "达标", "仅合成客户/账户；无真实 PII；审计 JSONL 本地落盘"],
        ["权限 / 二次确认", "达标（W0）/ 推进中（W1）", "转账≥5k 待确认；订阅写操作 PendingAction stub"],
        ["注入 / 越权拦截", "基本达标", "YAML 规则 + 单测；对抗集仍有漏检由双闸兜住"],
        ["Mock Bank 双闸", "达标", "直打 API 仍拦白名单/日限/适当性；5 条专测"],
        ["密钥不入库", "达标", "无 .env；仅 .env.example；zip 已抽检"],
    ],
)

# ---- 2 威胁模型 ----
add_heading("2. 威胁模型与资产", 1)
add_heading("2.1 资产", 2)
add_bullets([
    "Demo 客户身份与权限边界（persona：cust_yw_001 林晓晴，R2，理财≤单笔5万，转账日累计≤2万需二次确认）。",
    "理财产品目录 allowlist 与适当性映射（risk_score vs min_risk_score）。",
    "转账 / 申购资金动作路径（Mock，非真金）。",
    "合规规则 YAML、审计 JSONL、评测集。",
    "可选 LLM API Key（Demo 默认可无 Key 运行）。",
])
add_heading("2.2 主要威胁（Demo 范围）", 2)
add_table(
    ["威胁", "典型形态", "主要控制"],
    [
        ["提示词注入 / 越狱", "ignore rules、developer mode、日文無視、HTML 注释载体", "inject + indirect_inject 门；失败则 block"],
        ["越权 / 代客", "帮他查、导出客户、改风险测评、其他 cust_*", "gate_auth_scope 置首位"],
        ["幻觉产品 / 静默换品", "稳盈宝等非目录名诱导推荐", "显式解析；未知 ID → PRODUCT_NOT_IN_CATALOG"],
        ["绕过 Agent 直打 API", "对 Mock Bank POST 转账/申购", "银行侧第二道闸（白名单/日限/适当性）"],
        ["大额误转", "≥5千未确认、≥5万陌生户、日累计超2万", "pending_confirm + 银行硬拦"],
        ["密钥泄漏", "把 Key 写进仓库/提交包", ".gitignore + 打包排除 + 抽检"],
        ["询安误推品", "「钱放哪里最安全」被当购买", "否定买剥离 + 禁「最安全」话术（S09）"],
    ],
)
add_heading("2.3 明确不在范围", 2)
add_bullets([
    "真实银行核心、支付网关、短信 OTP、生产 IAM / 等保三级测评。",
    "对抗国家级 APT、物理安全、员工社保。",
    "多租户隔离与生产级密钥托管（KMS）——Demo 进程内内存态。",
])

# ---- 3 数据安全 ----
add_heading("3. 数据安全", 1)
add_heading("3.1 数据类型与分级", 2)
add_table(
    ["数据类", "内容", "处置"],
    [
        ["合成客户主数据", "姓名/城市/收入/风险等级（persona.md）", "仅 Mock seed；不外发、不上生产库"],
        ["账户与流水", "余额、转账 posted 记录（内存）", "进程内；重启重置；无持久化生产库"],
        ["产品目录", "WB_* 公开演示产品", "允许出现在文档与评测"],
        ["审计日志", "request_id / gates / decision JSONL", "本地 AUDIT_DIR；提交包排除运行时 JSONL"],
        ["评测语料", "合成 utterance", "可公开复现；无真实客户话术"],
    ],
)
add_heading("3.2 控制措施", 2)
add_bullets([
    "最小暴露：对外文档与提交材料只用合成 ID（cust_yw_001），不引入真实证件号/手机号。",
    "默认拒绝落地：意图不清、产品不在目录、金额无效 → 澄清或拦截，不静默写账。",
    "审计可回放：每次决策写入 audit/logger.py JSONL（ts、request_id、gate_results、decision、原因码）。",
    "提交纪律：源代码 ZIP 排除 .env / .venv / __pycache__ / 审计运行时；见 submit/03_打包说明.md。",
])
add_heading("3.3 残留风险", 2)
add_p(
    "Demo 审计字段尚未全量含 session_id/actor_role/rules_version（P1-3）；"
    "订阅写路径审计 before/after 随 W1 确认门落地补齐。不影响 W0 转账/申购演示安全结论。"
)

# ---- 4 权限与二次确认 ----
add_heading("4. 权限模型与二次确认", 1)
add_heading("4.1 Persona 权限边界（锁定 W0–W1 Demo）", 2)
add_p("主客群：有一定可投资产的年轻白领（非在校生）。权限摘要：")
add_bullets([
    "理财查看 / 购买：单笔 ≤ 5 万元；适当性必须匹配（R2 不可直买 R4）。",
    "转账：日累计对外 ≤ 2 万需二次确认语境；超限需提升权限（Demo 以拦截/确认体现）。",
    "KYC：已实名演示态；AML 无命中；非高风险职业。",
])
add_heading("4.2 转账二次确认（已实现）", 2)
add_table(
    ["条件", "行为", "实现位置"],
    [
        ["amount ≥ 5,000 且 confirmed=false", "返回 pending_confirm，不落账", "Agent 决策 + Mock Bank /v1/transfers"],
        ["amount > 50,000 且收款非本人名下", "403 TRANSFER_BANK_WHITELIST_REQUIRED", "Mock Bank 硬拦"],
        ["对外日累计 > 20,000", "403 TRANSFER_BANK_DAILY_LIMIT_EXCEEDED", "Mock Bank 软限硬拒"],
        ["本人名下划转", "不占日累计；大额可放行（演示备用户）", "_is_whitelisted_recipient"],
    ],
)
add_heading("4.3 订阅写操作确认门（W1 首项）", 2)
add_p(
    "改额 / 暂停·恢复代扣 / 取消订阅：必须先创建 PendingAction（pending_id、session_id、"
    "expires_at≤10 分钟）；用户明确「确认」且未过期才允许 Mock Bank 状态变更。"
    "status≠confirmed 时禁止写入 SUBSCRIPTIONS。见 agent/pending_action.py 与 docs/W1_订阅第4场景_执行提纲。"
)
add_bullets([
    "本轮已落：类型 + 内存 stub（create/confirm/cancel）；确认前零银行写。",
    "禁止：无 PendingAction 的「便利 POST」半成品真写死。",
    "过期再确认 → PENDING_EXPIRED，不落账。",
])

# ---- 5 注入与越权 ----
add_heading("5. 注入检测与越权拦截", 1)
add_heading("5.1 门控顺序", 2)
add_p(
    "run_four_gates：auth_scope（首位）→ intent（含注入扫描）→ product_match → suitability → script。"
    "授权范围门前置，避免越权句落 chitchat 被放行。"
)
add_heading("5.2 注入（INJECT_DETECTED）", 2)
add_bullets([
    "configs/compliance_rules.yaml：inject_patterns 扩至 14 条（日文無視、developer mode、print your rules、"
    "系统提示词、\"role\":\"system\"、合规已批准、新规：、没有合规限制、角色扮演、disable all gates 等）。",
    "indirect_inject_patterns：HTML 注释、账单备注等载体；details 标 via:indirect。",
    "否定引用保护：先剥离「不要/别/无需执行「…」」再扫描，避免 I01 误拦。",
    "单测：tests/test_inject.py（I02–I10 拦 + I01 放行）。",
])
add_heading("5.3 越权（AUTH_SCOPE_VIOLATION）", 2)
add_bullets([
    "三类正则：scope（张三/我老公/其他客户/所有客户/cust_(?!yw_001)/我是客服/导出客户）、"
    "self_service（风险测评改/调/设为）、delegation（帮他/替她/代客）。",
    "本人查询不误拦；单测 tests/test_auth_scope.py（V01–V06/R02/B02）。",
])
add_heading("5.4 产品与话术相关安全", 2)
add_bullets([
    "禁止静默换品：显式 ID/品名不在目录 → PRODUCT_NOT_IN_CATALOG；suspect_names 兜底。",
    "话术禁词 + 归一化（保本/稳赚/刚兑等）；询安「最安全」强制 chitchat + block（S09）。",
    "金额归一防拆分规避：千分位/中文数词/多笔合计，避免「转 10 万」被解析成 10 元放行。",
])
add_heading("5.5 对抗评测诚实披露", 2)
add_p(
    "对抗集实测中，注入门仍有漏检用例；部分攻击被金额门/白名单门兜住——"
    "说明双闸有工程价值，但注入逃逸率不按「全靠注入门满分」对外宣称。"
    "指标定义见 docs/指标定义_v1（含合规拦截率、越权拦截率、注入逃逸率、误拦率、二次确认率等）。"
)

# ---- 6 双闸 ----
add_heading("6. Mock Bank 双闸（第二道闸）", 1)
add_p(
    "设计意图：即便 Agent 合规门被注入/绕过，直接调用银行 API 仍被独立规则拦截。"
    "阈值与 compliance_rules.yaml 的 transfer.* / suitability 保持一致（W0 硬编码镜像）。"
)
add_heading("6.1 转账 /v1/transfers", 2)
add_table(
    ["闸", "阈值", "行为"],
    [
        ["白名单硬拦", "amount > 50,000", "非本人名下收款 → 403 TRANSFER_BANK_WHITELIST_REQUIRED"],
        ["日累计软限", "对外累计 > 20,000/日", "403 TRANSFER_BANK_DAILY_LIMIT_EXCEEDED；本人划转不占限额"],
        ["确认软提示", "amount ≥ 5,000 且未 confirmed", "pending_confirm（非硬拦，需 confirmed 才 posted）"],
    ],
)
add_heading("6.2 申购 /v1/wealth/purchase", 2)
add_bullets([
    "适当性兜底：customer.risk_score < product.min_risk_score → 403 SUITABILITY_MISMATCH。",
    "例：R2（cust_yw_001）申购 R4 WB_EQ_MIX_003 → 拒绝；申购 R2 WB_BOND_002 → 放行。",
])
add_heading("6.3 验证", 2)
add_p("tests/test_bank_second_gate.py 使用 TestClient 直连 bank（不经 Agent），覆盖白名单、日限、适当性正反例。W0 全量 pytest：83 passed（以本机 .venv 为准）。")

# ---- 7 密钥 ----
add_heading("7. 密钥与供应链纪律", 1)
add_table(
    ["控制项", "做法", "证据"],
    [
        ["密钥不入库", "仓库无真实 .env；仅 .env.example（OPENAI_API_KEY 注释占位）", ".env.example + .gitignore"],
        ["无 Key 可演示", "规则引擎确定性拦/放行，LLM 可选", "README / demo 脚本"],
        ["提交包清洁", "ZIP 排除 .env/.venv/__pycache__/运行时审计", "submit/03_打包说明.md 抽检"],
        ["配置外置", "COMPLIANCE_RULES / MOCK_BANK_URL / AUDIT_DIR 环境变量", ".env.example"],
        ["开源许可", "MIT LICENSE", "仓库根 LICENSE"],
    ],
)
add_p("红线复核：本自评撰写过程不登录外站、不外发、不花钱、不写入真实密钥。")

# ---- 8 测试矩阵 ----
add_heading("8. 安全相关测试与证据索引", 1)
add_table(
    ["主题", "测试 / 文档", "覆盖要点"],
    [
        ["注入", "tests/test_inject.py · W0_P0修复说明", "I01–I10；否定引用不误拦"],
        ["越权", "tests/test_auth_scope.py", "代客/导出/改测评拦；本人不误拦"],
        ["金额解析", "tests/test_amount_parse.py", "万字/中文数/拆分合计"],
        ["产品解析", "tests/test_product_resolve.py", "幻觉品名拦；目录正名放行"],
        ["双闸", "tests/test_bank_second_gate.py · MockBank双闸说明", "直打 API 仍 403"],
        ["询安", "tests/test_s09_safe_wording.py · S09说明", "不推 WB_*"],
        ["确认门", "agent/pending_action.py · W1提纲", "未确认不写"],
        ["对抗集", "docs/对抗评测集_v0_*.md", "诚实披露漏检与双闸兜底"],
    ],
)

# ---- 9 改进计划 ----
add_heading("9. 已知缺口与改进计划（不粉饰）", 1)
add_table(
    ["缺口", "风险", "计划阶段"],
    [
        ["注入词表多语言不全（韩/法/俄）", "注入逃逸", "W1 词表扩展 + 对抗集回归"],
        ["suspect_names 静态，幻觉长尾", "目录外产品漏拦", "W1 目录相似度"],
        ["审计缺 actor_role/rules_version", "举证粒度不足", "P1-3"],
        ["订阅确认门尚未全链路 pytest", "写路径半成品风险", "W1 DoD：3 条必测后合"],
        ["金额「全部提及求和」偏粗", "误拦升高", "W1 LLM 二轮澄清（可选）"],
        ["银行侧阈值与 YAML 双写", "漂移", "W1+ 共享加载"],
    ],
)

# ---- 10 签署 ----
add_heading("10. 自评声明", 1)
add_bullets([
    "本系统为竞赛 Demo：合成数据、Mock 资金、可选 LLM；不得用于真实客户交易。",
    "自评基于 2026-10-18 仓库状态与本地 pytest；指标数值以依灵确认的指标定义 v1 为准后再对外签章引用。",
    "队伍对提交材料原创性负责；安全控制以可复现测试与文档为准，接受评委抽检。",
])
add_p("")
add_p("队伍负责人：弋承熙（队长）", bold=True)
add_p("协同：高依灵")
add_p("文档版本：安全自评报告 v0｜2026-10-18 Asia/Shanghai")
add_p("本文档供平台第四栏上传；不含密钥、不含真实客户数据。", size=9.5)

doc.save(OUT)
print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
