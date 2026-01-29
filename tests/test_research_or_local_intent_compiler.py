import pytest

from agentos.research_or_local_intent_compiler import (
    ResearchOrLocalIntentCompiler,
    _ruleset_hash,
)
from agentos.intent_classes import (
    DEFAULT_MAX_RESULTS,
    REFUSAL_AMBIGUOUS_MODE,
    REFUSAL_FORBIDDEN_NO_NETWORK_FALSE,
    REFUSAL_FORBIDDEN_READ_ONLY_FALSE,
    REFUSAL_MISSING_QUERY,
    REFUSAL_NO_MODE_MATCH,
    REFUSAL_OUT_OF_BOUNDS_MAX_RESULTS,
    REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX,
)
from agentos.intent_compiler_contract import CompiledIntent, CompilationRefusal


def test_ruleset_hash_is_stable_and_matches_function():
    c = ResearchOrLocalIntentCompiler()
    assert c.compiler_ruleset_hash == _ruleset_hash()


def test_compile_research_success_default_constraints():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search papers about ichimoku")
    assert isinstance(out, CompiledIntent)
    ps = out.plan_spec
    assert ps["intent_class"] == "ResearchOrLocalIntentV1"
    assert ps["intent_class_version"] == 1
    assert ps["mode"] == "research"
    assert ps["delegate"]["role"] == "scout"
    assert ps["delegate"]["action"] == "external_research"
    assert ps["constraints"]["max_results"] == DEFAULT_MAX_RESULTS
    assert ps["constraints"]["no_network"] is True
    assert ps["constraints"]["read_only"] is True
    assert out.output_hash


def test_compile_local_exec_success_default_constraints():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("run pytest on the repo")
    assert isinstance(out, CompiledIntent)
    ps = out.plan_spec
    assert ps["mode"] == "local_exec"
    assert ps["delegate"]["role"] == "envoy"
    assert ps["delegate"]["action"] == "deterministic_local_execution"
    assert ps["constraints"]["max_results"] == DEFAULT_MAX_RESULTS
    assert ps["constraints"]["no_network"] is True
    assert ps["constraints"]["read_only"] is True
    assert out.output_hash


def test_compile_refuses_ambiguous_mode():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search citations and run pytest")
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason == REFUSAL_AMBIGUOUS_MODE


def test_compile_refuses_no_mode_match():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("hello world")
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason == REFUSAL_NO_MODE_MATCH


@pytest.mark.parametrize("s", ["search", "run", "look up", "execute"])
def test_compile_refuses_missing_query_when_only_trigger(s):
    c = ResearchOrLocalIntentCompiler()
    out = c.compile(s)
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason == REFUSAL_MISSING_QUERY


def test_compile_parses_max_results_equals_syntax():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search papers max_results=5 about volatility")
    assert isinstance(out, CompiledIntent)
    assert out.plan_spec["constraints"]["max_results"] == 5


def test_compile_parses_max_results_whitespace_syntax():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search papers max_results 7 about volatility")
    assert isinstance(out, CompiledIntent)
    assert out.plan_spec["constraints"]["max_results"] == 7


def test_compile_refuses_max_results_out_of_bounds_low():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search papers max_results=0 about volatility")
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason == REFUSAL_OUT_OF_BOUNDS_MAX_RESULTS


def test_compile_refuses_max_results_out_of_bounds_high():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search papers max_results=999 about volatility")
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason == REFUSAL_OUT_OF_BOUNDS_MAX_RESULTS


def test_compile_refuses_unknown_constraint_key():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search papers foo=1 about volatility")
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason.startswith(REFUSAL_UNSUPPORTED_CONSTRAINT_PREFIX)


def test_compile_refuses_no_network_false():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("search papers no_network=false about volatility")
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason == REFUSAL_FORBIDDEN_NO_NETWORK_FALSE


def test_compile_refuses_read_only_false():
    c = ResearchOrLocalIntentCompiler()
    out = c.compile("run pytest read_only=false")
    assert isinstance(out, CompilationRefusal)
    assert out.refusal_reason == REFUSAL_FORBIDDEN_READ_ONLY_FALSE


def test_compile_accepts_injected_intent_sha256():
    c = ResearchOrLocalIntentCompiler()
    injected = "aa" * 32
    out = c.compile("search papers about volatility", intent_sha256=injected)
    assert out.intent_sha256 == injected
