intents_registry: dict = {}  # define if not already defined

intents_registry["system_status"] = {
    "description": "Return current system status summary (UTC time, GPU load, memory usage).",
    "parameters": {},
    "expected_output": {
        "utc_time": "ISO8601 string",
        "gpu_util": "percentage float",
        "memory_used": "MiB integer"
    }
}


INTENTS = {
  "utc_date": {
    "description": "Return current UTC date in ISO-8601 YYYY-MM-DD",
    "schema_version": "agentos-intent/v1",
    "type": "string",
    "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
  },
  "system_status": {
    "description": "Return current system status summary (UTC time, GPU load, memory usage).",
    "schema_version": "agentos-intent/v1",
    "type": "object",
    "pattern": None
  }
}

def is_known_intent(name: str) -> bool:
  return isinstance(name, str) and name in INTENTS

def intent_spec(name: str) -> dict:
  if not is_known_intent(name):
    raise ValueError(f"unknown_intent:{name}")
  return INTENTS[name]
