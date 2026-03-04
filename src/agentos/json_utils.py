import json
from typing import Any

def canonical_json(obj: Any) -> str:
    """
    Return a deterministic JSON string:
    - keys sorted
    - no extra whitespace
    - UTF-8 safe
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
