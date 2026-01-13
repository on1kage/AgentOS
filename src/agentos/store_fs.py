from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from agentos.canonical import canonical_json, sha256_hex


@dataclass(frozen=True)
class EventRef:
    task_id: str
    seq: int
    sha256: str
    path: str


class FSStore:
    """
    Append-only filesystem event store.

    Layout:
      store/events/<task_id>/HEAD          -> last sequence integer
      store/events/<task_id>/<seq>.json    -> canonical event json (includes sha256)
    """

    def __init__(self, root: str = "store") -> None:
        self.root = Path(root)

    def _task_dir(self, task_id: str) -> Path:
        # task_id is treated as an opaque string; caller should ensure safe characters.
        return self.root / "events" / task_id

    def _head_path(self, task_id: str) -> Path:
        return self._task_dir(task_id) / "HEAD"

    def _event_path(self, task_id: str, seq: int) -> Path:
        return self._task_dir(task_id) / f"{seq:020d}.json"

    def _read_head(self, task_id: str) -> int:
        p = self._head_path(task_id)
        if not p.exists():
            return -1
        raw = p.read_text(encoding="utf-8").strip()
        return int(raw)

    def _write_head_atomic(self, task_id: str, seq: int) -> None:
        td = self._task_dir(task_id)
        td.mkdir(parents=True, exist_ok=True)
        head = self._head_path(task_id)
        tmp = td / "HEAD.tmp"
        tmp.write_text(f"{seq}", encoding="utf-8")
        os.replace(tmp, head)

    def append_event(self, task_id: str, type_: str, body: Dict[str, Any]) -> EventRef:
        """
        Append an event to a task stream. Deterministic serialization, explicit sha256.
        """
        td = self._task_dir(task_id)
        td.mkdir(parents=True, exist_ok=True)

        prev_seq = self._read_head(task_id)
        seq = prev_seq + 1

        ts_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        prev_hash = None
        if prev_seq >= 0:
            prev_path = self._event_path(task_id, prev_seq)
            if prev_path.exists():
                # We store the prior event hash to form a hash chain.
                import json as _json
                prev_obj = _json.loads(prev_path.read_text(encoding="utf-8"))
                prev_hash = prev_obj.get("sha256")

        event_core = {
            "task_id": task_id,
            "seq": seq,
            "ts_utc": ts_utc,
            "type": type_,
            "body": body,
            "prev_sha256": prev_hash,
        }

        sha = sha256_hex(canonical_json(event_core).encode("utf-8"))
        event = dict(event_core)
        event["sha256"] = sha

        path = self._event_path(task_id, seq)
        # Fail-closed: do not overwrite existing event files.
        if path.exists():
            raise RuntimeError(f"event already exists: {path}")

        # Atomic write via temp + rename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(canonical_json(event), encoding="utf-8")
        os.replace(tmp, path)

        # Update HEAD last (also atomic)
        self._write_head_atomic(task_id, seq)

        return EventRef(task_id=task_id, seq=seq, sha256=sha, path=str(path))

    def read_event(self, task_id: str, seq: int) -> Dict[str, Any]:
        p = self._event_path(task_id, seq)
        if not p.exists():
            raise FileNotFoundError(str(p))
        import json as _json
        return _json.loads(p.read_text(encoding="utf-8"))

    def list_events(self, task_id: str) -> Tuple[Dict[str, Any], ...]:
        td = self._task_dir(task_id)
        if not td.exists():
            return tuple()
        paths = sorted([p for p in td.glob("*.json") if p.name != "HEAD.json"])
        out = []
        import json as _json
        for p in paths:
            out.append(_json.loads(p.read_text(encoding="utf-8")))
        return tuple(out)

    def verify_chain(self, task_id: str) -> bool:
        """
        Verify sha256 fields and prev_sha256 chaining for a task.
        """
        events = self.list_events(task_id)
        prev = None
        for ev in events:
            sha = ev.get("sha256")
            core = {k: ev[k] for k in ("task_id", "seq", "ts_utc", "type", "body", "prev_sha256")}
            recomputed = sha256_hex(canonical_json(core).encode("utf-8"))
            if sha != recomputed:
                return False
            if prev is None:
                if ev.get("prev_sha256") is not None:
                    return False
            else:
                if ev.get("prev_sha256") != prev:
                    return False
            prev = sha
        return True
