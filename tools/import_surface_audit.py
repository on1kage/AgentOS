import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

def _stdlib_names() -> Set[str]:
    names: Set[str] = set()
    v = getattr(sys, "stdlib_module_names", None)
    if isinstance(v, frozenset) or isinstance(v, set):
        names |= set(v)
    names |= {
        "typing","pathlib","dataclasses","json","hashlib","re","os","sys","subprocess","datetime","time",
        "shutil","argparse","base64","binascii","itertools","functools","collections","math","statistics",
        "textwrap","traceback","logging","tempfile","uuid"
    }
    return names

def _top_level(mod: str) -> str:
    return (mod or "").split(".")[0].strip()

def _extract_runpy_paths_from_adapter_registry(adapter_registry_py: Path) -> List[str]:
    s = adapter_registry_py.read_text(encoding="utf-8")
    paths: List[str] = []
    for m in re.finditer(r"runpy\.run_path\(\\\"(tools/[^\\\"]+\.py)\\\"", s):
        paths.append(m.group(1))
    return sorted(set(paths))

def _imports_from_ast(tree: ast.AST) -> Set[str]:
    mods: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                mods.add(_top_level(a.name))
        elif isinstance(n, ast.ImportFrom):
            mods.add(_top_level(n.module or ""))
    mods.discard("")
    return mods

def _has_dynamic_import_calls(tree: ast.AST) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func
            if isinstance(fn, ast.Name) and fn.id in ("__import__",):
                return True
            if isinstance(fn, ast.Attribute):
                if isinstance(fn.value, ast.Name) and fn.value.id == "importlib" and fn.attr in ("import_module",):
                    return True
    return False

def audit_files(*, base_dir: Path, rel_paths: List[str]) -> Dict[str, object]:
    stdlib = _stdlib_names()
    allowed_prefixes = {"onemind", "agentos"}
    findings: Dict[str, object] = {"ok": True, "files": {}}

    for rel in rel_paths:
        p = base_dir / rel
        if not p.exists():
            findings["ok"] = False
            findings["files"][rel] = {"ok": False, "error": "missing_file"}
            continue

        src = p.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(p))
        imports = sorted(_imports_from_ast(tree))
        dyn = _has_dynamic_import_calls(tree)

        disallowed: List[str] = []
        for m in imports:
            if m in allowed_prefixes:
                continue
            if m in stdlib:
                continue
            disallowed.append(m)

        file_ok = (len(disallowed) == 0) and (not dyn)
        if not file_ok:
            findings["ok"] = False

        findings["files"][rel] = {
            "ok": file_ok,
            "imports": imports,
            "disallowed_imports": disallowed,
            "dynamic_import_calls": bool(dyn),
        }

    return findings

def audit_adapter_import_surface(repo_root: Path) -> Dict[str, object]:
    adapter_registry_py = repo_root / "src/agentos/adapter_registry.py"
    rel_paths = _extract_runpy_paths_from_adapter_registry(adapter_registry_py)
    return audit_files(base_dir=repo_root, rel_paths=rel_paths)

def main() -> int:
    repo = Path.cwd()
    r = audit_adapter_import_surface(repo)
    if not bool(r.get("ok")):
        raise SystemExit(2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
