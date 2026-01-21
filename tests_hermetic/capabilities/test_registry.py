from agentos.capabilities.registry import registry

def test_registry_contains_recon():
    r = registry()
    key = "envoy:deterministic_local_execution"
    assert key in r
    spec = r[key]
    assert spec.role == "envoy"
    assert spec.action == "deterministic_local_execution"
