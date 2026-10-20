# GitHub 开源参考（FinTechathon · 合规先审银行 Agent）

> 检索日期：2026-10-16（Asia/Shanghai）  
> 目标栈：`<repo-root>`（四道门 intent→product→suitability→script + Mock Bank + JSONL 审计 + LangGraph-ready）  
> 用法：**借鉴架构与评测思路**；默认只读 / 对照，不把整仓 vendoring 进本树。  
> **许可证红线**：未核对许可证前不要拷贝代码；**GPL / AGPL 代码不得并入本仓库**（除非单独注明并隔离，且比赛交付允许）。Apache-2.0 / MIT 可参考实现思路，合并前仍要保留 NOTICE/版权头。

星标数为检索当日 GitHub API 快照，会变动。

---

## Top 推荐（按对本栈价值排序）

### 1. open-compass/CNFinBench — ★21 · 许可证未在仓库标明（用前再核）

- Clone: `https://github.com/open-compass/CNFinBench.git`
- HTTPS: https://github.com/open-compass/CNFinBench
- 镜像/姊妹仓：https://github.com/VertiAIBench/CNFinBench （★~10）
- 论文：KDD 2026 / arXiv:2512.09506；榜单：https://cnfinbench.opencompass.org.cn/home
- **为何有用**：赛道叙事高度同构——Expertise / **Autonomy**（Intent→Plan→Tool→Verification）/ **Integrity**（即时拦截、合规持续性、多轮对抗）。`multi-turn/` 下的对抗评测与 LLM-as-Judge 可直接启发我们的自动评测集（保本诱导、越权转账、注入绕门）。
- **对本栈**：优先抄「任务taxonomy + 多轮攻击剧本」，不要依赖未标明许可证的数据文件直接进交付包；评测脚本可自写对齐其维度。

### 2. look378/finance-intelligent-agent — ★23 · MIT ✅

- Clone: `https://github.com/look378/finance-intelligent-agent.git`
- HTTPS: https://github.com/look378/finance-intelligent-agent
- **为何有用**：**中文财富管理 + LangGraph StateGraph** 的最近邻参考。显式覆盖：意图识别/槽位、函数调用、混合 RAG+GraphRAG、**保本/稳赚类话术检测**、PII 脱敏、**合规护栏 + 审计日志**、Docker Compose——与我们「先审后答」几乎同场景。
- **对本栈**：对照其 9-node 图与 input/output guardrail 切分，补强 `agent/graph.py` 与 `gates.py` 的「话术门 / 注入门」；RAG 产品说明书路径可参考其 ToolRegistry，别整仓复制。

### 3. AI4Finance-Foundation/FinRobot — ★8233 · Apache-2.0 ✅

- Clone: `https://github.com/AI4Finance-Foundation/FinRobot.git`
- HTTPS: https://github.com/AI4Finance-Foundation/FinRobot
- **为何有用**：成熟的金融 Agent 平台（含 robo-advisor 向），多 Agent 编排与金融工具调用样例丰富，适合借「Agent 角色拆分 / 工具边界」而不是借交易策略。
- **对本栈**：参考如何把「销售 / 分析 / 风控」拆节点；**不要**把交易执行链路搬进银行销售演示。Apache-2.0 可借鉴代码结构，合并需保留版权声明。

### 4. NVIDIA-NeMo/Guardrails — ★7310 · Apache-2.0 ✅（见 `LICENSE.md` / `LICENSE-Apache-2.0.txt`）

- Clone: `https://github.com/NVIDIA-NeMo/Guardrails.git`
- HTTPS: https://github.com/NVIDIA-NeMo/Guardrails
- **为何有用**：可编程对话护栏（Colang 规则、话题锁定、输入输出轨）。适合把 YAML 规则升级为「可声明的话术/话题门」，与 `configs/compliance_rules.yaml` 互补。
- **对本栈**：用作 **script / inject 门** 的设计参考或可选运行时；W0 仍以确定性正则+规则为主，后期可接一层 NeMo rails。注意第三方组件见仓库 `LICENCES-3rd-party`。

### 5. protectai/llm-guard — ★3216 · MIT ✅

- Clone: `https://github.com/protectai/llm-guard.git`
- HTTPS: https://github.com/protectai/llm-guard
- **为何有用**：成熟的 LLM 交互安全工具包（prompt injection、毒性、PII 等 scanner）。直接对标我们 gate1「intent / inject」。
- **对本栈**：可把其 injection scanner 接到 `gate_intent` 前后；保持「规则门优先、模型门兜底」以免评测不稳定。姊妹项目 **protectai/rebuff**（★~1529 · Apache-2.0）可作注入检测对照：`https://github.com/protectai/rebuff.git`。

### 6. SebAustin/fsi-compliance-agent — ★1 · MIT ✅（星少但架构极贴）

- Clone: `https://github.com/SebAustin/fsi-compliance-agent.git`
- HTTPS: https://github.com/SebAustin/fsi-compliance-agent
- **为何有用**：LangGraph 合规审查：**引经据典（citation）**、不确定则 **abstain→人工**、高风险 **approval gate**、**hash-chain 审计日志**、评测盯 **false-negative（漏拦）**——与我们「可审计、漏拦比准确率更重要」一致。
- **对本栈**：重点借鉴审计链式哈希与「无引用则拒判」合约，强化 `audit/logger.py`；规则书是合成数据，勿当真实监管文本。

