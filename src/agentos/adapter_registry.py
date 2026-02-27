ADAPTERS = {
    "scout": {
        "cmd": ["python3", "tools/scout_run.py"],
        "env_allowlist": ["PPLX_API_KEY"],
        "description": "External read-only intelligence via Perplexity",
        "adapter_version": "1.0.0"
    },
    "envoy": {
        "cmd": ["python3", "tools/envoy_live_probe.py"],
        "env_allowlist": [],
        "description": "Deterministic local execution (system UTC clock authoritative)",
        "adapter_version": "1.0.0"
    }
}
