from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from agentos.canonical import canonical_json, sha256_hex


def _die(msg: str) -> None:
    raise SystemExit(msg)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _die(f"invalid_json:{path}:{e.__class__.__name__}:{e}")


def _require(cond: bool, msg: str) -> None:
    if not cond:
        _die(msg)


def _iter_dirs(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    for p in root.rglob("*"):
        if p.is_dir():
            yield p


def _compute_manifest_sha256_json(files_map: Dict[str, str]) -> str:
    b = canonical_json({"files": files_map}).encode("utf-8")
    return sha256_hex(b)


def _validate_execution_bundle(bundle_dir: Path, contract: Dict[str, Any]) -> None:
    for fname in contract["required_files"]:
        _require((bundle_dir / fname).is_file(), f"missing_file:execution:{bundle_dir}:{fname}")
    for dname in contract.get("required_dirs", []):
        _require((bundle_dir / dname).is_dir(), f"missing_dir:execution:{bundle_dir}:{dname}")

    rs_path = bundle_dir / "run_summary.json"
    rs = _load_json(rs_path)
    for k in contract["run_summary_required_fields"]:
        _require(k in rs, f"missing_field:run_summary:{bundle_dir}:{k}")
    _require(int(rs["schema_version"]) == int(contract["run_summary_schema_version"]), f"bad_schema_version:run_summary:{bundle_dir}")

    manifest_path = bundle_dir / "manifest.sha256.json"
    man = _load_json(manifest_path)
    _require(isinstance(man, dict) and "files" in man and isinstance(man["files"], dict), f"bad_manifest_format:execution:{bundle_dir}")
    files_map = {str(k): str(v) for k, v in man["files"].items()}
    for k in contract.get("manifest_must_include", []):
        _require(k in files_map, f"missing_manifest_entry:execution:{bundle_dir}:{k}")

    for rel, hexsha in files_map.items():
        p = bundle_dir / rel
        _require(p.is_file(), f"manifest_points_to_missing_file:execution:{bundle_dir}:{rel}")
        got = sha256_hex(p.read_bytes())
        _require(got == hexsha, f"hash_mismatch:execution:{bundle_dir}:{rel}")

    expected_manifest_sha = sha256_hex(manifest_path.read_bytes())
    _require(str(rs["manifest_sha256"]) == expected_manifest_sha, f"run_summary_manifest_sha256_mismatch:{bundle_dir}")

    exec_spec_path = bundle_dir / "exec_spec.json"
    spec_sha = sha256_hex(exec_spec_path.read_bytes())
    _require(str(rs["spec_sha256"]) == spec_sha, f"run_summary_spec_sha256_mismatch:{bundle_dir}")


def _validate_rejection_bundle(bundle_dir: Path, contract: Dict[str, Any]) -> None:
    for fname in contract["required_files"]:
        _require((bundle_dir / fname).is_file(), f"missing_file:rejection:{bundle_dir}:{fname}")

    rej = _load_json(bundle_dir / "rejection.json")
    for k in contract["rejection_required_fields"]:
        _require(k in rej, f"missing_field:rejection.json:{bundle_dir}:{k}")
    _require(int(rej["schema_version"]) == int(contract["run_summary_schema_version"]), f"bad_schema_version:rejection:{bundle_dir}")
    _require(str(rej["outcome"]) == "REJECTED", f"bad_outcome:rejection:{bundle_dir}")

    manifest_path = bundle_dir / "manifest.sha256.json"
    man = _load_json(manifest_path)
    _require(isinstance(man, dict) and "files" in man and isinstance(man["files"], dict), f"bad_manifest_format:rejection:{bundle_dir}")
    files_map = {str(k): str(v) for k, v in man["files"].items()}
    for rel, hexsha in files_map.items():
        p = bundle_dir / rel
        _require(p.is_file(), f"manifest_points_to_missing_file:rejection:{bundle_dir}:{rel}")
        got = sha256_hex(p.read_bytes())
        _require(got == hexsha, f"hash_mismatch:rejection:{bundle_dir}:{rel}")

    expected_manifest_sha = sha256_hex(manifest_path.read_bytes())
    _require(files_map.get("manifest.sha256.json") == expected_manifest_sha or "manifest.sha256.json" not in files_map, f"manifest_self_hash_mismatch:rejection:{bundle_dir}")

    reason = str(rej["reason"])
    expected_rej_id = sha256_hex(reason.encode("utf-8"))[:16]
    _require(bundle_dir.name == expected_rej_id, f"rej_id_mismatch:{bundle_dir}:{expected_rej_id}")


def _validate_verification_bundle(bundle_dir: Path, contract: Dict[str, Any]) -> None:
    for fname in contract["required_files"]:
        _require((bundle_dir / fname).is_file(), f"missing_file:verification:{bundle_dir}:{fname}")

    manifest_path = bundle_dir / "manifest.sha256.json"
    payload = _load_json(manifest_path)
    _require(isinstance(payload, dict), f"bad_manifest_format:verification:{bundle_dir}")
    for k in ["spec_sha256", "reason", "idempotency_key", "decisions"]:
        _require(k in payload, f"missing_field:verification_manifest:{bundle_dir}:{k}")
    _require(str(payload["spec_sha256"]) == bundle_dir.name, f"verification_spec_dir_mismatch:{bundle_dir}")

    expected_bytes = canonical_json(payload).encode("utf-8")
    _require(manifest_path.read_bytes() == expected_bytes, f"verification_manifest_not_canonical:{bundle_dir}")


def main(argv: list[str]) -> int:
    contract_path = Path("ci/evidence_contract.v1.json")
    evidence_root = Path("evidence")

    if "--contract" in argv:
        i = argv.index("--contract")
        if i + 1 >= len(argv):
            _die("missing_arg:--contract")
        contract_path = Path(argv[i + 1])

    if "--evidence-root" in argv:
        i = argv.index("--evidence-root")
        if i + 1 >= len(argv):
            _die("missing_arg:--evidence-root")
        evidence_root = Path(argv[i + 1])

    contract = _load_json(contract_path)
    _require(isinstance(contract, dict) and contract.get("schema_version") == 1, "bad_contract_schema_version")

    bt = contract["bundle_types"]
    exec_c = bt["execution"]
    ver_c = bt["verification"]
    rej_c = bt["rejection"]

    if not evidence_root.exists():
        _die(f"missing_evidence_root:{evidence_root}")

    verify_root = evidence_root / "verify"
    rejections_marker = "rejections"

    for d in _iter_dirs(evidence_root):
        if d == evidence_root:
            continue
        rel = d.relative_to(evidence_root)
        parts = rel.parts

        if parts[0] == "verify":
            if len(parts) == 2:
                _validate_verification_bundle(d, ver_c)
            continue

        if rejections_marker in parts:
            if len(parts) >= 3 and parts[-2] == rejections_marker:
                _validate_rejection_bundle(d, rej_c)
            continue

        if len(parts) == 2:
            _validate_execution_bundle(d, exec_c)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"validator_crash:{e.__class__.__name__}:{e}")
