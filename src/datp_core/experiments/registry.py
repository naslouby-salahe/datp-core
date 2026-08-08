"""Typed experiment catalogue and bounded-evidence execution identities."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.core.errors import ScientificContractError
from datp_core.core.numeric import ConfidenceLevel

from .metrics import CONFIRMATORY_METRICS, OPERATING_POINT_METRICS, OPTIONAL_EQUITY_INDEX_METRICS
from .seeds import CONFIRMATORY_PAIRED_SEED_COUNT, SeedCohort


class ConfirmatoryDeltaDirection(StrEnum):
    SHARED_MINUS_LOCAL = "shared_minus_local"


class ExperimentDeclaration(StrictModel):
    id: ExperimentId
    role: EvidenceRole
    population: PopulationId
    training_model: TrainingModelId
    preprocessing_protocol: PreprocessingProtocolId
    federated_thresholds: tuple[FederatedThresholdMethod, ...]
    metrics: tuple[MetricId, ...]
    readiness: ExperimentReadiness

    @model_validator(mode="after")
    def validate_contents(self) -> "ExperimentDeclaration":
        if not self.federated_thresholds or not self.metrics:
            raise ValueError("experiments require threshold methods and metrics")
        if len(set(self.federated_thresholds)) != len(self.federated_thresholds):
            raise ValueError("experiment threshold methods must be unique")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("experiment metrics must be unique")
        if self.readiness is ExperimentReadiness.EXECUTABLE and self.role is EvidenceRole.OPERATIONAL_TRANSLATION:
            raise ValueError("operational translation experiments cannot be marked executable without rate evidence")
        return self


class ConfirmatoryEndpoint(StrictModel):
    experiment: Literal[ExperimentId.SHARED_VS_LOCAL_CONFIRMATION]
    population: Literal[PopulationId.NBAIOT_NATURAL_DEVICES]
    training_model: Literal[TrainingModelId.FEDAVG_AUTOENCODER]
    shared_threshold: Literal[FederatedThresholdMethod.SHARED_THRESHOLD]
    local_threshold: Literal[FederatedThresholdMethod.LOCAL_THRESHOLD]
    metric: Literal[MetricId.FPR_COEFFICIENT_OF_VARIATION]
    seed_cohort: SeedCohort
    positive_direction: Literal[ConfirmatoryDeltaDirection.SHARED_MINUS_LOCAL]
    interval_method: Literal[IntervalMethod.BCA_PAIRED_ARITHMETIC_MEAN]
    confidence_level: ConfidenceLevel

    @model_validator(mode="after")
    def validate_endpoint(self) -> "ConfirmatoryEndpoint":
        if self.seed_cohort.member_count != CONFIRMATORY_PAIRED_SEED_COUNT:
            raise ValueError("confirmatory endpoint requires the paired ten-seed journal cohort")
        return self


_SHARED_AND_LOCAL_METHODS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_SHARED_LOCAL_AND_GROUPED_METHODS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.CLUSTER_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_FULL_THRESHOLD_LADDER = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.FAMILY_THRESHOLD,
    FederatedThresholdMethod.CLUSTER_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_SHARED_THRESHOLD_CONSTRUCTIONS = (
    FederatedThresholdMethod.SHARED_THRESHOLD,
    FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
    FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
    FederatedThresholdMethod.LOCAL_THRESHOLD,
)
_FEDERATED_STATISTICS_COMPARISON_METHODS = _SHARED_THRESHOLD_CONSTRUCTIONS + (
    FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
)
_EDGE_BENIGN_EQUITY_METHODS = _FEDERATED_STATISTICS_COMPARISON_METHODS + (FederatedThresholdMethod.CLUSTER_THRESHOLD,)
_CALIBRATION_SIZE_METHODS = _SHARED_LOCAL_AND_GROUPED_METHODS + (
    FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
    FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
)
_TEMPORAL_METHODS = _SHARED_LOCAL_AND_GROUPED_METHODS + (FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionIdentityDeclaration:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_states: tuple[TemporalState | None, ...]

    def __post_init__(self) -> None:
        if not self.temporal_states:
            raise ValueError("execution identity declarations require at least one temporal state")
        if len(frozenset(self.temporal_states)) != len(self.temporal_states):
            raise ValueError("execution identity declaration temporal states must be unique")

    def matches(self, identity: "ExternalTemporalExecutionIdentity") -> bool:
        return (
            identity.experiment is self.experiment
            and identity.population is self.population
            and identity.evidence_role is self.evidence_role
            and identity.temporal_state in self.temporal_states
        )


EXECUTION_IDENTITY_DECLARATIONS = (
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        temporal_states=(None,),
    ),
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        population=PopulationId.CICIOT_FILE_CLIENTS,
        evidence_role=EvidenceRole.APPLICABILITY_BOUNDARY,
        temporal_states=(None,),
    ),
    ExecutionIdentityDeclaration(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_states=(
            TemporalState.STATIC_REFERENCE,
            TemporalState.FROZEN_FUTURE,
            TemporalState.RECALIBRATED_FUTURE,
        ),
    ),
)
BOUNDED_EVIDENCE_POPULATIONS = frozenset(declaration.population for declaration in EXECUTION_IDENTITY_DECLARATIONS)


class ExternalTemporalExecutionIdentity(StrictModel):
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    temporal_state: TemporalState | None

    @model_validator(mode="after")
    def validate_declared_identity(self) -> "ExternalTemporalExecutionIdentity":
        matches = tuple(declaration for declaration in EXECUTION_IDENTITY_DECLARATIONS if declaration.matches(self))
        if len(matches) != 1:
            raise ScientificContractError(
                "execution identity must be declared exactly once",
                subject=self.experiment,
            )
        return self

    def require_population(self, population: PopulationId) -> None:
        if self.population is not population:
            raise ScientificContractError(
                "execution identity population must match",
                subject=population,
            )

    def require_evidence_role(self, evidence_role: EvidenceRole) -> None:
        if self.evidence_role is not evidence_role:
            raise ScientificContractError(
                "execution identity evidence role must match",
                subject=evidence_role,
            )


def require_execution_identity(
    identity: ExternalTemporalExecutionIdentity | None,
    population: PopulationId,
) -> ExternalTemporalExecutionIdentity | None:
    if population not in BOUNDED_EVIDENCE_POPULATIONS:
        if identity is not None:
            raise ScientificContractError(
                "execution identity is reserved for bounded evidence",
                subject=population,
            )
        return None
    if identity is None:
        raise ScientificContractError(
            "bounded evidence requires an execution identity",
            subject=population,
        )
    identity.require_population(population)
    return identity


def _declared_readiness(
    experiment_id: ExperimentId,
    role: EvidenceRole,
) -> ExperimentReadiness:
    if experiment_id is ExperimentId.ALERT_BURDEN_TRANSLATION:
        return ExperimentReadiness.SUPPRESSED
    if role is EvidenceRole.OPERATIONAL_TRANSLATION:
        return ExperimentReadiness.SUPPRESSED
    return ExperimentReadiness.DECLARED


def _declare(
    experiment_id: ExperimentId,
    role: EvidenceRole,
    population: PopulationId,
    training_model: TrainingModelId,
    preprocessing_protocol: PreprocessingProtocolId,
    thresholds: tuple[FederatedThresholdMethod, ...],
    metrics: tuple[MetricId, ...],
) -> ExperimentDeclaration:
    return ExperimentDeclaration(
        id=experiment_id,
        role=role,
        population=population,
        training_model=training_model,
        preprocessing_protocol=preprocessing_protocol,
        federated_thresholds=thresholds,
        metrics=metrics,
        readiness=_declared_readiness(experiment_id, role),
    )


EXPERIMENTS = (
    _declare(
        ExperimentId.HISTORICAL_DATP_REPRODUCTION,
        EvidenceRole.ANCHOR_REPRODUCTION,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        EvidenceRole.CONFIRMATORY,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_THRESHOLD_CONSTRUCTIONS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.QUANTILE_SENSITIVITY,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FULL_THRESHOLD_LADDER,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        EvidenceRole.MECHANISM,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.CALIBRATION_SIZE_ABLATION,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _CALIBRATION_SIZE_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.FIXED_SHRINKAGE_CURVE,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,),
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.SIZE_AWARE_SHRINKAGE,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,),
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.LOCAL_CONFORMAL_COVERAGE,
        EvidenceRole.SUPPORTIVE,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,),
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.FEDERATED_BENIGN_STATISTICS_COMPARISON,
        EvidenceRole.THRESHOLD_VARIANT,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FEDERATED_STATISTICS_COMPARISON_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.FEDERATED_QUANTILE_ESTIMATION,
        EvidenceRole.THRESHOLD_VARIANT,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FEDERATED_STATISTICS_COMPARISON_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.FIXED_COEFFICIENT_STATISTICS_SENSITIVITY,
        EvidenceRole.THRESHOLD_VARIANT,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS + (FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,),
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        EvidenceRole.EXTERNAL_VALIDATION,
        PopulationId.EDGE_SENSOR_GROUPS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _EDGE_BENIGN_EQUITY_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        EvidenceRole.APPLICABILITY_BOUNDARY,
        PopulationId.CICIOT_FILE_CLIENTS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        EvidenceRole.TRAINING_STRESS_TEST,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDPROX_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _FULL_THRESHOLD_LADDER,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        EvidenceRole.TRAINING_STRESS_TEST,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        CONFIRMATORY_METRICS,
    ),
    _declare(
        ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        EvidenceRole.TEMPORAL_BOUNDARY,
        PopulationId.EDGE_TEMPORAL_GROUPS,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _TEMPORAL_METHODS,
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.ALERT_BURDEN_TRANSLATION,
        EvidenceRole.OPERATIONAL_TRANSLATION,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_AND_LOCAL_METHODS,
        (MetricId.ALERTS_PER_DAY,),
    ),
    _declare(
        ExperimentId.GROUP_MEDIAN_SUPPLEMENT,
        EvidenceRole.EXPLORATORY,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        (FederatedThresholdMethod.CLUSTER_THRESHOLD,),
        OPERATING_POINT_METRICS,
    ),
    _declare(
        ExperimentId.OPTIONAL_EQUITY_INDICES,
        EvidenceRole.EXPLORATORY,
        PopulationId.NBAIOT_NATURAL_DEVICES,
        TrainingModelId.FEDAVG_AUTOENCODER,
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        _SHARED_LOCAL_AND_GROUPED_METHODS,
        OPERATING_POINT_METRICS + OPTIONAL_EQUITY_INDEX_METRICS,
    ),
)
