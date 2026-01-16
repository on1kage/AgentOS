from agentos.capabilities.idempotency import IdempotencyStore
from agentos.canonical import sha256_hex

def test_idempotency_store(tmp_path):
    store = IdempotencyStore(root=str(tmp_path))
    task_id = "task1"
    exec_sha = sha256_hex(b"dummy")
    assert not store.check(task_id, exec_sha)
    assert store.record_if_absent(task_id, exec_sha, {"note": "first"}) is True
    assert store.check(task_id, exec_sha)
