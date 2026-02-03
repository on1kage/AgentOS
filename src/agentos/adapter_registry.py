# AgentOS Adapter Registry

ADAPTERS = {
    "scout": {
        "cmd": ["python3","-c","import sys,runpy; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; runpy.run_path('tools/scout_live_probe.py','__main__')"],
        "env_allowlist": ["PPLX_API_KEY","PPLX_BASE_URL","PPLX_MODEL"],
        "description": "External read-only intelligence via Perplexity"
    },
    "envoy": {
        "cmd": ["python3","-c","import sys,runpy; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; runpy.run_path('tools/envoy_live_probe.py','__main__')"],
        "env_allowlist": ["OLLAMA_HOST","OLLAMA_MODEL"],
        "description": "Deterministic local execution (system UTC clock authoritative)"
    }
}
