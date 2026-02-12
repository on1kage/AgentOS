import importlib.util
from pathlib import Path

from agentos.canonical import canonical_json, sha256_hex
from agentos.execution import canonical_inputs_manifest
from agentos.intents import intent_spec


def _load_weekly_proof_module():
    path = Path("tools/weekly_proof_run.py")
    spec = importlib.util.spec_from_file_location("weekly_proof_run", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_weekly_proof_inputs_manifest_binds_intent_spec():
    mod = _load_weekly_proof_module()
    ispec = intent_spec("utc_date")

    es = mod._make_spec(
        role="envoy",
        task_id="weekly_envoy",
        cmd_argv=["echo", "ok"],
        env_allowlist=[],
        cwd=str(Path.cwd()),
        intent_name="utc_date",
        intent_spec_obj=ispec,
    )

    expected = canonical_inputs_manifest(
        {
            "intent/name": sha256_hex("utc_date".encode("utf-8")),
            "intent/spec": sha256_hex(canonical_json(ispec).encode("utf-8")),
        }
    )

    assert es.inputs_manifest_sha256 == expected


def test_weekly_proof_manifest_changes_if_spec_changes():
    mod = _load_weekly_proof_module()
    ispec = intent_spec("utc_date")
    ispec2 = dict(ispec)
    ispec2["description"] = ispec2.get("description", "") + " (mutated)"

    es1 = mod._make_spec(
        role="envoy",
        task_id="weekly_envoy",
        cmd_argv=["echo", "ok"],
        env_allowlist=[],
        cwd=str(Path.cwd()),
        intent_name="utc_date",
        intent_spec_obj=ispec,
    )
    es2 = mod._make_spec(
        role="envoy",
        task_id="weekly_envoy",
        cmd_argv=["echo", "ok"],
        env_allowlist=[],
        cwd=str(Path.cwd()),
        intent_name="utc_date",
        intent_spec_obj=ispec2,
    )

    assert es1.inputs_manifest_sha256 != es2.inputs_manifest_sha256
