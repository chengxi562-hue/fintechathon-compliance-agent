from agent import pending_action as pa
from demo_web.app import SCENARIOS, run_scenario, build


def setup_function():
    pa.clear_store()


def test_four_buttons_three_scenes_plus_block():
    assert len(SCENARIOS) == 4


def test_interception_blocks():
    _, trace = run_scenario("④ 拦截演示：保本诱导（合规门拦截）")
    assert '"decision": "block"' in trace


def test_cross_scene_allow_no_write():
    _, trace = run_scenario("③ 跨场景：账单洞察 → 货基建议（零资金写）")
    assert "bill_insight" in trace and "transfer_apply" not in trace


def test_all_scenarios_run_and_ui_builds():
    for n in SCENARIOS:
        chat, _ = run_scenario(n)
        assert chat
    build()


def test_subscription_confirm_gate():
    import json
    _, t = run_scenario("② 订阅管理 + 二次确认（写操作需确认）")
    r = json.loads(t)
    assert r[1]["pending_id"] and r[2]["decision"] == "allow"
