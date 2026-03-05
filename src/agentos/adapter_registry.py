ADAPTERS = {
    "scout": {
        "cmd": ["python3", "-c", "import runpy,sys; sys.path.insert(0,\"src\"); runpy.run_path(\"tools/scout_run.py\", run_name=\"__main__\")"],
        "env_allowlist": ["PPLX_API_KEY","OPENAI_API_KEY"],
        "description": "External read-only intelligence via Perplexity",
        "adapter_version": "1.0.0"
    }
    ,"morpheus": {
        "cmd": ["python3", "-c", "import runpy,sys; sys.path.insert(0,\"src\"); runpy.run_path(\"tools/morpheus_run.py\", run_name=\"__main__\")"],
        "env_allowlist": ["OPENAI_API_KEY"],
        "description": "Architectural reasoning and system-level synthesis",
        "adapter_version": "1.0.0"
    }
,
    "envoy": {
        "cmd": ["python3", "-c", "import runpy,sys; sys.path.insert(0,\"src\"); runpy.run_path(\"tools/envoy_system_status.py\", run_name=\"__main__\")"],
        "env_allowlist": [],
        "description": "Deterministic local execution (system UTC clock authoritative)",
        "adapter_version": "1.0.0"
    }
}
