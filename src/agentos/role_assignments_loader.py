from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set

REQUIRED_ROLES = {"morpheus", "scout", "envoy"}
REQUIRED_FIELDS = {"provider", "model", "api_env"}

ASSIGNMENTS_PATH = Path(__file__).parent / "role_assignments.json"


class RoleAssignmentError(RuntimeError):
    pass


def load_role_assignments(*, require_env_for_roles: Optional[Iterable[str]] = None) -> Dict[str, Dict[str, Any]]:
    if not ASSIGNMENTS_PATH.exists():
        raise RoleAssignmentError("role_assignments.json missing")

    try:
        data = json.loads(ASSIGNMENTS_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise RoleAssignmentError(f"invalid_json:{e}")

    if not isinstance(data, dict):
        raise RoleAssignmentError("role_assignments must be object")

    missing_roles = REQUIRED_ROLES - set(data.keys())
    if missing_roles:
        raise RoleAssignmentError(f"missing_roles:{sorted(missing_roles)}")

    require_set: Set[str] = set(require_env_for_roles or [])

    for role, cfg in data.items():
        if not isinstance(cfg, dict):
            raise RoleAssignmentError(f"invalid_config:{role}")

        missing_fields = REQUIRED_FIELDS - set(cfg.keys())
        if missing_fields:
            raise RoleAssignmentError(f"missing_fields:{role}:{sorted(missing_fields)}")

        provider = cfg["provider"]
        model = cfg["model"]
        api_env = cfg["api_env"]

        if not isinstance(provider, str) or not provider:
            raise RoleAssignmentError(f"invalid_provider:{role}")

        if not isinstance(model, str) or not model:
            raise RoleAssignmentError(f"invalid_model:{role}")

        if api_env is not None and (not isinstance(api_env, str) or not api_env):
            raise RoleAssignmentError(f"invalid_api_env:{role}")

        if role in require_set and api_env is not None:
            if os.environ.get(api_env) is None:
                raise RoleAssignmentError(f"missing_api_key_env:{role}:{api_env}")

    return data
