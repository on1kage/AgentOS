"""
Deterministic kernel tree fingerprint for AgentOS.

Purpose:
- Bind weekly_proof artifacts to the exact executing codebase.
- Prevent "verified artifact produced by modified executor" false trust.

Definition:
- Hash is computed over a canonical manifest of file SHA256s for:
  - src/agentos/**
  - tools/**

Exclusions (non-semantic / non-deterministic):
- __pycache__, *.pyc, .pytest_cache, .venv, .git, store, dist, build, *.egg-info
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from agentos.canonical import canonical_json, sha256_hex


_EXCLUDE_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    ".git",
    "store",
    "dist",
    "build",
}

_EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
}


_EXCLUDE_FILES = {
    "src/agentos/adapter_role_contract.json",
    "src/agentos/role_assignments.json",
}

_EXCLUDE_NAME_CONTAINS = (
    ".egg-info",
)


def _repo_root() -> Path:
    # src/agentos/kernel_fingerprint.py -> parents:
    # 0=agentos, 1=src, 2=repo root
    return Path(__file__).resolve().parents[2]


def _is_excluded_path(p: Path) -> bool:
    parts = set(p.parts)
    if parts & _EXCLUDE_DIRS:
        return True
    name = p.name
    if any(x in name for x in _EXCLUDE_NAME_CONTAINS):
        return True
    if p.suffix in _EXCLUDE_SUFFIXES:
        return True
    return False


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    out: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if _is_excluded_path(p):
            continue
        out.append(p)
    out.sort(key=lambda x: str(x))
    return out


def _sha256_file_bytes(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_kernel_tree_sha256(
    *,
    repo_root: Optional[Path] = None,
    include_roots: Optional[List[str]] = None,
) -> str:
    """
    Compute a deterministic fingerprint of the AgentOS executor surface.

    Returns:
        sha256 hex of canonical manifest:
        {
          "schema_version": "agentos-kernel-tree/v1",
          "roots": ["src/agentos", "tools"],
          "files": [{"path": "...", "sha256": "..."}, ...]
        }
    """
    rr = Path(repo_root) if repo_root is not None else _repo_root()
    roots = include_roots or ["src/agentos", "tools"]

    manifest_files: List[Dict[str, str]] = []
    for r in roots:
        base = (rr / r).resolve()
        for f in _iter_files(base):
            rel = f.resolve().relative_to(rr.resolve())
            if rel.as_posix() in _EXCLUDE_FILES:
                continue
            manifest_files.append(
                {
                    "path": rel.as_posix(),
                    "sha256": _sha256_file_bytes(f),
                }
            )

    # Canonicalize ordering deterministically (double safety).
    manifest_files.sort(key=lambda d: d["path"])

    payload = {
        "schema_version": "agentos-kernel-tree/v1",
        "roots": list(roots),
        "files": manifest_files,
    }
    return sha256_hex(canonical_json(payload).encode("utf-8"))
