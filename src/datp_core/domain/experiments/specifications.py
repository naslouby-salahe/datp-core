from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import TYPE_CHECKING, assert_never

from datp_core.domain.artifacts.keys import ArtifactNamespace
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedModelIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
    StageIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.datasets import Dataset, Regime, TimestampEvidence
from datp_core.domain.data.partitioning import (
    N_BAIOT_NATURAL_DEVICE_COUNT,
    ClientDefinitionStrategy,
    DirichletAlpha,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.metrics import (
    ClusterMetric,
    DetectionQualityMetric,
    DiagnosticRatio,
    DistributionMetric,
    EquityMetric,
    EstimationMetric,
    MetricId,
    OperatingPointMetric,
    ResourceMetric,
)
from datp_core.domain.evaluation.statistical_results import (
    ClaimOutcome,
    CoverageRatio,
    PairedDeltaDirection,
    Probability,
    StatisticalAnalysisSpec,
)
from datp_core.domain.experiments.claims import ClaimTier, ExecutionStatus, ExperimentRole
from datp_core.domain.experiments.feasibility import FeasibilityStatus, ScientificReadinessResult
from datp_core.domain.experiments.identities import ArchitectureCatalogueId, CellId, ExperimentId, ExperimentIdentity
from datp_core.domain.experiments.protocols import (
    ArtifactPolicy,
    ExecutionPolicy,
    ProtocolTrack,
    ReportArtifactType,
    ReportingPolicy,
    ScientificProtocolSpec,
)
from datp_core.domain.learning.training import AggregationStrategy, ParticipationStrategy
from datp_core.domain.runtime.seeds import EnumMap, SeedTuple
from datp_core.domain.thresholding.clustering import CanonicalB4ClusteringProfile
from datp_core.domain.thresholding.federated_statistics import FedStatsK
from datp_core.domain.thresholding.policies import (
    B0PooledThresholdSpec,
    FprTarget,
    LocalThresholdSpec,
    SharedThresholdConstruction,
    SharedThresholdSpec,
    ThresholdPercentile,
)
from datp_core.domain.thresholding.variants import ShrinkageWeight

if TYPE_CHECKING:
    from datp_core.domain.thresholding.policies import ThresholdConstructionSpec


class ManuscriptPlacement(StrEnum):
    MAIN = "main"
    SUPPLEMENT = "supplement"
    SUPPRESSION_NOTE = "suppression_note"


class SweepAxis(StrEnum):
    QUANTILE = "quantile"
    DIRICHLET_ALPHA = "dirichlet_alpha"
    CALIBRATION_SIZE = "calibration_size"
    SHRINKAGE_WEIGHT = "shrinkage_weight"
    FED_STATS_K = "fed_stats_k"


type SweepValue = ThresholdPercentile | DirichletAlpha | CalibrationSampleCount | ShrinkageWeight | FedStatsK

_METRIC_ID_TYPES = (
    OperatingPointMetric,
    DetectionQualityMetric,
    EquityMetric,
    EstimationMetric,
    ClusterMetric,
    DistributionMetric,
    DiagnosticRatio,
    ResourceMetric,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AbsorptionGateSpec:
    strongly_useful_fraction: Probability
    partial_absorption_fraction: Probability
    alternative_path_distance: Probability

    def __post_init__(self) -> None:
        if self.partial_absorption_fraction.value >= self.strongly_useful_fraction.value:
            raise DomainValidationError(
                detail="the partial-absorption band must sit strictly below the strongly-useful band",
                value=repr(self),
                constraint="partial_absorption_fraction < strongly_useful_fraction",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalRecoveryGateSpec:
    meaningful_recovery_fraction: Probability

    def __post_init__(self) -> None:
        if type(self.meaningful_recovery_fraction) is not Probability:
            raise DomainValidationError(
                detail="temporal recovery gate requires a typed recovery fraction",
                value=repr(self),
                constraint="Probability",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeDViabilityGateSpec:
    minimum_eligibility_coverage: CoverageRatio
    minimum_calibration_samples: CalibrationSampleCount

    def __post_init__(self) -> None:
        if (
            type(self.minimum_eligibility_coverage) is not CoverageRatio
            or type(self.minimum_calibration_samples) is not CalibrationSampleCount
        ):
            raise DomainValidationError(
                detail="Regime D viability gate requires typed eligibility coverage and calibration samples",
                value=repr(self),
                constraint="CoverageRatio and CalibrationSampleCount",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatorySignRequirement:
    direction: PairedDeltaDirection

    def __post_init__(self) -> None:
        if self.direction is not PairedDeltaDirection.B1_MINUS_B2:
            raise DomainValidationError(
                detail="confirmatory sign requirement must retain the locked B1 minus B2 direction",
                value=repr(self.direction),
                constraint="B1_MINUS_B2",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SuppressionGateSpec:
    outcome: ClaimOutcome

    def __post_init__(self) -> None:
        if self.outcome is not ClaimOutcome.SUPPRESSED:
            raise DomainValidationError(
                detail="suppression gate must retain the explicit suppressed outcome",
                value=repr(self.outcome),
                constraint="ClaimOutcome.SUPPRESSED",
            )


def _is_confirmatory_protocol(protocol: ScientificProtocolSpec, statistics: StatisticalAnalysisSpec) -> bool:
    constructions = protocol.evaluation_arm.thresholds.constructions
    return all(
        (
            _has_confirmatory_threshold_constructions(constructions),
            _has_confirmatory_dataset_and_partitioning(protocol),
            _has_confirmatory_training(protocol),
            _has_confirmatory_evaluation(protocol, statistics),
        )
    )


def _has_confirmatory_threshold_constructions(
    constructions: tuple[ThresholdConstructionSpec, ...],
) -> bool:
    if tuple(type(construction) for construction in constructions) != (SharedThresholdSpec, LocalThresholdSpec):
        return False
    first_construction = constructions[0]
    if not isinstance(first_construction, SharedThresholdSpec):
        return False
    return first_construction.construction is SharedThresholdConstruction.MEAN


def _has_confirmatory_dataset_and_partitioning(protocol: ScientificProtocolSpec) -> bool:
    return (
        protocol.regime_data.dataset.dataset is Dataset.N_BAIOT
        and protocol.regime_data.partitioning.strategy is ClientDefinitionStrategy.NATURAL_DEVICE
    )


def _has_confirmatory_training(protocol: ScientificProtocolSpec) -> bool:
    federation = protocol.detector_branch.training.federation
    return (
        federation.aggregation is AggregationStrategy.FEDAVG
        and federation.local_epochs == 1
        and federation.participation is ParticipationStrategy.FULL
    )


def _has_confirmatory_evaluation(
    protocol: ScientificProtocolSpec,
    statistics: StatisticalAnalysisSpec,
) -> bool:
    return (
        protocol.evaluation_arm.evaluation.primary_metric is OperatingPointMetric.CV_FPR
        and protocol.statistics == statistics
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactDependencySpec:
    required_artifacts: tuple[ArtifactType, ...]

    def __post_init__(self) -> None:
        if not _has_unique_typed_artifact_dependencies(self.required_artifacts):
            raise DomainValidationError(
                detail="profile artifact dependencies must be a non-empty unique typed tuple",
                value=repr(self.required_artifacts),
                constraint="unique tuple[ArtifactType, ...]",
            )


def _has_unique_typed_artifact_dependencies(required_artifacts: tuple[ArtifactType, ...]) -> bool:
    return all(
        (
            bool(required_artifacts),
            all(type(artifact) is ArtifactType for artifact in required_artifacts),
            len(set(required_artifacts)) == len(required_artifacts),
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class FallbackPolicySpec:
    outcomes: tuple[ClaimOutcome, ...]

    def __post_init__(self) -> None:
        if not _has_unique_typed_fallback_outcomes(self.outcomes):
            raise DomainValidationError(
                detail="fallback policy requires unique declared claim outcomes",
                value=repr(self.outcomes),
                constraint="unique tuple[ClaimOutcome, ...]",
            )


def _has_unique_typed_fallback_outcomes(outcomes: tuple[ClaimOutcome, ...]) -> bool:
    return all(
        (
            bool(outcomes),
            all(type(outcome) is ClaimOutcome for outcome in outcomes),
            len(set(outcomes)) == len(outcomes),
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ManuscriptRoleSpec:
    placement: ManuscriptPlacement
    report_artifacts: tuple[ReportArtifactType, ...]

    def __post_init__(self) -> None:
        if (
            type(self.placement) is not ManuscriptPlacement
            or any(type(artifact) is not ReportArtifactType for artifact in self.report_artifacts)
            or len(set(self.report_artifacts)) != len(self.report_artifacts)
        ):
            raise DomainValidationError(
                detail="manuscript role requires a typed placement and unique typed report artifacts",
                value=repr(self),
                constraint="ManuscriptPlacement and unique tuple[ReportArtifactType, ...]",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimSpec:
    identity: ExperimentIdentity
    fallback_policy: FallbackPolicySpec
    manuscript_role: ManuscriptRoleSpec

    def __post_init__(self) -> None:
        if not _has_claim_component_types(self):
            raise DomainValidationError(
                detail="claim requires a typed experiment identity, fallback policy, and manuscript role",
                value=repr(self),
                constraint="ExperimentIdentity, FallbackPolicySpec, ManuscriptRoleSpec",
            )


def _has_claim_component_types(claim: ClaimSpec) -> bool:
    return (
        type(claim.identity) is ExperimentIdentity
        and type(claim.fallback_policy) is FallbackPolicySpec
        and type(claim.manuscript_role) is ManuscriptRoleSpec
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeCompatibilitySpec:
    regime: Regime
    dataset: Dataset
    client_strategy: ClientDefinitionStrategy
    client_count: int | None
    feasibility_status: FeasibilityStatus
    boundary_only: bool
    timestamp_evidence: TimestampEvidence | None

    def __post_init__(self) -> None:
        if not _is_authorized_regime_compatibility(self):
            raise DomainValidationError(
                detail="regime compatibility must be one closed architecture-approved mapping",
                value=repr(self),
                constraint="Architecture section 8.3 regime mapping",
            )


def _is_authorized_regime_compatibility(specification: RegimeCompatibilitySpec) -> bool:
    match specification.regime:
        case Regime.A:
            return _matches_natural_regime_a(specification)
        case Regime.B_A:
            return _matches_boundary_regime_ba(specification)
        case Regime.C:
            return _matches_dirichlet_regime_c(specification)
        case Regime.D:
            return _matches_regime_d(specification)
        case Regime.D_TEMPORAL:
            return _matches_temporal_regime_d(specification)
        case _:
            assert_never(specification.regime)


def _matches_natural_regime_a(specification: RegimeCompatibilitySpec) -> bool:
    return (
        specification.dataset,
        specification.client_strategy,
        specification.client_count,
        specification.feasibility_status,
        specification.boundary_only,
        specification.timestamp_evidence,
    ) == (
        Dataset.N_BAIOT,
        ClientDefinitionStrategy.NATURAL_DEVICE,
        N_BAIOT_NATURAL_DEVICE_COUNT,
        FeasibilityStatus.FEASIBLE,
        False,
        None,
    )


def _matches_boundary_regime_ba(specification: RegimeCompatibilitySpec) -> bool:
    return (
        specification.dataset,
        specification.client_strategy,
        specification.client_count,
        specification.feasibility_status,
        specification.boundary_only,
        specification.timestamp_evidence,
    ) == (
        Dataset.CICIOT2023,
        ClientDefinitionStrategy.FILE_PSEUDO_CLIENT,
        63,
        FeasibilityStatus.FEASIBLE,
        True,
        None,
    )


def _matches_dirichlet_regime_c(specification: RegimeCompatibilitySpec) -> bool:
    return (
        specification.dataset,
        specification.client_strategy,
        specification.client_count,
        specification.feasibility_status,
        specification.boundary_only,
        specification.timestamp_evidence,
    ) == (
        Dataset.N_BAIOT,
        ClientDefinitionStrategy.DIRICHLET_SYNTHETIC,
        20,
        FeasibilityStatus.FEASIBLE,
        False,
        None,
    )


def _matches_regime_d(specification: RegimeCompatibilitySpec) -> bool:
    return _matches_edge_regime(specification, boundary_only=False, timestamp_evidence=None)


def _matches_temporal_regime_d(specification: RegimeCompatibilitySpec) -> bool:
    return _matches_edge_regime(
        specification,
        boundary_only=True,
        timestamp_evidence=TimestampEvidence,
    )


def _matches_edge_regime(
    specification: RegimeCompatibilitySpec,
    *,
    boundary_only: bool,
    timestamp_evidence: type[TimestampEvidence] | None,
) -> bool:
    return (
        specification.dataset is Dataset.EDGE_IIOTSET
        and specification.client_strategy
        in {ClientDefinitionStrategy.DEVICE_CLIENT, ClientDefinitionStrategy.GROUP_CLIENT}
        and specification.client_count is None
        and specification.feasibility_status is FeasibilityStatus.FEASIBLE
        and specification.boundary_only is boundary_only
        and _matches_timestamp_evidence(specification.timestamp_evidence, timestamp_evidence)
    )


def _matches_timestamp_evidence(
    actual: TimestampEvidence | None,
    expected_type: type[TimestampEvidence] | None,
) -> bool:
    if expected_type is None:
        return actual is None
    return type(actual) is expected_type


@dataclass(frozen=True, slots=True, kw_only=True)
class SweepSpec:
    axis: SweepAxis
    values: tuple[SweepValue, ...]
    catalogue: ProfileCatalogueSpec

    def __post_init__(self) -> None:
        if not _is_authorized_sweep(self):
            raise DomainValidationError(
                detail="sweep requires an authorized ordered unique typed grid",
                value=repr(self.values),
                constraint="non-empty unique profile-catalogue grid",
            )

    def expand(self, *, profile: ExperimentProfileSpec) -> tuple[ScientificProtocolSpec, ...]:
        return profile.authorized_protocols


def _is_authorized_sweep(sweep: SweepSpec) -> bool:
    if not _has_authorized_sweep_shape(sweep):
        return False
    return _has_authorized_sweep_values(sweep)


def _has_authorized_sweep_shape(sweep: SweepSpec) -> bool:
    return type(sweep.axis) is SweepAxis and bool(sweep.values) and type(sweep.catalogue) is ProfileCatalogueSpec


def _has_authorized_sweep_values(sweep: SweepSpec) -> bool:
    expected_type = _sweep_value_type(sweep.axis)
    return (
        all(type(value) is expected_type for value in sweep.values)
        and len(set(sweep.values)) == len(sweep.values)
        and set(sweep.values).issubset(sweep.catalogue.grid_for(axis=sweep.axis))
    )


def _sweep_value_type(axis: SweepAxis) -> type[SweepValue]:
    match axis:
        case SweepAxis.QUANTILE:
            return ThresholdPercentile
        case SweepAxis.DIRICHLET_ALPHA:
            return DirichletAlpha
        case SweepAxis.CALIBRATION_SIZE:
            return CalibrationSampleCount
        case SweepAxis.SHRINKAGE_WEIGHT:
            return ShrinkageWeight
        case SweepAxis.FED_STATS_K:
            return FedStatsK
        case _:
            assert_never(axis)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentProfileSpec:
    catalogue_id: ExperimentId | ArchitectureCatalogueId
    claim: ClaimSpec
    regime_compatibility: RegimeCompatibilitySpec
    authorized_protocols: tuple[ScientificProtocolSpec, ...]
    authorized_seed_plan: SeedTuple
    primary_metrics: tuple[MetricId, ...]
    secondary_metrics: tuple[MetricId, ...]
    statistical_procedure: StatisticalAnalysisSpec
    artifact_dependencies: ArtifactDependencySpec

    def __post_init__(self) -> None:
        if not _is_valid_experiment_profile(self):
            raise DomainValidationError(
                detail="experiment profile must hold one closed non-overlapping scientific authorization set",
                value=repr(self),
                constraint="non-empty unique authorized protocols and primary metrics",
            )


def _is_valid_experiment_profile(profile: ExperimentProfileSpec) -> bool:
    return all(
        (
            _has_profile_component_types(profile),
            _has_valid_profile_protocols(profile),
            _has_valid_profile_metrics(profile),
            _has_matching_catalogue_identity(profile),
            _has_matching_regime_protocols(profile),
            _has_confirmatory_role_matching_subtype(profile),
        )
    )


def _has_confirmatory_role_matching_subtype(profile: ExperimentProfileSpec) -> bool:
    if profile.claim.identity.evidence_role is ExperimentRole.CONFIRMATORY:
        return type(profile) is ConfirmatoryExperimentProfileSpec
    return True


def _has_profile_component_types(profile: ExperimentProfileSpec) -> bool:
    return all(
        (
            type(profile.claim) is ClaimSpec,
            type(profile.regime_compatibility) is RegimeCompatibilitySpec,
            type(profile.authorized_seed_plan) is SeedTuple,
            type(profile.statistical_procedure) is StatisticalAnalysisSpec,
            type(profile.artifact_dependencies) is ArtifactDependencySpec,
        )
    )


def _has_valid_profile_protocols(profile: ExperimentProfileSpec) -> bool:
    protocols = profile.authorized_protocols
    return (
        bool(protocols)
        and all(type(protocol) is ScientificProtocolSpec for protocol in protocols)
        and len(set(protocols)) == len(protocols)
    )


def _has_valid_profile_metrics(profile: ExperimentProfileSpec) -> bool:
    primary_metrics = profile.primary_metrics
    secondary_metrics = profile.secondary_metrics
    return (
        bool(primary_metrics)
        and _are_unique_metric_identifiers(primary_metrics)
        and _are_unique_metric_identifiers(secondary_metrics)
        and not set(primary_metrics).intersection(secondary_metrics)
    )


def _are_unique_metric_identifiers(metrics: tuple[MetricId, ...]) -> bool:
    return all(type(metric) in _METRIC_ID_TYPES for metric in metrics) and len(set(metrics)) == len(metrics)


def _has_matching_catalogue_identity(profile: ExperimentProfileSpec) -> bool:
    catalogue_id = profile.catalogue_id
    if type(catalogue_id) is ExperimentId:
        return profile.claim.identity.experiment_id == catalogue_id
    if type(catalogue_id) is ArchitectureCatalogueId:
        return catalogue_id.value == "B_A_APPLICABILITY_BOUNDARY"
    return False


def _has_matching_regime_protocols(profile: ExperimentProfileSpec) -> bool:
    compatibility = profile.regime_compatibility
    return all(_matches_profile_regime(protocol, compatibility) for protocol in profile.authorized_protocols)


def _matches_profile_regime(
    protocol: ScientificProtocolSpec,
    compatibility: RegimeCompatibilitySpec,
) -> bool:
    return (
        protocol.regime_data.dataset.dataset is compatibility.dataset
        and protocol.regime_data.partitioning.regime is compatibility.regime
        and protocol.regime_data.partitioning.strategy is compatibility.client_strategy
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatoryExperimentProfileSpec(ExperimentProfileSpec):
    def __post_init__(self) -> None:
        ExperimentProfileSpec.__post_init__(self)
        if not _is_locked_confirmatory_profile(self):
            raise DomainValidationError(
                detail="confirmatory profile must use the locked E-C1 regime, metric, seed cohort, and BCa procedure",
                value=repr(self),
                constraint="E-C1 confirmatory profile",
            )


def _is_locked_confirmatory_profile(profile: ConfirmatoryExperimentProfileSpec) -> bool:
    return all(
        (
            _has_confirmatory_identity(profile),
            _has_confirmatory_statistical_contract(profile),
            _has_confirmatory_protocols(profile),
        )
    )


def _has_confirmatory_identity(profile: ConfirmatoryExperimentProfileSpec) -> bool:
    return (
        profile.catalogue_id == ExperimentId(value="E-C1")
        and profile.claim.identity.evidence_role is ExperimentRole.CONFIRMATORY
        and profile.claim.identity.tier is ClaimTier.TIER_1
        and profile.regime_compatibility.regime is Regime.A
        and profile.primary_metrics == (OperatingPointMetric.CV_FPR,)
    )


def _has_confirmatory_statistical_contract(profile: ConfirmatoryExperimentProfileSpec) -> bool:
    return (
        profile.statistical_procedure.is_confirmatory_locked
        and len(profile.authorized_seed_plan.values) == profile.statistical_procedure.paired_seed_count
    )


def _has_confirmatory_protocols(profile: ConfirmatoryExperimentProfileSpec) -> bool:
    return all(
        _is_confirmatory_protocol(protocol, profile.statistical_procedure) for protocol in profile.authorized_protocols
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedModelComparatorSpec:
    model_identity: CentralizedModelIdentity
    checkpoint_identity: CentralizedCheckpointIdentity
    calibration_score_identity: CentralizedCalibrationScoringIdentity
    test_score_identity: CentralizedTestScoringIdentity
    threshold_identity: CentralizedThresholdIdentity
    evaluation_identity: CentralizedEvaluationIdentity

    def __post_init__(self) -> None:
        if (
            type(self.model_identity) is not CentralizedModelIdentity
            or type(self.checkpoint_identity) is not CentralizedCheckpointIdentity
            or type(self.calibration_score_identity) is not CentralizedCalibrationScoringIdentity
            or type(self.test_score_identity) is not CentralizedTestScoringIdentity
            or type(self.threshold_identity) is not CentralizedThresholdIdentity
            or type(self.evaluation_identity) is not CentralizedEvaluationIdentity
        ):
            raise DomainValidationError(
                detail="centralized comparator requires complete independent lineage identifiers",
                value=repr(self),
                constraint="non-empty centralized B0 lineage",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedModelComparatorProfileSpec:
    catalogue_id: ArchitectureCatalogueId
    identity: ExperimentIdentity
    comparator: CentralizedModelComparatorSpec
    reporting_policy: ReportingPolicy

    def __post_init__(self) -> None:
        if (
            type(self.catalogue_id) is not ArchitectureCatalogueId
            or type(self.identity) is not ExperimentIdentity
            or type(self.comparator) is not CentralizedModelComparatorSpec
            or type(self.reporting_policy) is not ReportingPolicy
        ):
            raise DomainValidationError(
                detail="B0 requires its disjoint centralized comparator profile route",
                value=repr(self),
                constraint=(
                    "ArchitectureCatalogueId, ExperimentIdentity, CentralizedModelComparatorSpec, ReportingPolicy"
                ),
            )


def _b0_identity(role: str) -> StageFingerprint:
    return StageFingerprint(value=sha256(f"b0-centralized-comparator-{role}".encode()).hexdigest())


LOCKED_B0_CENTRALIZED_COMPARATOR_PROFILE = CentralizedModelComparatorProfileSpec(
    catalogue_id=ArchitectureCatalogueId(value="B0_CENTRALIZED_COMPARATOR"),
    identity=ExperimentIdentity(
        experiment_id=ExperimentId(value="E-B0"),
        evidence_role=ExperimentRole.SUPPORTIVE,
        tier=ClaimTier.TIER_2,
        execution_status=ExecutionStatus.MANDATORY,
    ),
    comparator=CentralizedModelComparatorSpec(
        model_identity=CentralizedModelIdentity(value=_b0_identity("model")),
        checkpoint_identity=CentralizedCheckpointIdentity(value=_b0_identity("checkpoint")),
        calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_b0_identity("calibration-score")),
        test_score_identity=CentralizedTestScoringIdentity(value=_b0_identity("test-score")),
        threshold_identity=CentralizedThresholdIdentity(value=_b0_identity("threshold")),
        evaluation_identity=CentralizedEvaluationIdentity(value=_b0_identity("evaluation")),
    ),
    reporting_policy=ReportingPolicy(
        tables=(),
        figures=(),
        report_artifacts=(),
        formats=EnumMap(entries=(), allowed_keys=(), is_sparse=False),
        wording_outcomes=(),
    ),
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentSpec:
    claim: ClaimSpec
    profile: ExperimentProfileSpec
    scientific_protocol: ScientificProtocolSpec
    execution_policy: ExecutionPolicy
    artifact_policy: ArtifactPolicy
    reporting_policy: ReportingPolicy

    def __post_init__(self) -> None:
        if not _is_valid_experiment_specification(self):
            raise DomainValidationError(
                detail="experiment specifications can be constructed only from their closed profile authorization",
                value=repr(self.claim.identity),
                constraint="profile claim and authorized scientific protocol",
            )


def _is_valid_experiment_specification(specification: ExperimentSpec) -> bool:
    return all(
        (
            _has_experiment_specification_types(specification),
            _has_profile_authorized_protocol(specification),
            _has_matching_artifact_namespace(specification),
            _has_matching_manuscript_report_artifacts(specification),
        )
    )


def _has_experiment_specification_types(specification: ExperimentSpec) -> bool:
    return all(
        (
            type(specification.claim) is ClaimSpec,
            type(specification.profile) in {ExperimentProfileSpec, ConfirmatoryExperimentProfileSpec},
            type(specification.scientific_protocol) is ScientificProtocolSpec,
            type(specification.execution_policy) is ExecutionPolicy,
            type(specification.artifact_policy) is ArtifactPolicy,
            type(specification.reporting_policy) is ReportingPolicy,
        )
    )


def _has_profile_authorized_protocol(specification: ExperimentSpec) -> bool:
    return (
        specification.claim == specification.profile.claim
        and specification.scientific_protocol in specification.profile.authorized_protocols
    )


def _has_matching_artifact_namespace(specification: ExperimentSpec) -> bool:
    match specification.scientific_protocol.track:
        case ProtocolTrack.DATP_ANCHOR:
            return specification.artifact_policy.namespace is ArtifactNamespace.DATP_ANCHOR
        case ProtocolTrack.COMPLETE:
            return specification.artifact_policy.namespace is ArtifactNamespace.COMPLETE
        case _:
            assert_never(specification.scientific_protocol.track)


def _has_matching_manuscript_report_artifacts(specification: ExperimentSpec) -> bool:
    return specification.claim.manuscript_role.report_artifacts == specification.reporting_policy.report_artifacts


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentCell:
    cell_id: CellId
    experiment_id: ExperimentId
    scientific_protocol: ScientificProtocolSpec
    execution_policy: ExecutionPolicy
    artifact_policy: ArtifactPolicy
    reporting_policy: ReportingPolicy
    stage_identities: StageIdentity
    scientific_readiness: ScientificReadinessResult

    def __post_init__(self) -> None:
        if not _has_cell_component_types(self):
            raise DomainValidationError(
                detail="experiment cell requires every resolved specification in its declared typed position",
                value=repr(self.cell_id),
                constraint="CellId, ExperimentId, ScientificProtocolSpec, ExecutionPolicy, "
                "ArtifactPolicy, ReportingPolicy, StageIdentity, ScientificReadinessResult",
            )


def _has_cell_component_types(cell: ExperimentCell) -> bool:
    return all(
        (
            type(cell.cell_id) is CellId,
            type(cell.experiment_id) is ExperimentId,
            type(cell.scientific_protocol) is ScientificProtocolSpec,
            type(cell.execution_policy) is ExecutionPolicy,
            type(cell.artifact_policy) is ArtifactPolicy,
            type(cell.reporting_policy) is ReportingPolicy,
            type(cell.stage_identities) is StageIdentity,
            type(cell.scientific_readiness) is ScientificReadinessResult,
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileCatalogueSpec:
    quantile_grid: tuple[ThresholdPercentile, ...]
    dirichlet_alpha_grid: tuple[DirichletAlpha, ...]
    calibration_size_grid: tuple[CalibrationSampleCount, ...]
    shrinkage_weight_grid: tuple[ShrinkageWeight, ...]
    conformal_alpha: FprTarget
    fed_stats_k_grid: tuple[FedStatsK, ...]
    b0_pooled_threshold: B0PooledThresholdSpec
    canonical_b4_profile: CanonicalB4ClusteringProfile
    absorption_gates: AbsorptionGateSpec
    temporal_recovery_gate: TemporalRecoveryGateSpec
    regime_d_viability_gate: RegimeDViabilityGateSpec
    suppression_gate: SuppressionGateSpec
    confirmatory_sign_requirement: ConfirmatorySignRequirement
    evidence_roles: tuple[ExperimentRole, ...]
    main_placement: ManuscriptPlacement
    supplementary_placement: ManuscriptPlacement

    def __post_init__(self) -> None:
        if not _is_closed_profile_catalogue(self):
            raise DomainValidationError(
                detail="profile catalogue must retain every fixed grid and typed reporting gate",
                value=repr(self),
                constraint="closed roadmap grids, gates, evidence roles, and manuscript placements",
            )

    def grid_for(self, *, axis: SweepAxis) -> tuple[SweepValue, ...]:
        match axis:
            case SweepAxis.QUANTILE:
                return self.quantile_grid
            case SweepAxis.DIRICHLET_ALPHA:
                return self.dirichlet_alpha_grid
            case SweepAxis.CALIBRATION_SIZE:
                return self.calibration_size_grid
            case SweepAxis.SHRINKAGE_WEIGHT:
                return self.shrinkage_weight_grid
            case SweepAxis.FED_STATS_K:
                return self.fed_stats_k_grid
            case _:
                assert_never(axis)


def _is_closed_profile_catalogue(catalogue: ProfileCatalogueSpec) -> bool:
    return all(
        (
            _has_catalogue_grids(catalogue),
            _has_catalogue_gates(catalogue),
            _has_catalogue_reporting_contract(catalogue),
        )
    )


def _has_catalogue_grids(catalogue: ProfileCatalogueSpec) -> bool:
    return all(
        (
            _is_strictly_increasing_grid(catalogue.quantile_grid, value_type=ThresholdPercentile),
            _is_unique_grid(catalogue.dirichlet_alpha_grid, value_type=DirichletAlpha),
            _is_strictly_increasing_grid(catalogue.calibration_size_grid, value_type=CalibrationSampleCount),
            _is_unit_interval_grid(catalogue.shrinkage_weight_grid),
            type(catalogue.conformal_alpha) is FprTarget,
            _is_unique_grid(catalogue.fed_stats_k_grid, value_type=FedStatsK),
            type(catalogue.b0_pooled_threshold) is B0PooledThresholdSpec,
            type(catalogue.canonical_b4_profile) is CanonicalB4ClusteringProfile,
        )
    )


def _is_strictly_increasing_grid(grid: tuple[SweepValue, ...], *, value_type: type) -> bool:
    if not grid or any(type(item) is not value_type for item in grid):
        return False
    values = tuple(item.value for item in grid)
    return values == tuple(sorted(set(values)))


def _is_unique_grid(grid: tuple[SweepValue, ...], *, value_type: type) -> bool:
    return bool(grid) and all(type(item) is value_type for item in grid) and len(set(grid)) == len(grid)


def _is_unit_interval_grid(grid: tuple[ShrinkageWeight, ...]) -> bool:
    if not _is_strictly_increasing_grid(grid, value_type=ShrinkageWeight):
        return False
    values = tuple(item.value for item in grid)
    return values[0] == 0.0 and values[-1] == 1.0


def _has_catalogue_gates(catalogue: ProfileCatalogueSpec) -> bool:
    return all(
        (
            type(catalogue.absorption_gates) is AbsorptionGateSpec,
            type(catalogue.temporal_recovery_gate) is TemporalRecoveryGateSpec,
            type(catalogue.regime_d_viability_gate) is RegimeDViabilityGateSpec,
            type(catalogue.suppression_gate) is SuppressionGateSpec,
            type(catalogue.confirmatory_sign_requirement) is ConfirmatorySignRequirement,
        )
    )


def _has_catalogue_reporting_contract(catalogue: ProfileCatalogueSpec) -> bool:
    return (
        catalogue.evidence_roles == tuple(ExperimentRole)
        and catalogue.main_placement is ManuscriptPlacement.MAIN
        and catalogue.supplementary_placement is ManuscriptPlacement.SUPPLEMENT
    )
