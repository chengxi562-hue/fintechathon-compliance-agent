# 合规先审 · 银行 AI 销售智能体（合规官）
# Compliance-First Bank AI Sales Agent (“Compliance Officer”)

> FinTechathon 2026 · 赛道：银行 AI 智能体（AI Banking Agent）  
> 队伍：弋承熙 & 高依灵 · 工程主责：Grok Bot  
> 阶段：**W1/W2 完成**（2026-10-20）：四场景 + Demo Web + 注入/编码防御加固
> 所有客户数据均为合成 Mock，不含真实个人信息或密钥。


## 一句话 / One-liner

**中文**：不做“会聊天的理财客服”，做“先审后答、可审计、能过自动评测”的银行销售 Agent。  
**EN**: Not a chatty wealth FAQ bot — a **pre-check, auditable** bank sales agent that can pass automated evals.

四道合规门：**意图 → 产品匹配 → 适当性 → 话术**  
Four gates: **intent → product match → suitability → script**

演示客群（已锁定）：有一定可投资产的**年轻白领**（非在校生）。见 [`docs/persona.md`](docs/persona.md)。  
Demo persona (locked): **young white-collar with investable assets** (not students). See [`docs/persona.md`](docs/persona.md).

## 冲奖交付件索引 / Deliverables

> 仓库实际路径为 `fintechathon/`（冲奖计划旧名已废弃，以本目录为准）。

| 交付件 | 路径 | 状态 |
|--------|------|------|
| 对抗评测集 v0.1（103 条，全部真跑实测） | [`docs/对抗评测集_v0_20261018.md`](docs/对抗评测集_v0_20261018.md) | ✅ P/F 逐条，原始输出 `data/evals/_probe_adv_v0.json` |
| 评测集 v0 草案（70 条 + 指标口径 §4） | [`docs/评测集_v0_草案_20261018.md`](docs/评测集_v0_草案_20261018.md) | ✅ 机器核对 P36/F34 |
| Demo 分镜一页纸 | [`docs/Demo分镜_一页纸_20261018.md`](docs/Demo分镜_一页纸_20261018.md) | ✅ |
| W0 问题清单执行卡 | [`docs/W0问题清单执行卡_20261018.md`](docs/W0问题清单执行卡_20261018.md) | ✅ |
| 平台提交核对清单 | [`docs/平台提交核对清单_20261020.md`](docs/平台提交核对清单_20261020.md) | 🟡 apply.g-ican.com 字段【需 Scott 登录】 |
| 指标定义 v1（8 指标独立成文） | [`docs/指标定义_v1_20261018.md`](docs/指标定义_v1_20261018.md) | 🟡【待依灵确认】 |


---

## 目录结构 / Layout

```
fintechathon/
├── README.md
├── docker-compose.yml          # Mock Bank 一键起
├── Dockerfile
├── requirements.txt
├── configs/compliance_rules.yaml
├── docs/persona.md
├── mock_bank/                  # FastAPI：账户 / 转账 / 理财
├── agent/                      # LangGraph-ready 状态机 + 四关
├── audit/                      # JSONL 审计
├── data/audit/                 # events.jsonl（运行时生成）
├── scripts/demo_wealth_ask.py  # 问理财 → 拦/放行
└── tests/                      # pytest 占位 + W0 smoke
```

---

## Demo Web（Gradio）

```bash
pip install -r requirements.txt
PYTHONPATH=. python -m demo_web.app   # 打开 http://127.0.0.1:7860
```

四个按钮：① 稳健理财咨询（放行）② 订阅修改 + 二次确认 ③ 跨场景账单洞察→货基建议（零资金写）④ 保本诱导拦截。右侧/下方展示意图、计划、工具调用与合规 reason codes 审计轨迹。

## 测试与评测

```bash
PYTHONPATH=. pytest -q                      # 135 passed
PYTHONPATH=. python scripts/run_eval_v1.py  # 评测集 v1：P168 / F3 / SKIP2（173 条，未美化）
```

> **跑测试不需要、也不应该连 Mock Bank**：`tests/conftest.py` 会把 `MOCK_BANK_URL` 指到一个空端口，
> 走文档里写的离线回退路径。这样「先起 Mock Bank 再跑 pytest」不会互相干扰（2026-10-20 修）。

## 快速开始 / Quick start

### 0) 依赖

