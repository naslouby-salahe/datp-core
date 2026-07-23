from __future__ import annotations

from datp_core.configuration.project import resolve_project_configuration


def test_executable_invariants_are_locked() -> None:
    resolved = resolve_project_configuration()

    # Assert deterministic fingerprint size and non-emptiness
    assert len(resolved.scientific_fingerprint.value) == 64
    assert len(resolved.execution_fingerprint.value) == 64

    # Assert configured experiments count
    assert len(resolved.experiments) > 0
    from datp_core.pipeline.identifiers import ExperimentId

    assert ExperimentId("anchor_reproduction") in resolved.experiments.keys()

    # Verify that the canonical configuration projection is non-empty
    assert bool(resolved.scientific_projection)
    assert bool(resolved.execution_projection)
