from __future__ import annotations
from pathlib import Path
from typing import Dict
import json
from agentos.canonical import sha256_hex

class IdempotencyStore:
    def __init__(self, root: str = "store/idempotency") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _key_path(self, task_id: str, exec_sha: str) -> Path:
        return self.root / f"{task_id}_{exec_sha}.json"

    def check(self, task_id: str, exec_sha: str) -> bool:
        return self._key_path(task_id, exec_sha).exists()

    def record(self, task_id: str, exec_sha: str, metadata: Dict[str, str]) -> None:
        path = self._key_path(task_id, exec_sha)
        if path.exists():
            raise RuntimeError(f"Idempotent key exists: {task_id} {exec_sha}")
        path.write_text(
            json.dumps(metadata, sort_keys=True, separators=(',', ':'), ensure_ascii=False),
            encoding="utf-8"
        )
