import os
from pathlib import Path

from agentos.plan_runner_full_pipeline import run_full_pipeline


def test_planspec_gate_fails_closed_when_intent_source_unset(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOS_STORE_ROOT", str(tmp_path))
    monkeypatch.delenv("AGENTOS_INTENT_SOURCE", raising=False)

    payload = {
        "intent_text": "unit:test intent_source unset must fail closed",
        "plan_spec": {"role": "envoy", "action": "deterministic_local_execution", "metadata": {}},
    }

    r = run_full_pipeline(payload)

    assert r.ok is False
    assert isinstance(r.decisions, list) and len(r.decisions) > 0
    d0 = r.decisions[0]
    assert d0.get("stage") == "intent_source_gate"
    assert d0.get("reason") == "legacy_path_blocked:intent_source_unset"
    assert d0.get("legacy_id") == "intent_source_unset"
    assert isinstance(r.verification_bundle_dir, str) and r.verification_bundle_dir
    assert isinstance(r.verification_manifest_sha256, str) and r.verification_manifest_sha256
