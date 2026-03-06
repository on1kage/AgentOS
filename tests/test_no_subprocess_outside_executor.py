from __future__ import annotations

from pathlib import Path


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_no_subprocess_run_outside_executor_module() -> None:
    root = Path("src/agentos")
    hits = []
    for f in sorted(root.rglob("*.py")):
        if f.name == "executor.py":
            continue
        s = _read(f)
        if "subprocess.run(" in s:
            hits.append(str(f))
    assert hits == [], f"subprocess.run must only appear in src/agentos/executor.py; found in: {hits}"


def test_localexecutor_only_instantiated_by_runner() -> None:
    root = Path("src/agentos")
    hits = []
    for f in sorted(root.rglob("*.py")):
        if f.name in ("runner.py", "executor.py"):
            continue
        s = _read(f)
        if "LocalExecutor(" in s:
            hits.append(str(f))
    assert hits == [], f"LocalExecutor must only be instantiated by runner.py; found in: {hits}"
