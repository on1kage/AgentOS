from agentos.intent_compiler_contract import CompilationRefusal

def test_parse_proposed_intent_accepts_minimal():
    res = parse_proposed_intent_v1("x", {"mode": "research", "query": "q"})
    assert res.mode == "research"
    assert res.query == "q"

def test_parse_proposed_intent_rejects_unknown_keys():
    res = parse_proposed_intent_v1("x", {"mode": "research", "query": "q", "extra": 1})
    assert isinstance(res, CompilationRefusal)
    assert res.refusal_reason.startswith("refusal:proposed_intent:unknown_keys:")

def test_parse_proposed_intent_rejects_out_of_bounds_max_results():
    res = parse_proposed_intent_v1("x", {"mode": "research", "query": "q", "max_results": 999})
    assert isinstance(res, CompilationRefusal)
    assert res.refusal_reason == "refusal:proposed_intent:max_results_out_of_bounds"