```bash
cd <repo-root>
python3 -m venv .venv && source .venv/bin/activate   # 所有复现/评测脚本均在 .venv 中运行
pip install -r requirements.txt
```

### 1) 仅跑合规演示（可不启 Mock Bank）

离线会回退到内存产品目录：

```bash
python scripts/demo_wealth_ask.py
```

期望：第一条 **block**（含「保本」），第二条 **allow**（R2 货基/短债），并写入 `data/audit/events.jsonl`。

### 2) 启动 Mock Bank（本机）

```bash
uvicorn mock_bank.app:app --host 127.0.0.1 --port 8000
# 另开终端
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/v1/wealth/products | head
python scripts/demo_wealth_ask.py
```

### 3) Docker Compose（可选，需要本机已装 Docker）

```bash
docker compose up --build
# Mock Bank → http://127.0.0.1:8000
```

> **本工程未在 Docker 内验证过**（提交机无 Docker）。评委请优先走上面的 venv 路径，
> 该路径已在全新虚拟环境中实测：装依赖 → `135 passed`。

### 4) 测试

```bash
PYTHONPATH=. pytest -q     # 135 passed
```

与第 2 步的 Mock Bank 互不影响：测试会自行避开 8000 端口。

---

## 两个进程 vs 一个进程：状态写在哪

这是本工程最容易看错的地方，先说清：

| 场景 | 资金/订阅状态存在哪 | 谁能看到写入 |
|---|---|---|
| `pytest` / `scripts/demo_wealth_ask.py` / `scripts/run_eval_v1.py` | **本进程内存**（`mock_bank/data.py` 的 seed） | 只有本进程；进程退出即复原 |
| `uvicorn mock_bank.app:app` 单独起服务 + Agent 指向它 | **服务进程内存** | 所有连到该服务的客户端 |

所以：

- 不启 Mock Bank 时，Agent 走离线回退，`确认` 会把订阅改在**本进程**的 seed 上——演示够用。
- 启了 Mock Bank 后，`确认` 的写入落在**服务进程**里。此时在本进程打印 `store.SUBSCRIPTIONS` 仍然看到旧值，
  **这是正常的，不是 bug**。要看真实结果，请查服务端：

```bash
curl -s http://127.0.0.1:8000/v1/customers/cust_yw_001/subscriptions
```

`MOCK_BANK_URL` 环境变量控制 Agent 连哪个地址（默认 `http://127.0.0.1:8000`）。

---

## 架构 / Architecture

```
User utterance
    → Intent classify
    → Plan (explicit steps)
    → Compliance Gate ×4  (YAML rules)
         1. intent / inject
         2. product catalog allowlist
         3. suitability (risk_score vs product)
         4. script (禁「保本/稳赚…」+ 披露提示)
    → Tools (Mock Bank HTTP) only if allowed
    → Explain + Audit JSONL
```

`agent/graph.py` 已按未来 **LangGraph** 节点切分；W0 用纯 Python 状态机，保证无 LLM Key 也可演示拦/放行。

---

## Mock Bank API（节选）

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/v1/customers/{id}` | 客户（含 risk_score） |
| GET | `/v1/accounts/{id}` | 账户余额 |
| GET | `/v1/wealth/products` | 理财目录 |
| POST | `/v1/transfers` | 转账（大额需 confirmed） |
| POST | `/v1/wealth/purchase` | 申购（适当性由 Agent 门执行） |

Seed 客户：`cust_yw_001`（林晓晴，R2，深圳白领）。

---

## 审计 / Audit

每次 `run_agent` 追加一行 JSONL 至 `data/audit/events.jsonl`，字段含：`ts, request_id, utterance, intent, plan, gate_results, decision, reason_codes, tool_calls, response`。

---

## 路线图对齐 / Roadmap

| 周 | 目标 |
|----|------|
| **W0**（本仓） | 仓库 + Mock Bank + 四关骨架 + 1 条问理财拦/放行 + pytest 占位 |
| W1 | **订阅第 4 场景（首项·改额/代扣需确认门）** + 理财 / 受控转账 / 跨场景闭环 + 权限矩阵 + Demo UI |
| W2 | 评测集强化 + 演示视频 |

内部提交截止：**2026-11-02 18:00 Asia/Shanghai**。

---

## 许可 / License

**MIT License** — Copyright (c) 2026 弋承熙 / Chengxi Yi.  
详见根目录 [`LICENSE`](LICENSE)。
