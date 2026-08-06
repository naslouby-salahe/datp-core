"""Historical five-seed anchor reproduction without confirmatory-cohort substitution."""

from enum import StrEnum
from json import loads
from pathlib import Path

from pydantic import ConfigDict, ValidationError, field_validator, model_validator

from datp_core.anchor.comparison import (
    AbsoluteToleranceRule,
    AnchorComparisonDecision,
    AnchorDiscrepancy,
    AnchorDiscrepancyReason,
    AnchorMetricComparison,
    AnchorMetricReference,
    AnchorObservationSourceKind,
    AnchorObservedMetric,
    AnchorSeedSubsetComparison,
    compare_anchor_metric,
)
from datp_core.anchor.models import _require_non_empty_detail
from datp_core.domain.contracts import StrictModel
from datp_core.domain.enums import (
    CheckpointStatus,
    ContractSubject,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values.base import str_enum_schema
from datp_core.domain.values.checksums import Checksum, checksum_file
from datp_core.domain.values.counts import ClientCount, Seed, SeedCount
from datp_core.domain.values.ratios import MetricValue
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL, HISTORICAL_ANCHOR_SEED_COHORT, AnchorDecisionProtocol
from datp_core.protocols.populations import NBAIOT_NATURAL_DEVICES
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort

ANCHOR_EXPERIMENT: ExperimentId = ExperimentId.HISTORICAL_DATP_REPRODUCTION
ANCHOR_POPULATION: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES
ANCHOR_TRAINING_MODEL: TrainingModelId = TrainingModelId.FEDAVG_AUTOENCODER
ANCHOR_METRIC: MetricId = MetricId.FPR_COEFFICIENT_OF_VARIATION
ANCHOR_CHECKPOINT_STATUS: CheckpointStatus = CheckpointStatus.HISTORICAL_ENDPOINT
ANCHOR_EVIDENCE_ROLE: EvidenceRole = EvidenceRole.ANCHOR_REPRODUCTION
ANCHOR_HISTORICAL_SEED_COUNT: SeedCount = HISTORICAL_ANCHOR_SEED_COHORT.member_count
CONFIRMATORY_PAIRED_SEED_COUNT: SeedCount = CONFIRMATORY_SEED_COHORT.member_count
HISTORICAL_ELIGIBLE_CLIENT_COUNT: ClientCount = NBAIOT_NATURAL_DEVICES.client_count

# No non-blocking discrepancy reasons are currently declared in the scientific source.
DECLARED_NON_BLOCKING_DISCREPANCY_REASONS: frozenset[AnchorDiscrepancyReason] = frozenset()


class AnchorDependencyKind(StrEnum):
    FEDERATED_TRAINING_CHECKPOINTING_AND_SCORING = "federated_training_checkpointing_and_scoring"
    HISTORICAL_ARTIFACT_ROOT = "historical_artifact_root"


class HistoricalThresholdScopeToken(StrEnum):
    """Semantic threshold-scope tokens stored in historical metrics artifacts."""

    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"

    __get_pydantic_core_schema__ = classmethod(str_enum_schema)

    def to_threshold_method(self) -> FederatedThresholdMethod:
        match self:
            case HistoricalThresholdScopeToken.ELIGIBLE_CLIENT_ARITHMETIC_MEAN:
                return FederatedThresholdMethod.SHARED_THRESHOLD
            case HistoricalThresholdScopeToken.PER_CLIENT_PERCENTILE:
                return FederatedThresholdMethod.LOCAL_THRESHOLD


class HistoricalDatasetToken(StrEnum):
    NBAIOT = "nbaiot"

    __get_pydantic_core_schema__ = classmethod(str_enum_schema)


class HistoricalRegimeToken(StrEnum):
    PHYSICAL_DEVICE_ANCHOR = "a"

    __get_pydantic_core_schema__ = classmethod(str_enum_schema)


class AnchorArtifactFileName(StrEnum):
    """On-disk artifact file names used by historical load and stage diagnostics."""

    METRICS = "metrics.json"
    GATE_DECISION = "anchor_gate_decision.json"
    DISCREPANCIES = "anchor_discrepancies.json"
    GATE_COMPLETION = "anchor_gate_complete.json"


class AnchorSeedDirectoryPrefix(StrEnum):
    SEED = "seed_"


class HistoricalBoundaryModel(StrictModel):
    """External historical-artifact boundary. Extra legacy fields are ignored, never trusted."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)


class HistoricalArtifactProvenanceDocument(HistoricalBoundaryModel):
    model_checkpoint_identity: Checksum
    score_artifact_identity: Checksum
    split_manifest_identity: Checksum
    config_identity: Checksum
    metric_code_version: Checksum
    threshold_code_version: Checksum
    package_version: Checksum
    generated_at_utc: str


class HistoricalMetricsDocument(HistoricalBoundaryModel):
    """Boundary model for historical seed-level metrics artifacts."""

    seed: Seed
    dataset: HistoricalDatasetToken
    regime: HistoricalRegimeToken
    threshold_scope: HistoricalThresholdScopeToken
    cv_fpr: MetricValue
    client_count: ClientCount
    eligible_count: ClientCount
    provenance: HistoricalArtifactProvenanceDocument


class AnchorDependencyBlocker(StrictModel):
    kind: AnchorDependencyKind
    detail: str

    @field_validator("detail")
    @classmethod
    def validate_detail(cls, v: str) -> str:
        return _require_non_empty_detail(v)


class AnchorReproductionResult(StrictModel):
    experiment: ExperimentId
    evidence_role: EvidenceRole
    seed_cohort: SeedCohort
    references: tuple[AnchorMetricReference, ...]
    observations: tuple[AnchorObservedMetric, ...]
    seed_subset_comparison: AnchorSeedSubsetComparison
    metric_comparisons: tuple[AnchorMetricComparison, ...]
    discrepancies: tuple[AnchorDiscrepancy, ...]
    dependency_blocker: AnchorDependencyBlocker | None = None

    @model_validator(mode="after")
    def validate_identity(self) -> "AnchorReproductionResult":
        if self.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ValueError("anchor reproduction requires the historical DATP reproduction experiment")
        if self.evidence_role is not EvidenceRole.ANCHOR_REPRODUCTION:
            raise ValueError("anchor reproduction requires the anchor_reproduction evidence role")
        return self


class HistoricalMetricArtifactSource(StrictModel):
    path: Path
    seed: Seed
    threshold_method: FederatedThresholdMethod

    @model_validator(mode="after")
    def validate_threshold_method(self) -> "HistoricalMetricArtifactSource":
        if self.threshold_method not in {
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        }:
            raise ValueError("historical anchor artifacts support only shared and local thresholds")
        return self


def references_from_protocol(
    protocol: AnchorDecisionProtocol = ANCHOR_DECISION_PROTOCOL,
) -> tuple[AnchorMetricReference, ...]:
    validate_historical_seed_cohort(protocol.seed_cohort)
    references: list[AnchorMetricReference] = []
    for item in protocol.references:
        if item.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
            raise AnchorReproductionError(
                "anchor protocol reference metric is not CV(FPR)",
                subject=item.metric,
                reason=AnchorDiscrepancyReason.WRONG_METRIC.value,
            )
        references.append(
            AnchorMetricReference(
                seed=item.seed,
                population=ANCHOR_POPULATION,
                training_model=ANCHOR_TRAINING_MODEL,
                threshold_method=item.threshold_method,
                metric=item.metric,
                value=item.value,
                tolerance_rule=AbsoluteToleranceRule(
                    absolute_tolerance=(
                        item.absolute_tolerance
                        if isinstance(item.absolute_tolerance, MetricValue)
                        else MetricValue(item.absolute_tolerance.value)
                    )
                ),
                checkpoint_status=ANCHOR_CHECKPOINT_STATUS,
            )
        )
    return tuple(references)


def validate_historical_seed_cohort(seed_cohort: SeedCohort) -> SeedCohort:
    values = seed_cohort.values
    member_count = seed_cohort.member_count
    if member_count == CONFIRMATORY_PAIRED_SEED_COUNT or seed_cohort == CONFIRMATORY_SEED_COHORT:
        raise AnchorReproductionError(
            "confirmatory ten-seed paired cohort cannot enter anchor reproduction",
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.CONFIRMATORY_TEN_SEED_COHORT_REJECTED.value,
        )
    if member_count != ANCHOR_HISTORICAL_SEED_COUNT:
        raise AnchorReproductionError(
            "anchor reproduction requires exactly the historical five-seed cohort",
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.WRONG_SEED_SUBSET.value,
        )
    if len(set(values)) != len(values):
        raise AnchorReproductionError(
            "anchor seed cohort contains duplicate seeds",
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.DUPLICATE_SEED.value,
        )
    if seed_cohort != HISTORICAL_ANCHOR_SEED_COHORT:
        raise AnchorReproductionError(
            "anchor seed cohort must match the declared historical five-seed cohort",
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.WRONG_SEED_SUBSET.value,
        )
    return seed_cohort


def independent_reproduction_dependency_blocker() -> AnchorDependencyBlocker:
    return AnchorDependencyBlocker(
        kind=AnchorDependencyKind.FEDERATED_TRAINING_CHECKPOINTING_AND_SCORING,
        detail=(
            "Independent re-execution of historical training, checkpointing, and scoring "
            "requires the federated training and scoring workflow"
        ),
    )


def load_historical_observation(source: HistoricalMetricArtifactSource) -> AnchorObservedMetric:
    path = source.path
    document = _read_historical_metrics_document(path)
    _validate_historical_document(document, source)
    return AnchorObservedMetric(
        seed=source.seed,
        population=ANCHOR_POPULATION,
        training_model=ANCHOR_TRAINING_MODEL,
        threshold_method=source.threshold_method,
        metric=ANCHOR_METRIC,
        value=document.cv_fpr,
        checkpoint_status=ANCHOR_CHECKPOINT_STATUS,
        source_kind=AnchorObservationSourceKind.HISTORICAL_ARTIFACT,
        artifact_path=path.resolve(),
        artifact_checksum=checksum_file(path),
        model_checkpoint_identity=document.provenance.model_checkpoint_identity,
        evidence_role=ANCHOR_EVIDENCE_ROLE,
    )


def _read_historical_metrics_document(path: Path) -> HistoricalMetricsDocument:
    if not path.is_file():
        raise AnchorReproductionError(
            "historical metrics artifact is missing",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION.value,
        )
    try:
        return HistoricalMetricsDocument.model_validate(loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError, TypeError) as error:
        raise AnchorReproductionError(
            "historical metrics artifact failed schema validation",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.STALE_OR_MISMATCHED_ARTIFACT.value,
        ) from error


def _validate_historical_document(
    document: HistoricalMetricsDocument,
    source: HistoricalMetricArtifactSource,
) -> None:
    if document.seed != source.seed:
        raise AnchorReproductionError(
            "historical metrics seed does not match the artifact coordinate",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_SEED_SUBSET.value,
        )
    if document.dataset is not HistoricalDatasetToken.NBAIOT:
        raise AnchorReproductionError(
            "historical metrics artifact is not N-BaIoT",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_POPULATION.value,
        )
    if document.regime is not HistoricalRegimeToken.PHYSICAL_DEVICE_ANCHOR:
        raise AnchorReproductionError(
            "historical metrics artifact is not the physical-device anchor regime",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.STALE_OR_MISMATCHED_ARTIFACT.value,
        )
    if document.client_count != HISTORICAL_ELIGIBLE_CLIENT_COUNT:
        raise AnchorReproductionError(
            "historical metrics artifact client count is not the locked nine-device population",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_POPULATION.value,
        )
    if document.eligible_count != HISTORICAL_ELIGIBLE_CLIENT_COUNT:
        raise AnchorReproductionError(
            "historical metrics artifact eligible count is not the locked nine-device population",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_POPULATION.value,
        )
    if document.threshold_scope.to_threshold_method() is not source.threshold_method:
        raise AnchorReproductionError(
            "historical threshold scope does not match the artifact coordinate",
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD.value,
        )


def load_historical_observations(
    sources: tuple[HistoricalMetricArtifactSource, ...],
) -> tuple[AnchorObservedMetric, ...]:
    if not sources:
        raise AnchorReproductionError(
            "historical observation sources are required",
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION.value,
        )
    coordinates = tuple((source.seed, source.threshold_method) for source in sources)
    if len(set(coordinates)) != len(coordinates):
        raise AnchorReproductionError(
            "duplicate historical observation coordinates",
            reason=AnchorDiscrepancyReason.DUPLICATE_SEED.value,
        )
    return tuple(load_historical_observation(source) for source in sources)


def historical_sources_for_seed_directories(
    shared_root: Path,
    local_root: Path,
    seed_cohort: SeedCohort = HISTORICAL_ANCHOR_SEED_COHORT,
) -> tuple[HistoricalMetricArtifactSource, ...]:
    """Build typed sources from descriptive shared/local result directories."""
    validate_historical_seed_cohort(seed_cohort)
    sources: list[HistoricalMetricArtifactSource] = []
    for seed in seed_cohort.values:
        seed_directory = f"{AnchorSeedDirectoryPrefix.SEED.value}{seed.value}"
        sources.append(
            HistoricalMetricArtifactSource(
                path=shared_root / seed_directory / AnchorArtifactFileName.METRICS.value,
                seed=seed,
                threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            )
        )
        sources.append(
            HistoricalMetricArtifactSource(
                path=local_root / seed_directory / AnchorArtifactFileName.METRICS.value,
                seed=seed,
                threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            )
        )
    return tuple(sources)


def reproduce_anchor(
    *,
    protocol: AnchorDecisionProtocol = ANCHOR_DECISION_PROTOCOL,
    observations: tuple[AnchorObservedMetric, ...] | None = None,
    dependency_blocker: AnchorDependencyBlocker | None = None,
) -> AnchorReproductionResult:
    """Compare protocol references to observations for the historical five-seed cohort."""
    seed_cohort = validate_historical_seed_cohort(protocol.seed_cohort)
    references = references_from_protocol(protocol)
    resolved_observations = () if observations is None else observations
    _reject_confirmatory_only_artifacts(resolved_observations)
    _reject_non_historical_checkpoint(resolved_observations)

    seed_subset = _compare_seed_subsets(seed_cohort, resolved_observations)
    observation_index = {(item.seed, item.threshold_method, item.metric): item for item in resolved_observations}
    if len(observation_index) != len(resolved_observations):
        seed_subset = AnchorSeedSubsetComparison(
            expected_seeds=seed_cohort.values,
            observed_seeds=tuple(item.seed for item in resolved_observations),
            decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
            reason=AnchorDiscrepancyReason.DUPLICATE_SEED,
        )

    comparisons = tuple(
        compare_anchor_metric(
            reference,
            observation_index.get((reference.seed, reference.threshold_method, reference.metric)),
        )
        for reference in references
    )
    discrepancies = _collect_discrepancies(comparisons, seed_subset, dependency_blocker)
    return AnchorReproductionResult(
        experiment=ANCHOR_EXPERIMENT,
        evidence_role=ANCHOR_EVIDENCE_ROLE,
        seed_cohort=seed_cohort,
        references=references,
        observations=resolved_observations,
        seed_subset_comparison=seed_subset,
        metric_comparisons=comparisons,
        discrepancies=discrepancies,
        dependency_blocker=dependency_blocker,
    )


def _compare_seed_subsets(
    seed_cohort: SeedCohort,
    observations: tuple[AnchorObservedMetric, ...],
) -> AnchorSeedSubsetComparison:
    expected = seed_cohort.values
    observed = tuple(sorted({item.seed for item in observations}, key=lambda seed: seed.value))
    if not observations:
        return AnchorSeedSubsetComparison(
            expected_seeds=expected,
            observed_seeds=observed,
            decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
        )
    if observed == expected:
        return AnchorSeedSubsetComparison(
            expected_seeds=expected,
            observed_seeds=observed,
            decision=AnchorComparisonDecision.EQUIVALENT,
            reason=None,
        )
    reason = (
        AnchorDiscrepancyReason.CONFIRMATORY_TEN_SEED_COHORT_REJECTED
        if len(observed) == CONFIRMATORY_PAIRED_SEED_COUNT.value
        else AnchorDiscrepancyReason.WRONG_SEED_SUBSET
    )
    return AnchorSeedSubsetComparison(
        expected_seeds=expected,
        observed_seeds=observed,
        decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
        reason=reason,
    )


def _reject_confirmatory_only_artifacts(observations: tuple[AnchorObservedMetric, ...]) -> None:
    seeds = {item.seed for item in observations}
    if len(seeds) >= CONFIRMATORY_PAIRED_SEED_COUNT.value:
        raise AnchorReproductionError(
            "confirmatory ten-seed cohort cannot supply anchor observations",
            reason=AnchorDiscrepancyReason.CONFIRMATORY_TEN_SEED_COHORT_REJECTED.value,
        )
    confirmatory_only = {
        Seed(value)
        for value in range(CONFIRMATORY_PAIRED_SEED_COUNT.value)
        if Seed(value) not in HISTORICAL_ANCHOR_SEED_COHORT.values
    }
    if seeds & confirmatory_only:
        raise AnchorReproductionError(
            "observations include confirmatory-only seeds outside the historical five-seed cohort",
            reason=AnchorDiscrepancyReason.CONFIRMATORY_TEN_SEED_COHORT_REJECTED.value,
        )


def _reject_non_historical_checkpoint(observations: tuple[AnchorObservedMetric, ...]) -> None:
    """Reject non-historical checkpoint candidates as a cohort-level structural failure."""
    if any(item.checkpoint_status is not ANCHOR_CHECKPOINT_STATUS for item in observations):
        raise AnchorReproductionError(
            "non-historical checkpoint selection cannot enter historical anchor reproduction",
            subject=ANCHOR_CHECKPOINT_STATUS,
            reason=AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS.value,
        )


def _collect_discrepancies(
    comparisons: tuple[AnchorMetricComparison, ...],
    seed_subset: AnchorSeedSubsetComparison,
    dependency_blocker: AnchorDependencyBlocker | None,
) -> tuple[AnchorDiscrepancy, ...]:
    discrepancies: list[AnchorDiscrepancy] = []
    if seed_subset.decision is not AnchorComparisonDecision.EQUIVALENT:
        discrepancies.append(AnchorDiscrepancy.from_seed_subset(seed_subset))
    for comparison in comparisons:
        if comparison.decision is AnchorComparisonDecision.EQUIVALENT:
            continue
        discrepancies.append(AnchorDiscrepancy.from_comparison(comparison))
    if dependency_blocker is not None:
        discrepancies.append(AnchorDiscrepancy.from_dependency_blocker(dependency_blocker))
    return tuple(discrepancies)
