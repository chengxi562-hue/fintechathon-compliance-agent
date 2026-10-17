from agent.graph import run_agent, verdict_to_dict

def test_small_internal_transfer_allows():
    s = run_agent("把 100 元转到自己活期备用金。")
    assert s.intent == "transfer"
    assert s.decision == "allow"
    assert s.verdict and s.verdict.allowed is True
    assert "TRANSFER_OK" in (s.verdict.reason_codes if s.verdict else [])

def test_stranger_large_transfer_blocks():
    s = run_agent("转 60000 给陌生人。")
    assert s.intent == "transfer"
    assert s.decision == "block"
    assert s.verdict and s.verdict.allowed is False
    d = verdict_to_dict(s.verdict)
    assert d["allowed"] is False
    assert "TRANSFER_WHITELIST_REQUIRED" in d["reason_codes"]

def test_confirm_threshold_blocks():
    s = run_agent("付给房东房租 5500。")
    assert s.intent == "transfer"
    assert s.decision == "block"
    assert s.verdict and s.verdict.allowed is False
    assert "TRANSFER_CONFIRM_REQUIRED" in s.verdict.reason_codes
