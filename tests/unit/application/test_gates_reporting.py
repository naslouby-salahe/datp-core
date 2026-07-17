from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from datp_core.analysis.report_models import ReportColumn, ReportRow, TableSpecification
from datp_core.application.planning.gates import (
    AnchorReproductionGate,
    AnchorReproductionGateRequest,
    FeasibilityGateEvaluator,
    FeasibilityGateRequest,
    RegimeDFeasibilityEvidence,
    ScientificReadinessEvaluator,
)
from datp_core.application.reporting.freeze import ResultFreezeEligibility
from datp_core.application.reporting.tracing import TableFigureTracer, TraceReportArtifactRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, PartitionIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
    ArtifactSchemaVersion,
    StageFingerprint,
)
from datp_core.domain.errors import AnchorReproductionFailure, DomainValidationError, ProvenanceError
from datp_core.domain.evaluation.alert_burden import BootstrapResampleCount, CalibrationSampleCount
from datp_core.domain.evaluation.statistical_results import (
    AnchorMovementAssessment,
    ConfidenceLevel,
    CoverageRatio,
    FailedAnchorReproductionResult,
    StatisticalMethod,
    ValidBootstrapIntervalResult,
)
from datp_core.domain.experiments.feasibility import BlockingReason, ScientificReadinessResult
from datp_core.domain.experiments.protocols import TableType
from datp_core.domain.experiments.specifications import RegimeDViabilityGateSpec


def _artifact(*, character: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _table_specification() -> TableSpecification:
    return TableSpecification(
        table_type=TableType.CONFIRMATORY_INTERVAL,
        columns=(ReportColumn(key="metric", label="Metric"),),
        rows=(ReportRow(values=(0.1,)),),
    )


def _regime_d_gate() -> FeasibilityGateEvaluator:
    return FeasibilityGateEvaluator(
        viability=RegimeDViabilityGateSpec(
            minimum_eligibility_coverage=CoverageRatio(value=Decimal("0.90")),
            minimum_calibration_samples=CalibrationSampleCount(value=100),
        )
    )


def test_anchor_and_feasibility_gates_block_failed_typed_evidence() -> None:
    interval = ValidBootstrapIntervalResult(
        method=StatisticalMethod.BCA_BOOTSTRAP,
        point_estimate=0.6,
        lower=0.5,
        upper=0.7,
        confidence=ConfidenceLevel(value=Decimal("0.95")),
        resamples=BootstrapResampleCount(value=10),
    )
    failed = FailedAnchorReproductionResult(
        reproduced_interval=interval,
        movement_assessment=AnchorMovementAssessment.MATERIAL_TOWARD_ZERO,
        failure=AnchorReproductionFailure(
            detail="synthetic", reference_interval="[0.1, 0.2]", reproduced_interval="[0, 1]"
        ),
    )
    source = DatasetSourceIdentity(value=StageFingerprint(value="a" * 64))
    partition = PartitionIdentity(value=StageFingerprint(value="b" * 64))
    decision = _regime_d_gate().evaluate(
        FeasibilityGateRequest(
            evidence=RegimeDFeasibilityEvidence(
                audited_source_identity=source,
                audited_partition_identity=partition,
                requested_source_identity=DatasetSourceIdentity(value=StageFingerprint(value="c" * 64)),
                requested_partition_identity=partition,
                eligibility_coverage=CoverageRatio(value=Decimal("0.89")),
            )
        )
    )

    request = AnchorReproductionGateRequest(result=failed)
    gate = AnchorReproductionGate()
    assert not gate.evaluate(request).readiness.is_ready
    with pytest.raises(AnchorReproductionFailure):
        gate.require_anchor_passage(request)
    assert decision.readiness.blockers == (BlockingReason.INVALID_LINEAGE, BlockingReason.FAILED_FEASIBILITY)


def test_tracer_refuses_a_provenance_gap_before_rendering() -> None:
    required = _artifact(character="a", artifact_type=ArtifactType.TABLE_INPUT)
    freeze = _artifact(character="b", artifact_type=ArtifactType.RESULT_FREEZE)
    request = TraceReportArtifactRequest(
        output=_artifact(character="c", artifact_type=ArtifactType.RENDERED_TABLE),
        specification=_table_specification(),
        required_inputs=ArtifactReferenceCollection(references=(required,)),
        provenance_chain=ArtifactReferenceCollection(references=()),
        result_freeze=ResultFreezeEligibility(
            result_freeze=freeze,
            readiness=ScientificReadinessResult(blockers=()),
        ),
    )
    tracer = TableFigureTracer()

    with pytest.raises(ProvenanceError):
        tracer.trace(request)


def test_feasibility_accepts_the_exact_minimum_coverage_for_matching_lineage() -> None:
    source = DatasetSourceIdentity(value=StageFingerprint(value="a" * 64))
    partition = PartitionIdentity(value=StageFingerprint(value="b" * 64))

    decision = _regime_d_gate().evaluate(
        FeasibilityGateRequest(
            evidence=RegimeDFeasibilityEvidence(
                audited_source_identity=source,
                audited_partition_identity=partition,
                requested_source_identity=source,
                requested_partition_identity=partition,
                eligibility_coverage=CoverageRatio(value=Decimal("0.90")),
            )
        )
    )

    assert decision.readiness.is_ready


def test_tracer_returns_a_closed_trace_only_after_a_eligible_freeze() -> None:
    required = _artifact(character="a", artifact_type=ArtifactType.TABLE_INPUT)
    freeze = _artifact(character="b", artifact_type=ArtifactType.RESULT_FREEZE)
    output = _artifact(character="c", artifact_type=ArtifactType.RENDERED_TABLE)

    traced = TableFigureTracer().trace(
        TraceReportArtifactRequest(
            output=output,
            specification=_table_specification(),
            required_inputs=ArtifactReferenceCollection(references=(required,)),
            provenance_chain=ArtifactReferenceCollection(references=(required,)),
            result_freeze=ResultFreezeEligibility(
                result_freeze=freeze,
                readiness=ScientificReadinessResult(blockers=()),
            ),
        )
    )

    assert traced.output == output
    assert traced.result_freeze == freeze


def test_tracer_rejects_a_blocked_result_freeze_before_provenance_evaluation() -> None:
    request = TraceReportArtifactRequest(
        output=_artifact(character="a", artifact_type=ArtifactType.RENDERED_TABLE),
        specification=_table_specification(),
        required_inputs=ArtifactReferenceCollection(references=()),
        provenance_chain=ArtifactReferenceCollection(references=()),
        result_freeze=ResultFreezeEligibility(
            result_freeze=_artifact(character="b", artifact_type=ArtifactType.RESULT_FREEZE),
            readiness=ScientificReadinessResult(blockers=(BlockingReason.FAILED_ANCHOR_GATE,)),
        ),
    )
    tracer = TableFigureTracer()

    with pytest.raises(DomainValidationError):
        tracer.trace(request)


@given(st.lists(st.sampled_from(tuple(BlockingReason)), unique=True))
def test_readiness_preserves_every_supplied_blocker(blockers: list[BlockingReason]) -> None:
    result = ScientificReadinessEvaluator().evaluate(blockers=tuple(blockers))

    assert result.blockers == tuple(blockers)
