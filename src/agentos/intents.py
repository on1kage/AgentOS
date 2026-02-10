INTENTS = {
  "utc_date": {
    "description": "Return current UTC date in ISO-8601 YYYY-MM-DD",
    "schema_version": "agentos-intent/v1",
    "type": "string",
    "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
  }
}

def is_known_intent(name: str) -> bool:
  return isinstance(name, str) and name in INTENTS

def intent_spec(name: str) -> dict:
  if not is_known_intent(name):
    raise ValueError(f"unknown_intent:{name}")
  return INTENTS[name]