### 7. AI4Finance-Foundation/FinRAG — ★63 · Apache-2.0 ✅

- Clone: `https://github.com/AI4Finance-Foundation/FinRAG.git`
- HTTPS: https://github.com/AI4Finance-Foundation/FinRAG
- **为何有用**：金融 RAG 专用脚手架，适合「理财产品说明书 / 风险揭示」检索后再进 product_match / suitability。
- **对本栈**：产品白名单仍以 Mock Bank catalog 为准；RAG 只作解释层，**禁止**用检索结果绕过 allowlist。

### 8. The-FinAI/FinBen（+ PIXIU）— FinBen ★18 · MIT ✅；PIXIU ★894 · MIT ✅

- FinBen clone: `https://github.com/The-FinAI/FinBen.git` — https://github.com/The-FinAI/FinBen  
  （经典 FinBench / financial LLM holistic benchmark，arXiv:2402.12659）
- PIXIU clone: `https://github.com/The-FinAI/PIXIU.git` — https://github.com/The-FinAI/PIXIU  
  （金融指令数据 + 评测套件；原 ChanceFocus/PIXIU 已迁至 The-FinAI）
- **为何有用**：补齐「英文/国际 FinBench」与中文 CNFinBench 的对照评测材料；比赛材料里可写「对齐 FinBen/CNFinBench 的 Integrity 维度」。
- **对本栈**：作评测题库灵感；不必全量跑通，抽与销售话术、适当性相关子集即可。

---

## 次选 / 按需翻阅（不进 Top，但有用）

| 仓库 | ★（约） | License | 一句话 |
|------|--------|---------|--------|
| [databricks-industry-solutions/banking-agent-accelerator](https://github.com/databricks-industry-solutions/banking-agent-accelerator) | 10 | 仓库标 NOASSERTION（依赖多为 Apache/MIT，**合并前读 LICENSE**） | 确定性 stage-driven LangGraph + 异步 HITL checkpoint，私人银行受益人/提额场景 |
| [Azure-Samples/agent-openai-java-banking-assistant-langgraph4j](https://github.com/Azure-Samples/agent-openai-java-banking-assistant-langgraph4j) | 27 | MIT | 银行助手参考（Java/LangGraph4j）；思路可迁，语言栈不匹配 |
| [redis-developer/banking-agent-semantic-routing-demo](https://github.com/redis-developer/banking-agent-semantic-routing-demo) | 3 | MIT | 语义路由 + 槽位填充的银行对话编排 |
| [AI4Finance-Foundation/FinGPT](https://github.com/AI4Finance-Foundation/FinGPT) | 21410 | MIT | 金融 LLM 底座；本赛重合规 Agent，不作主依赖 |
| [Duxiaoman-DI/XuanYuan](https://github.com/Duxiaoman-DI/XuanYuan) | 1324 | 未标明 | 中文金融对话模型资料；许可证不清，**勿拷代码** |

---

## 明确不建议并入本树的类型

- **交易/量化向**（如 TradingAgents 等）：赛道是银行销售合规 Agent，不是炒股多空辩论。
- **许可证不明或 GPL/AGPL**：不可直接 vendor；仅可阅读思路。CNFinBench / XuanYuan / Databricks accelerator 等需二次确认后再考虑任何文件拷贝。
- **仅安全通用、无金融语义的小众 guard**（星标很低）：优先 llm-guard / NeMo / 自研 YAML 规则。

---

## 建议落地顺序（工程）

1. **评测对齐**：CNFinBench Integrity 维度 → 自建 20～50 条中文对抗用例（保本、越权、注入、适当性错配）。  
2. **架构对照**：`finance-intelligent-agent` + `fsi-compliance-agent` → 补图节点与审计哈希。  
3. **护栏增强**：llm-guard（注入）± NeMo rails（话术话题）。  
4. **知识层**：FinRAG 思路挂产品说明书；**永远**经 product allowlist + suitability 门。  
5. **可选平台参考**：FinRobot 角色拆分（只读架构，不引入交易）。

### 快速 clone（只读参考目录示例，勿混进 src）

```bash
mkdir -p <repo-root>/.refs && cd <repo-root>/.refs
# MIT / Apache-2.0 优先
git clone --depth 1 https://github.com/look378/finance-intelligent-agent.git
git clone --depth 1 https://github.com/SebAustin/fsi-compliance-agent.git
git clone --depth 1 https://github.com/protectai/llm-guard.git
git clone --depth 1 https://github.com/NVIDIA-NeMo/Guardrails.git
git clone --depth 1 https://github.com/AI4Finance-Foundation/FinRAG.git
git clone --depth 1 https://github.com/AI4Finance-Foundation/FinRobot.git
git clone --depth 1 https://github.com/The-FinAI/FinBen.git
git clone --depth 1 https://github.com/open-compass/CNFinBench.git   # 许可证未标明：只读，勿拷进交付
echo ".refs/" >> <repo-root>/.gitignore  # 若尚未忽略
```

---

## 检索关键词（可复跑）

`CNFinBench` · `FinBen` · `PIXIU` · `langgraph banking agent` · `financial advisor langgraph` · `finance-intelligent-agent` · `fsi-compliance-agent` · `NeMo Guardrails` · `llm-guard prompt injection` · `FinRAG` · `FinRobot` · `suitability agent finance`
