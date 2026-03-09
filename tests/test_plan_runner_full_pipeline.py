import os
import pytest
from agentos.plan_runner_full_pipeline import run_full_pipeline

def test_full_pipeline_success(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    os.environ["AGENTOS_INTENT_SOURCE"] = "planspec_v1"
    os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
    try:
        payload = {
            "intent_text": "search for papers",
            "plan_spec": {"role": "scout", "action": "external_research", "metadata": {"query": "papers", "max_results": 3}},
        }
        result = run_full_pipeline(payload)
        assert "compiled_intent" in payload
        assert "intent_compilation_manifest_sha256" in payload
        assert result is not None
        assert getattr(result, "ok", None) is True
    finally:
        os.environ.pop("AGENTOS_INTENT_SOURCE", None)
        if old_store is None:
            os.environ.pop("AGENTOS_STORE_ROOT", None)
        else:
            os.environ["AGENTOS_STORE_ROOT"] = old_store

def test_full_pipeline_blocks_legacy_intake_when_intent_source_unset(tmp_path):
    old_store = os.environ.get("AGENTOS_STORE_ROOT")
    os.environ["AGENTOS_STORE_ROOT"] = str(tmp_path / "store")
    try:
        payload = {"intent_text": "do something unknown"}
        result = run_full_pipeline(payload)
        assert result is not None
        assert getattr(result, "ok", None) is False
        assert result.decisions[0]["stage"] == "intent_source_gate"
        assert result.decisions[0]["reason"] == "legacy_path_blocked:intent_source_unset"
        assert getattr(result, "verification_manifest_sha256", None)
    finally:
        if old_store is None:
            os.environ.pop("AGENTOS_STORE_ROOT", None)
        else:
            os.environ["AGENTOS_STORE_ROOT"] = old_store

def test_planspec_success_authorized(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTOS_INTENT_SOURCE", "planspec_v1")
    monkeypatch.setenv("AGENTOS_STORE_ROOT", str(tmp_path / "store"))
    payload = {
        "intent_text": "any text (ignored by planspec path)",
        "plan_spec": {"role": "morpheus", "action": "verification", "metadata": {}},
    }
    result = run_full_pipeline(payload)
    assert result is not None
    assert getattr(result, "ok", None) is True
    assert "compiled_intent" in payload
    ci = payload["compiled_intent"]
    assert ci["selected"]["role"] == "morpheus"
    assert ci["selected"]["action"] == "verification"
    assert getattr(result, "verification_manifest_sha256", None)

def test_planspec_refusal_missing_planspec(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTOS_INTENT_SOURCE", "planspec_v1")
    monkeypatch.setenv("AGENTOS_STORE_ROOT", str(tmp_path / "store"))
    payload = {"intent_text": "x"}
    result = run_full_pipeline(payload)
    assert result is not None
    assert getattr(result, "ok", None) is False
    assert getattr(result, "verification_manifest_sha256", None)

def test_planspec_refusal_unknown_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTOS_INTENT_SOURCE", "planspec_v1")
    monkeypatch.setenv("AGENTOS_STORE_ROOT", str(tmp_path / "store"))
    payload = {
        "intent_text": "x",
        "plan_spec": {"role": "morpheus", "action": "verification", "wat": 1},
    }
    result = run_full_pipeline(payload)
    assert result is not None
    assert getattr(result, "ok", None) is False
    assert getattr(result, "verification_manifest_sha256", None)

def test_planspec_refusal_invalid_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTOS_INTENT_SOURCE", "planspec_v1")
    monkeypatch.setenv("AGENTOS_STORE_ROOT", str(tmp_path / "store"))
    payload = {
        "intent_text": "x",
        "plan_spec": {"role": "morpheus", "action": "verification", "metadata": "nope"},
    }
    result = run_full_pipeline(payload)
    assert result is not None
    assert getattr(result, "ok", None) is False
    assert getattr(result, "verification_manifest_sha256", None)
