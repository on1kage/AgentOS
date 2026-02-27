from __future__ import annotations

import json
import os
from pathlib import Path

import agentos.role_assignments_loader as ral


def test_role_assignments_loader_happy_path(tmp_path: Path, monkeypatch):
    p = tmp_path / "role_assignments.json"
    p.write_text(
        json.dumps(
            {
                "morpheus": {"provider": "openai", "model": "chatgpt", "api_env": "OPENAI_API_KEY"},
                "scout": {"provider": "perplexity", "model": "sonar-pro", "api_env": "PPLX_API_KEY"},
                "envoy": {"provider": "ollama", "model": "qwen2.5:14b", "api_env": None},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ral, "ASSIGNMENTS_PATH", p)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("PPLX_API_KEY", "y")

    out = ral.load_role_assignments()
    assert out["morpheus"]["provider"] == "openai"
    assert out["scout"]["provider"] == "perplexity"
    assert out["envoy"]["provider"] == "ollama"


def test_role_assignments_loader_missing_key_fails_closed(tmp_path: Path, monkeypatch):
    p = tmp_path / "role_assignments.json"
    p.write_text(
        json.dumps(
            {
                "morpheus": {"provider": "openai", "model": "chatgpt", "api_env": "OPENAI_API_KEY"},
                "scout": {"provider": "perplexity", "model": "sonar-pro", "api_env": "PPLX_API_KEY"},
                "envoy": {"provider": "ollama", "model": "qwen2.5:14b", "api_env": None},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ral, "ASSIGNMENTS_PATH", p)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.delenv("PPLX_API_KEY", raising=False)

    try:
        ral.load_role_assignments(require_env_for_roles=["scout"])
        assert False, "expected RoleAssignmentError"
    except ral.RoleAssignmentError as e:
        assert "missing_api_key_env:scout:PPLX_API_KEY" in str(e)
