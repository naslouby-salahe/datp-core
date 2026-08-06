from pathlib import Path

import pytest
from tests.unit.anchor.helpers import make_reference

from datp_core.anchor.comparison import (
    AbsoluteToleranceRule,
    AnchorObservationSourceKind,
    AnchorObservedMetric,
    ExactEqualityRule,
    MetricInterval,
    RelativeToleranceRule,
)
from datp_core.anchor.reproduction import (
    ANCHOR_CHECKPOINT_STATUS,
    ANCHOR_METRIC,
    ANCHOR_POPULATION,
    ANCHOR_TRAINING_MODEL,
)
from datp_core.domain.enums import (
    CheckpointStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue


def test_reference_locks_historical_coordinates() -> None:
    reference = make_reference(
        value=1.0,
        rule=AbsoluteToleranceRule(absolute_tolerance=MetricValue(1e-12)),
    )
    assert reference.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert reference.training_model is TrainingModelId.FEDAVG_AUTOENCODER
    assert reference.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    assert reference.checkpoint_status is CheckpointStatus.HISTORICAL_ENDPOINT
    assert reference.population is ANCHOR_POPULATION
    assert reference.training_model is ANCHOR_TRAINING_MODEL
    assert reference.metric is ANCHOR_METRIC
    assert reference.checkpoint_status is ANCHOR_CHECKPOINT_STATUS


def test_reference_rejects_non_historical_checkpoint_semantics() -> None:
    with pytest.raises(ScientificContractError, match="historical endpoint"):
        make_reference(
            rule=ExactEqualityRule(),
            checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        )


def test_relative_tolerance_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        RelativeToleranceRule(relative_tolerance=MetricValue(0.0))


def test_metric_interval_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError, match="lower bound"):
        MetricInterval(lower=MetricValue(1.0), upper=MetricValue(0.5))


def test_observation_requires_anchor_evidence_role() -> None:
    with pytest.raises(ValueError, match="anchor_reproduction"):
        AnchorObservedMetric(
            seed=Seed(0),
            population=PopulationId.CICIOT_FILE_CLIENTS,
            training_model=TrainingModelId.FEDAVG_AUTOENCODER,
            threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
            value=MetricValue(1.0),
            checkpoint_status=CheckpointStatus.HISTORICAL_ENDPOINT,
            source_kind=AnchorObservationSourceKind.HISTORICAL_ARTIFACT,
            artifact_path=Path("metrics.json"),
            artifact_checksum=Checksum("a" * 64),
            model_checkpoint_identity=Checksum("b" * 64),
            evidence_role=EvidenceRole.CONFIRMATORY,
        )
