"""Independent observation package load/publish and gate verification."""

from pathlib import Path

from datp_core.anchor.gate import load_anchor_gate_decision
from datp_core.anchor.models import AnchorGateStatus, AnchorObservationSourceKind
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL
from tests.unit.anchor.helpers import matching_anchor_observations

from datp_core.core.identifiers import ExperimentReadiness
from datp_core.experiments.anchor.run import (
    VerifyAnchorStageRequest,
    load_independent_observations,
    publish_independent_observations,
    verify_anchor,
)


def _independent_observations():
    return tuple(
        item.model_copy(update={"source_kind": AnchorObservationSourceKind.INDEPENDENT_REPRODUCTION})
        for item in matching_anchor_observations()
    )


def test_independent_package_round_trip_and_gate_pass(tmp_path: Path) -> None:
    package = tmp_path / "independent"
    diagnostics = tmp_path / "diagnostics"
    observations = _independent_observations()
    publish_independent_observations(package, observations)
    loaded = load_independent_observations(package)
    assert loaded is not None
    assert len(loaded) == 10
    assert all(item.source_kind is AnchorObservationSourceKind.INDEPENDENT_REPRODUCTION for item in loaded)
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=diagnostics,
            independent_package_directory=package,
            request_independent_reproduction=True,
        )
    )
    assert result.status.gate_status is AnchorGateStatus.PASS
    assert result.status.dependent_readiness is ExperimentReadiness.DECLARED
    decision = load_anchor_gate_decision(diagnostics)
    assert decision.status is AnchorGateStatus.PASS


def test_independent_verify_without_package_fails_closed(tmp_path: Path) -> None:
    result = verify_anchor(
        VerifyAnchorStageRequest(
            protocol=ANCHOR_DECISION_PROTOCOL,
            diagnostics_directory=tmp_path / "diagnostics",
            independent_package_directory=tmp_path / "missing",
            request_independent_reproduction=True,
        )
    )
    assert result.status.gate_status is AnchorGateStatus.BLOCKED
    assert result.status.dependent_readiness is ExperimentReadiness.BLOCKED
    assert result.status.observation_count.value == 0
    assert result.status.dependency_blocker is not None
