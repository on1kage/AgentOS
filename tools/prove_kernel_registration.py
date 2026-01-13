from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from agentos.register import register_into


def main() -> None:
    # Import kernel singleton from onemind-FSM-Kernel on PYTHONPATH
    from onemind.kernel.core import KERNEL  # type: ignore

    before = sorted(list(getattr(KERNEL, "subsystems", {}).keys()))
    register_into(KERNEL, overwrite=True)
    after = sorted(list(getattr(KERNEL, "subsystems", {}).keys()))

    agentos = KERNEL.subsystems.get("agentos")
    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kernel": {"module": "onemind.kernel.core", "singleton": "KERNEL"},
        "agentos_repo": os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        "before": before,
        "after": after,
        "agentos": {
            "present": agentos is not None,
            "has_execute": callable(getattr(agentos, "execute", None)) if agentos else False,
            "describe": agentos.describe() if agentos else None,
        },
    }

    # Canonical JSON
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
