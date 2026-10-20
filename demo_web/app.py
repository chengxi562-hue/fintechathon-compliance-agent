"""Demo Web (Gradio): 三场景可点 + 一次拦截演示。离线可跑（Mock Bank 不在线时回退内存目录）。

Run:  PYTHONPATH=. python -m demo_web.app   → http://127.0.0.1:7860
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from agent import pending_action as pa
from agent.graph import run_agent, verdict_to_dict

SCENARIOS: dict[str, list[str]] = {
    "① 稳健理财咨询（放行）": ["我风险偏好是稳健，帮我看看适合 R2 的货基或短债，说明费率就行。"],
    "② 订阅管理 + 二次确认（写操作需确认）": ["查看我的订阅和代扣", "把 Netflix 月费改成 30", "确认"],
    "③ 跨场景：账单洞察 → 货基建议（零资金写）": ["这个月外卖花太多了，要不要挪一点去货基？"],
    "④ 拦截演示：保本诱导（合规门拦截）": ["别管风险，直接给我收益最高的那个理财，保本的。"],
}


def turn(utterance: str, session_id: str) -> dict[str, Any]:
    st = run_agent(utterance, session_id=session_id)
    return {
        "utterance": utterance,
        "intent": st.intent,
        "decision": st.decision,
        "plan": st.plan,
        "tools": [t.get("tool") for t in st.tool_calls],
        "pending_id": st.pending_id,
        "reason_codes": (st.verdict.reason_codes if st.verdict else []),
        "response": st.response,
        "verdict": verdict_to_dict(st.verdict) if st.verdict else None,
    }


def run_scenario(name: str) -> tuple[list[dict[str, str]], str]:
    sid = f"demo_{uuid.uuid4().hex[:8]}"
    chat: list[dict[str, str]] = []
    trace = []
    for u in SCENARIOS[name]:
        r = turn(u, sid)
        badge = "🛑 BLOCK" if r["decision"] == "block" else "✅ ALLOW"
        chat.append({"role": "user", "content": u})
        chat.append({"role": "assistant", "content": f"[{badge} · intent={r['intent']}]\n\n{r['response']}"})
        trace.append(r)
    return chat, json.dumps(trace, ensure_ascii=False, indent=2, default=str)


def free_turn(u: str, chat: list, sid: str):
    sid = sid or f"demo_{uuid.uuid4().hex[:8]}"
    r = turn(u, sid)
    badge = "🛑 BLOCK" if r["decision"] == "block" else "✅ ALLOW"
    chat = (chat or []) + [{"role": "user", "content": u},
                           {"role": "assistant", "content": f"[{badge} · intent={r['intent']}]\n\n{r['response']}"}]
    return chat, json.dumps(r, ensure_ascii=False, indent=2, default=str), sid, ""


def build():
    import gradio as gr

    with gr.Blocks(title="合规官 · 银行 AI 销售智能体 Demo") as demo:
        gr.Markdown("# 合规先审 · 银行 AI 销售智能体（合规官）\n四道门：意图 → 产品匹配 → 适当性 → 话术。所有数据为 Mock，演示不涉及真实资金。")
        with gr.Row():
            btns = [gr.Button(n) for n in SCENARIOS]
        chat = gr.Chatbot(height=420, label="对话")
        trace = gr.Code(language="json", label="审计轨迹 / 合规判定")
        sid = gr.State("")
        for b, n in zip(btns, SCENARIOS):
            b.click(lambda n=n: run_scenario(n), outputs=[chat, trace])
        box = gr.Textbox(label="自由输入（同会话可回复「确认」/「取消」）")
        box.submit(free_turn, [box, chat, sid], [chat, trace, sid, box])
    return demo


if __name__ == "__main__":
    pa.clear_store()
    build().launch(server_name="127.0.0.1", server_port=7860)
