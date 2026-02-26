#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CONTRACT_PATH = Path("src/agentos/adapter_role_contract.json")


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def git_show(rev: str, path: Path) -> str:
    return run(["git", "show", f"{rev}:{path.as_posix()}"])


def load_contract(text: str) -> dict:
    return json.loads(text)


def contract_version(doc: dict) -> str:
    v = doc.get("contract_version")
    if not isinstance(v, str) or not v.strip():
        raise ValueError("adapter_role_contract.json missing non-empty string contract_version")
    return v.strip()


def main() -> int:
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"])
    except Exception:
        print("ERROR: not a git repository", file=sys.stderr)
        return 2

    base_ref = None
    for candidate in ("origin/main", "origin/master", "main", "master"):
        try:
            run(["git", "rev-parse", "--verify", candidate])
            base_ref = candidate
            break
        except Exception:
            continue

    if base_ref is None:
        print("ERROR: could not find a base ref (origin/main, origin/master, main, master). Ensure CI fetches the base branch.", file=sys.stderr)
        return 2

    head = "HEAD"
    try:
        changed = run(["git", "diff", "--name-only", f"{base_ref}...{head}"]).splitlines()
    except Exception as e:
        print(f"ERROR: git diff failed: {e}", file=sys.stderr)
        return 2

    contract_changed = any(p.strip() == CONTRACT_PATH.as_posix() for p in changed if p.strip())
    if not contract_changed:
        print("OK: contract file unchanged")
        return 0

    try:
        new_doc = load_contract(CONTRACT_PATH.read_text(encoding="utf-8"))
        new_ver = contract_version(new_doc)
    except Exception as e:
        print(f"ERROR: failed to read current contract: {e}", file=sys.stderr)
        return 2

    try:
        old_text = git_show(base_ref, CONTRACT_PATH)
    except Exception:
        print("OK: contract file changed and did not exist on base ref (new file)")
        return 0

    try:
        old_doc = load_contract(old_text)
        old_ver = contract_version(old_doc)
    except Exception as e:
        print(f"ERROR: failed to read base contract version from {base_ref}: {e}", file=sys.stderr)
        return 2

    if new_ver == old_ver:
        print("FAIL: adapter_role_contract.json changed but contract_version did not change.", file=sys.stderr)
        print(f"Base ({base_ref}) contract_version: {old_ver}", file=sys.stderr)
        print(f"Head (HEAD) contract_version: {new_ver}", file=sys.stderr)
        return 1

    print("OK: contract file changed and contract_version was bumped")
    print(f"Base ({base_ref}) contract_version: {old_ver}")
    print(f"Head (HEAD) contract_version: {new_ver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
