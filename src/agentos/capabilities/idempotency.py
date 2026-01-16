from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict


class IdempotencyStore:
    """
    Filesystem-backed idempotency with an atomic in-flight lock and atomic attempt recording.

    Layout:
      root/records/<task_id>_<exec_sha>.json   # authoritative "attempt happened" marker
      root/locks/<task_id>_<exec_sha>.lock     # in-flight mutex (prevents concurrent double-run)

    Policy modes:
    - This store supports "record_if_absent" which is used to implement Policy B:
        retry forbidden after any attempt (success or failure).
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

    def load_metadata(self, task_id: str, exec_sha: str) -> Dict[str, str]:
        """Load immutable metadata for an existing idempotency record.

        Fail-closed if the record does not exist or is not valid JSON.
        """
        rp = self._record_path(task_id, exec_sha)
        if not rp.exists():
            raise RuntimeError(f"missing idempotency record: {task_id} {exec_sha}")
        obj = json.loads(rp.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise TypeError("idempotency record must be a JSON object")
        out: Dict[str, str] = {}
        for k, v in obj.items():
            if isinstance(k, str) and isinstance(v, str):
                out[k] = v
        return out

    def acquire_lock(self, task_id: str, exec_sha: str) -> None:
        """
        Acquire an exclusive in-flight lock atomically.
        Raises RuntimeError if the lock is already held.
        """
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

    def record_if_absent(self, task_id: str, exec_sha: str, metadata: Dict[str, str]) -> bool:
        """
        Atomically create the record file iff it does not already exist.
        Returns True if created, False if already present.

        This is the primitive required for Policy B (no retry after any attempt).
        """
        path = self._record_path(task_id, exec_sha)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            fd = os.open(str(path), flags, 0o600)
        except FileExistsError:
            return False

        try:
            data = json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            os.write(fd, data)
        finally:
            os.close(fd)
        return True
