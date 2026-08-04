from datp_core.pipeline.preflight import ExtensionKind, ExtensionRequest, assess_extension


def test_future_attack_behavior_is_not_implemented() -> None:
    decision = assess_extension(ExtensionRequest(kind=ExtensionKind.ATTACK, identity="poisoning"))
    assert not decision.permitted
