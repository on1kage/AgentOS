from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List

from agentos.canonical import canonical_json


def _json_top_keys(p: Path) -> List[str] | None:
    """
    Return sorted top-level keys if p is a JSON object file; otherwise None.
    Fail-closed: any parse error returns None (caller decides).
    """
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(obj, dict):
        return sorted([str(k) for k in obj.keys()])
    return None


def bundle_schema_object(bundle_dir: str) -> Dict[str, Any]:
    """
    Canonical evidence-bundle schema surface:
    - file list (names only)
    - for *.json files: sorted top-level keys
    - for non-json files: type marker only

    This is a schema fingerprint, not a content hash.
    """
    root = Path(bundle_dir)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"bundle_dir_missing:{root}")

    files = sorted([p.name for p in root.iterdir() if p.is_file()])

    json_keys: Dict[str, List[str]] = {}
    other_files: List[str] = []
    for name in files:
        p = root / name
        if name.endswith(".json"):
            keys = _json_top_keys(p)
            if keys is None:
                # Fail-closed: declared JSON file must parse to a dict
                raise RuntimeError(f"bundle_json_unparseable_or_not_object:{name}")
            json_keys[name] = keys
        else:
            other_files.append(name)

    return {
        "schema_version": "agentos-evidence-bundle-schema/v1",
        "files": files,
        "json_top_level_keys": {k: json_keys[k] for k in sorted(json_keys.keys())},
        "non_json_files": other_files,
    }


def bundle_schema_sha256(bundle_dir: str) -> str:
    obj = bundle_schema_object(bundle_dir)
    payload = canonical_json(obj).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
