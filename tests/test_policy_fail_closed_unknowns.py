from agentos.pipeline import Step, verify_plan


def test_verify_plan_denies_unknown_role():
    res = verify_plan([Step(role="__bogus_role__", action="external_research")], evidence_root="store/evidence")
    assert res.ok is False
    assert res.verification_manifest_sha256
    assert res.decisions[0]["allow"] is False
    assert res.decisions[0]["reason"].startswith("deny:unknown_role:")


def test_verify_plan_denies_unknown_action():
    res = verify_plan([Step(role="scout", action="__bogus_action__")], evidence_root="store/evidence")
    assert res.ok is False
    assert res.verification_manifest_sha256
    assert res.decisions[0]["allow"] is False
    assert res.decisions[0]["reason"].startswith("deny:unknown_action:")
