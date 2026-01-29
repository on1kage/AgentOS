from agentos.pipeline import PipelineResult
from agentos.intent_evidence import IntentIngestReceipt
from agentos.intent_normalizer import IntentNormalizedReceipt
from agentos.intent_compiler_contract import CompiledIntent, CompilationRefusal

def _fields(cls):
    return tuple(f.name for f in cls.__dataclass_fields__.values())

def test_pipeline_result_fields_locked():
    assert _fields(PipelineResult) == (
        "ok",
        "decisions",
        "verification_bundle_dir",
        "verification_manifest_sha256",
    )

def test_intent_ingest_receipt_fields_locked():
    assert _fields(IntentIngestReceipt) == (
        "intent_sha256",
        "bundle_dir",
        "manifest_sha256",
    )

def test_intent_normalized_receipt_fields_locked():
    assert _fields(IntentNormalizedReceipt) == (
        "intent_sha256",
        "verification_spec_sha256",
        "bundle_dir",
        "manifest_sha256",
    )

def test_compiled_intent_fields_locked():
    assert _fields(CompiledIntent) == (
        "plan_spec",
        "intent_sha256",
        "compiler_version",
        "compiler_ruleset_hash",
        "output_hash",
    )

def test_compilation_refusal_fields_locked():
    assert _fields(CompilationRefusal) == (
        "intent_sha256",
        "compiler_version",
        "compiler_ruleset_hash",
        "refusal_reason",
    )
