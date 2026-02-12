from typing import Dict, List

ROLE_ALLOWLIST: Dict[str, List[str]] = {
    "scout": [
        "web_search",
        "doc_retrieval",
        "data_lookup",
        "summarize_sources",
        "extract_entities",
        "transform_text",
        "weekly_proof"
    ],
    "envoy": [
        "shell_exec",
        "repo_ops",
        "test_exec",
        "build_exec",
        "file_write",
        "artifact_pack",
        "weekly_proof"
    ],
}

SCOUT_REQUIRED_KEYS = {
    "adapter_role",
    "adapter_version",
    "action_class",
    "ok",
    "result",
    "sources",
    "errors",
}

ENVOY_REQUIRED_KEYS = {
    "adapter_role",
    "adapter_version",
    "action_class",
    "ok",
    "exit_code",
    "stdout",
    "stderr",
    "artifacts",
    "errors",
}

def validate_role_action(role: str, action_class: str) -> bool:
    allowed = ROLE_ALLOWLIST.get(role, [])
    return action_class in allowed

def validate_output_schema(role: str, payload: dict) -> bool:
    if role == "scout":
        required = SCOUT_REQUIRED_KEYS
    elif role == "envoy":
        required = ENVOY_REQUIRED_KEYS
    else:
        return False
    if set(payload.keys()) != required:
        return False
    if payload.get("adapter_role") != role:
        return False
    if not validate_role_action(role, payload.get("action_class")):
        return False
    return True
