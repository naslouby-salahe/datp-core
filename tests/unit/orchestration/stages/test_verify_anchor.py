from pathlib import Path

import pytest
from tests.unit.anchor.helpers import matching_anchor_observations

from datp_core.anchor.models import AnchorGateStatus, AnchorObservedMetric, HistoricalMetricArtifactSource
from datp_core.domain.enums import ExperimentReadiness, FederatedThresholdMethod, StageOperationId
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import MetricValue, Seed
from datp_core.orchestration.stages.verify_anchor import VerifyAnchorStageRequest, verify_anchor_stage


def test_stage_passes_with_typed_observations(tmp_path: Path) -> None:
    result = verify_anchor_stage(
        VerifyAnchorStageRequest(
            observations=matching_anchor_observations(),
            diagnostics_directory=tmp_path,
        )
    )
    assert result.status.stage is StageOperationId.VERIFY_ANCHOR
    assert result.status.gate_status is AnchorGateStatus.PASS
    assert result.status.dependent_readiness is ExperimentReadiness.DECLARED
    assert result.status.reference_count.value == 10
    assert result.status.observation_count.value == 10
    from datp_core.anchor.models import AnchorArtifactFileName

    assert (tmp_path / AnchorArtifactFileName.GATE_DECISION.value).is_file()
    assert (tmp_path / AnchorArtifactFileName.DISCREPANCIES.value).is_file()


def test_stage_blocks_without_observations_and_preserves_dependency_blocker() -> None:
    result = verify_anchor_stage()
    assert result.status.gate_status is AnchorGateStatus.BLOCKED
    assert result.status.dependent_readiness is ExperimentReadiness.BLOCKED
    assert result.status.dependency_blocker is not None
    assert "Phase 08" in result.status.dependency_blocker
    assert result.gate.reproduction.discrepancies


def test_stage_rejects_independent_reproduction_request() -> None:
    with pytest.raises(AnchorReproductionError, match="Phase 08"):
        verify_anchor_stage(VerifyAnchorStageRequest(request_independent_reproduction=True))


def test_stage_rejects_mixed_observation_inputs() -> None:
    with pytest.raises(AnchorReproductionError, match="either typed observations or historical sources"):
        verify_anchor_stage(
            VerifyAnchorStageRequest(
                observations=matching_anchor_observations(),
                historical_sources=(
                    HistoricalMetricArtifactSource(
                        path=Path("x.json"),
                        seed=Seed(0),
                        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
                    ),
                ),
            )
        )


def test_stage_diagnostics_survive_material_failure(tmp_path: Path) -> None:
    observations = list(matching_anchor_observations())
    first = observations[0]
    observations[0] = AnchorObservedMetric(
        seed=first.seed,
        population=first.population,
        training_model=first.training_model,
        threshold_method=first.threshold_method,
        metric=first.metric,
        value=MetricValue(first.value.value + 0.5),
        checkpoint_status=first.checkpoint_status,
        source_kind=first.source_kind,
        artifact_path=first.artifact_path,
        artifact_checksum=first.artifact_checksum,
        model_checkpoint_identity=first.model_checkpoint_identity,
        evidence_role=first.evidence_role,
    )
    result = verify_anchor_stage(
        VerifyAnchorStageRequest(
            observations=tuple(observations),
            diagnostics_directory=tmp_path,
        )
    )
    assert result.status.gate_status is AnchorGateStatus.BLOCKED
    from datp_core.anchor.models import AnchorArtifactFileName

    payload = (tmp_path / AnchorArtifactFileName.DISCREPANCIES.value).read_text(encoding="utf-8")
    assert "expected" in payload
