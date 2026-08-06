from pathlib import Path

from datp_core.anchor.models import (
    ANCHOR_CHECKPOINT_STATUS,
    ANCHOR_METRIC,
    ANCHOR_POPULATION,
    ANCHOR_TRAINING_MODEL,
    AnchorArtifactFileName,
    AnchorMetricReference,
    AnchorObservationSourceKind,
    AnchorObservedMetric,
    AnchorToleranceRule,
    ExactEqualityRule,
    MetricInterval,
)
from datp_core.anchor.reproduction import references_from_protocol
from datp_core.domain.enums import (
    CheckpointStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import ClientCount, Seed
from datp_core.domain.values.ratios import MetricValue


def matching_anchor_observations() -> tuple[AnchorObservedMetric, ...]:
    return tuple(
        AnchorObservedMetric(
            seed=reference.seed,
            population=reference.population,
            training_model=reference.training_model,
            threshold_method=reference.threshold_method,
            metric=reference.metric,
            value=reference.value,
            checkpoint_status=reference.checkpoint_status,
            source_kind=AnchorObservationSourceKind.HISTORICAL_ARTIFACT,
            artifact_path=Path(f"{reference.threshold_method.value}_{reference.seed.value}.json"),
            artifact_checksum=Checksum("a" * 64),
            model_checkpoint_identity=Checksum("b" * 64),
            evidence_role=EvidenceRole.ANCHOR_REPRODUCTION,
        )
        for reference in references_from_protocol()
    )


def make_reference(
    *,
    value: float = 1.0,
    rule: AnchorToleranceRule | None = None,
    checkpoint_status: CheckpointStatus = ANCHOR_CHECKPOINT_STATUS,
    interval: MetricInterval | None = None,
    count: ClientCount | None = None,
) -> AnchorMetricReference:
    return AnchorMetricReference(
        seed=Seed(0),
        population=ANCHOR_POPULATION,
        training_model=ANCHOR_TRAINING_MODEL,
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        metric=ANCHOR_METRIC,
        value=MetricValue(value),
        tolerance_rule=rule or ExactEqualityRule(),
        checkpoint_status=checkpoint_status,
        interval=interval,
        count=count,
    )


def make_observation(
    *,
    value: float = 1.0,
    seed: Seed | None = None,
    population: PopulationId = ANCHOR_POPULATION,
    training_model: TrainingModelId = ANCHOR_TRAINING_MODEL,
    threshold_method: FederatedThresholdMethod = FederatedThresholdMethod.SHARED_THRESHOLD,
    metric: MetricId = ANCHOR_METRIC,
    checkpoint_status: CheckpointStatus = ANCHOR_CHECKPOINT_STATUS,
    interval: MetricInterval | None = None,
    count: ClientCount | None = None,
) -> AnchorObservedMetric:
    return AnchorObservedMetric(
        seed=Seed(0) if seed is None else seed,
        population=population,
        training_model=training_model,
        threshold_method=threshold_method,
        metric=metric,
        value=MetricValue(value),
        checkpoint_status=checkpoint_status,
        source_kind=AnchorObservationSourceKind.HISTORICAL_ARTIFACT,
        artifact_path=Path(AnchorArtifactFileName.METRICS.value),
        artifact_checksum=Checksum("a" * 64),
        model_checkpoint_identity=Checksum("b" * 64),
        evidence_role=EvidenceRole.ANCHOR_REPRODUCTION,
        interval=interval,
        count=count,
    )
