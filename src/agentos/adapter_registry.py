ADAPTERS = {
    "scout": {
        "cmd": ["python3","-c","import sys; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; from onemind.scout.perplexity import ask_perplexity; print(ask_perplexity(sys.argv[1]))"],
        "env_allowlist": ["PPLX_API_KEY","PPLX_BASE_URL"],
        "description": "External read-only intelligence via Perplexity"
    },
    "envoy": {
        "cmd": ["python3","-c","import sys,runpy; sys.path[:0]=['src','src/onemind-FSM-Kernel/src']; runpy.run_path('tools/envoy_live_probe.py', run_name='__main__')"],
        "env_allowlist": [],
        "description": "Deterministic local execution (system UTC clock authoritative)"
    }
}
