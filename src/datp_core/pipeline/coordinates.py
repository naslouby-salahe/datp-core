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

    @property
    def experiment(self) -> ExperimentId: ...

    @property
    def evidence_role(self) -> EvidenceRole: ...

    @property
    def dataset(self) -> DatasetId: ...

    @property
    def population(self) -> PopulationId: ...

    @property
    def training_model(self) -> TrainingModelId: ...

    @property
    def training_seed(self) -> Seed: ...

    @property
    def split_protocol(self) -> SplitProtocolId: ...

    @property
    def threshold_method(self) -> FederatedThresholdMethod: ...

    @property
    def metric(self) -> MetricId: ...

    @property
    def temporal_state(self) -> TemporalState | None: ...
