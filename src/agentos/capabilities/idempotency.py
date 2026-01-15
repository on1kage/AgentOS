from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict


class IdempotencyStore:
    """
    Filesystem-backed idempotency with an atomic in-flight lock.

    Invariants:
    - A completed execution is represented by a record file:
        store/idempotency/records/<task_id>_<exec_sha>.json
    - A currently executing attempt holds an exclusive lock file:
        store/idempotency/locks/<task_id>_<exec_sha>.lock

    Concurrency guarantee:
    - lock acquisition uses O_CREAT|O_EXCL, so exactly one contender can acquire.
    """

    def __init__(self, root: str = "store/idempotency") -> None:
        self.root = Path(root)
        self.records = self.root / "records"
        self.locks = self.root / "locks"
        self.records.mkdir(parents=True, exist_ok=True)
        self.locks.mkdir(parents=True, exist_ok=True)

    def _key_stem(self, task_id: str, exec_sha: str) -> str:
        return f"{task_id}_{exec_sha}"

    def _record_path(self, task_id: str, exec_sha: str) -> Path:
        return self.records / f"{self._key_stem(task_id, exec_sha)}.json"

    def _lock_path(self, task_id: str, exec_sha: str) -> Path:
        return self.locks / f"{self._key_stem(task_id, exec_sha)}.lock"

    def check(self, task_id: str, exec_sha: str) -> bool:
        return self._record_path(task_id, exec_sha).exists()

    def acquire_lock(self, task_id: str, exec_sha: str) -> None:
        lp = self._lock_path(task_id, exec_sha)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            fd = os.open(str(lp), flags, 0o600)
        except FileExistsError as e:
            raise RuntimeError(f"Idempotent lock held: {task_id} {exec_sha}") from e
        else:
            os.close(fd)

    def release_lock(self, task_id: str, exec_sha: str) -> None:
        try:
            self._lock_path(task_id, exec_sha).unlink()
        except FileNotFoundError:
            pass

    def record(self, task_id: str, exec_sha: str, metadata: Dict[str, str]) -> None:
        path = self._record_path(task_id, exec_sha)
        if path.exists():
            raise RuntimeError(f"Idempotent key exists: {task_id} {exec_sha}")
        path.write_text(
            json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
