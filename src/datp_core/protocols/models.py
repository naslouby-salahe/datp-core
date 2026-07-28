"""Frozen, typed scientific declarations."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp_core.domain.enums import (
    CentralizedModelId,
    CentralizedThresholdMethod,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values import (
    CalibrationSize,
    ClientCount,
    ConfidenceLevel,
    CoverageTarget,
    DittoRegularization,
    LocalEpochCount,
    ProximalCoefficient,
    Quantile,
    Ratio,
    RoundNumber,
    ShrinkageWeight,
    SummaryCoefficient,
)


class Declaration(BaseModel):
    """Common immutable Pydantic configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class SeedCohort(Declaration):
    values: tuple[int, ...]

    @model_validator(mode="after")
    def validate_values(self) -> "SeedCohort":
        if len(self.values) != 10 or any(isinstance(value, bool) or value < 0 for value in self.values):
            raise ValueError("a seed cohort requires ten non-negative integer seeds")
        if len(set(self.values)) != len(self.values):
            raise ValueError("seed cohort values must be unique")
        return self


class FractionalSplitProtocol(Declaration):
    training: Ratio
    calibration: Ratio
    evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "FractionalSplitProtocol":
        if abs(self.training.value + self.calibration.value + self.evaluation.value - 1.0) > 1e-12:
            raise ValueError("fractional split must sum to one")
        return self


class TemporalSplitProtocol(Declaration):
    historical_training: Ratio
    historical_calibration: Ratio
    future_recalibration: Ratio
    future_evaluation: Ratio

    @model_validator(mode="after")
    def validate_total(self) -> "TemporalSplitProtocol":
        total = sum(
            (
                self.historical_training.value,
                self.historical_calibration.value,
                self.future_recalibration.value,
                self.future_evaluation.value,
            )
        )
        if abs(total - 1.0) > 1e-12:
            raise ValueError("temporal split must sum to one")
        return self


class CheckpointProtocol(Declaration):
    candidates: tuple[RoundNumber, ...]
    maximum_round: RoundNumber

    @model_validator(mode="after")
    def validate_candidates(self) -> "CheckpointProtocol":
        values = tuple(candidate.value for candidate in self.candidates)
        if not values or values != tuple(sorted(values)) or len(set(values)) != len(values):
            raise ValueError("checkpoint candidates must be unique and ordered")
        if values[-1] != self.maximum_round.value:
            raise ValueError("maximum round must be the final checkpoint candidate")
        return self


class AutoencoderProtocol(Declaration):
    widths: tuple[int, ...]


class OptimizerProtocol(Declaration):
    identity: str


class FedAvgProtocol(Declaration):
    kind: Literal[TrainingModelId.FEDAVG_AUTOENCODER]
    local_epochs: LocalEpochCount
    optimizer: OptimizerProtocol


class FedProxProtocol(Declaration):
    kind: Literal[TrainingModelId.FEDPROX_AUTOENCODER]
    local_epochs: LocalEpochCount
    optimizer: OptimizerProtocol
    coefficient: ProximalCoefficient


class DittoProtocol(Declaration):
    kind: Literal[TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER]
    regularization: DittoRegularization


TrainingProtocol = Annotated[FedAvgProtocol | FedProxProtocol | DittoProtocol, Field(discriminator="kind")]


class CentralizedTrainingProtocol(Declaration):
    kind: Literal[CentralizedModelId.CENTRALIZED_AUTOENCODER]
    optimizer: OptimizerProtocol


class CentralizedQuantileProtocol(Declaration):
    method: Literal[CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE]
    quantile: Quantile


class CalibrationEligibilityProtocol(Declaration):
    minimum_support: CalibrationSize


class QuantileProtocol(Declaration):
    method: Literal[
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    ]
    quantile: Quantile


class CalibrationSizeProtocol(Declaration):
    sizes: tuple[CalibrationSize, ...]


class FixedShrinkageProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE]
    weights: tuple[ShrinkageWeight, ...]


class SizeAwareShrinkageProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE]
    minimum_support: CalibrationSize


class ConformalProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD]
    coverage: CoverageTarget
    significance: Ratio

    @model_validator(mode="after")
    def validate_complement(self) -> "ConformalProtocol":
        if abs(self.coverage.value + self.significance.value - 1.0) > 1e-12:
            raise ValueError("coverage and significance must be complements")
        return self


class FederatedStatisticsProtocol(Declaration):
    method: Literal[FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS]
    coefficients: tuple[SummaryCoefficient, ...]


class MetricProtocol(Declaration):
    metrics: tuple[MetricId, ...]


class StatisticalInferenceProtocol(Declaration):
    confidence_level: ConfidenceLevel
    paired_seed_count: ClientCount


class TrafficRateEvidence(Declaration):
    population: PopulationId
    source_locator: str


class PopulationDeclaration(Declaration):
    id: PopulationId
    dataset: DatasetId
    client_count: ClientCount
    has_attack_assignment: bool
    has_chronology: bool
    has_family_taxonomy: bool
    confirmatory_eligible: bool


class ExperimentDeclaration(Declaration):
    id: ExperimentId
    role: EvidenceRole
    population: PopulationId
    training_model: TrainingModelId
    federated_thresholds: tuple[FederatedThresholdMethod, ...]
    metrics: tuple[MetricId, ...]


class AnchorReference(Declaration):
    metric: MetricId
    value: float


class AnchorDecisionProtocol(Declaration):
    references: tuple[AnchorReference, ...]


class RuntimeProtocol(Declaration):
    data_root: Path
    outputs_root: Path
    require_cuda: bool
    worker_count: int
    overwrite_outputs: bool

    @model_validator(mode="after")
    def validate_paths(self) -> "RuntimeProtocol":
        if self.data_root.is_absolute() or self.outputs_root.is_absolute():
            raise ValueError("runtime paths must be project-relative")
        if self.data_root.parts[0] != "data" or self.outputs_root.parts[0] != "outputs":
            raise ValueError("runtime paths must remain under data and outputs")
        if isinstance(self.worker_count, bool) or self.worker_count < 1:
            raise ValueError("worker count must be positive")
        return self


class ResolvedProtocolGraph(Declaration):
    populations: tuple[PopulationDeclaration, ...]
    experiments: tuple[ExperimentDeclaration, ...]
    temporal_split: TemporalSplitProtocol
    checkpoint: CheckpointProtocol
    calibration: CalibrationEligibilityProtocol
