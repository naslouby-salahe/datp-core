"""Complete scientific coordinate contract shared by pipeline lifecycle services."""

from typing import Protocol, runtime_checkable

from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.domain.values import Seed


@runtime_checkable
class PipelineCoordinate(Protocol):
    """Scientific identity required to bind, validate, and reuse pipeline artifacts."""

    experiment: ExperimentId
    evidence_role: EvidenceRole
    dataset: DatasetId
    population: PopulationId
    training_model: TrainingModelId
    training_seed: Seed
    split_protocol: SplitProtocolId
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    temporal_state: TemporalState | None
