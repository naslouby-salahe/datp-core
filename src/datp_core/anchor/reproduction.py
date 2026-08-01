"""Historical five-seed anchor reproduction without confirmatory-cohort substitution."""

from json import loads
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, ValidationError

from datp_core.anchor.comparison import compare_anchor_metric
from datp_core.anchor.models import (
    ANCHOR_CHECKPOINT_STATUS,
    ANCHOR_EVIDENCE_ROLE,
    ANCHOR_EXPERIMENT,
    ANCHOR_HISTORICAL_SEED_COUNT,
    ANCHOR_METRIC,
    ANCHOR_POPULATION,
    ANCHOR_TRAINING_MODEL,
    CONFIRMATORY_PAIRED_SEED_COUNT,
    HISTORICAL_ELIGIBLE_CLIENT_COUNT,
    AbsoluteToleranceRule,
    AnchorArtifactFileName,
    AnchorComparisonDecision,
    AnchorDependencyBlocker,
    AnchorDependencyKind,
    AnchorDiscrepancy,
    AnchorDiscrepancyReason,
    AnchorMetricComparison,
    AnchorMetricReference,
    AnchorObservationSourceKind,
    AnchorObservedMetric,
    AnchorReproductionResult,
    AnchorSeedDirectoryPrefix,
    AnchorSeedSubsetComparison,
    HistoricalDatasetToken,
    HistoricalMetricArtifactSource,
    HistoricalRegimeToken,
    HistoricalThresholdScopeToken,
)
from datp_core.domain.enums import ContractSubject, FederatedThresholdMethod, MetricId
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values import Checksum, ClientCount, MetricValue, Seed, checksum_file
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL, HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.protocols.models import AnchorDecisionProtocol, AnchorReference, SeedCohort
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT


def _as_seed(value: Seed | int) -> Seed:
    if isinstance(value, Seed):
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("seed must be an integer")
    return Seed(value)


def _as_metric_value(value: MetricValue | int | float) -> MetricValue:
    if isinstance(value, MetricValue):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("metric value must be numeric")
    return MetricValue(float(value))


def _as_client_count(value: ClientCount | int) -> ClientCount:
    if isinstance(value, ClientCount):
        return value
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("client count must be an integer")
    return ClientCount(value)


def _as_checksum(value: Checksum | str) -> Checksum:
    if isinstance(value, Checksum):
        return value
    if not isinstance(value, str):
        raise TypeError("checksum must be a string")
    return Checksum(value)


def _as_dataset_token(value: HistoricalDatasetToken | str) -> HistoricalDatasetToken:
    if isinstance(value, HistoricalDatasetToken):
        return value
    if not isinstance(value, str):
        raise TypeError("dataset token must be a string")
    return HistoricalDatasetToken(value)


def _as_regime_token(value: HistoricalRegimeToken | str) -> HistoricalRegimeToken:
    if isinstance(value, HistoricalRegimeToken):
        return value
    if not isinstance(value, str):
        raise TypeError("regime token must be a string")
    return HistoricalRegimeToken(value)


def _as_threshold_scope_token(
    value: HistoricalThresholdScopeToken | str,
) -> HistoricalThresholdScopeToken:
    if isinstance(value, HistoricalThresholdScopeToken):
        return value
    if not isinstance(value, str):
        raise TypeError("threshold scope token must be a string")
    return HistoricalThresholdScopeToken(value)


SeedField = Annotated[Seed, BeforeValidator(_as_seed)]
MetricValueField = Annotated[MetricValue, BeforeValidator(_as_metric_value)]
ClientCountField = Annotated[ClientCount, BeforeValidator(_as_client_count)]
ChecksumField = Annotated[Checksum, BeforeValidator(_as_checksum)]
DatasetField = Annotated[HistoricalDatasetToken, BeforeValidator(_as_dataset_token)]
RegimeField = Annotated[HistoricalRegimeToken, BeforeValidator(_as_regime_token)]
ThresholdScopeField = Annotated[HistoricalThresholdScopeToken, BeforeValidator(_as_threshold_scope_token)]


class HistoricalBoundaryModel(BaseModel):
    """External historical-artifact boundary. Extra legacy fields are ignored, never trusted."""

    model_config = ConfigDict(frozen=True, extra="ignore", strict=True)


class HistoricalArtifactProvenanceDocument(HistoricalBoundaryModel):
    model_checkpoint_identity: ChecksumField
    score_artifact_identity: ChecksumField
    split_manifest_identity: ChecksumField
    config_identity: ChecksumField
    metric_code_version: ChecksumField
    threshold_code_version: ChecksumField
    package_version: ChecksumField
    generated_at_utc: str


class HistoricalMetricsDocument(HistoricalBoundaryModel):
    """Boundary model for historical seed-level metrics artifacts."""

    seed: SeedField
    dataset: DatasetField
    regime: RegimeField
    threshold_scope: ThresholdScopeField
    cv_fpr: MetricValueField
    client_count: ClientCountField
    eligible_count: ClientCountField
    provenance: HistoricalArtifactProvenanceDocument


def references_from_protocol(
    protocol: AnchorDecisionProtocol = ANCHOR_DECISION_PROTOCOL,
) -> tuple[AnchorMetricReference, ...]:
    validate_historical_seed_cohort(protocol.seed_cohort)
    return tuple(_reference_from_declaration(item) for item in protocol.references)


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
    checks: tuple[tuple[bool, str, AnchorDiscrepancyReason], ...] = (
        (
            document.seed != source.seed,
            "historical metrics seed does not match the artifact coordinate",
            AnchorDiscrepancyReason.WRONG_SEED_SUBSET,
        ),
        (
            document.dataset is not HistoricalDatasetToken.NBAIOT,
            "historical metrics artifact is not N-BaIoT",
            AnchorDiscrepancyReason.WRONG_POPULATION,
        ),
        (
            document.regime is not HistoricalRegimeToken.PHYSICAL_DEVICE_ANCHOR,
            "historical metrics artifact is not the physical-device anchor regime",
            AnchorDiscrepancyReason.STALE_OR_MISMATCHED_ARTIFACT,
        ),
        (
            document.client_count != HISTORICAL_ELIGIBLE_CLIENT_COUNT,
            "historical metrics artifact client count is not the locked nine-device population",
            AnchorDiscrepancyReason.WRONG_POPULATION,
        ),
        (
            document.eligible_count != HISTORICAL_ELIGIBLE_CLIENT_COUNT,
            "historical metrics artifact eligible count is not the locked nine-device population",
            AnchorDiscrepancyReason.WRONG_POPULATION,
        ),
        (
            threshold_method_from_historical_scope(document.threshold_scope) is not source.threshold_method,
            "historical threshold scope does not match the artifact coordinate",
            AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD,
        ),
    )
    for failed, message, reason in checks:
        if failed:
            raise AnchorReproductionError(message, subject=ContractSubject.ARTIFACT_PATH, reason=reason.value)


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


def threshold_method_from_historical_scope(
    scope_token: HistoricalThresholdScopeToken | str,
) -> FederatedThresholdMethod:
    token = (
        scope_token
        if isinstance(scope_token, HistoricalThresholdScopeToken)
        else HistoricalThresholdScopeToken(scope_token)
    )
    match token:
        case HistoricalThresholdScopeToken.ELIGIBLE_CLIENT_ARITHMETIC_MEAN:
            return FederatedThresholdMethod.SHARED_THRESHOLD
        case HistoricalThresholdScopeToken.PER_CLIENT_PERCENTILE:
            return FederatedThresholdMethod.LOCAL_THRESHOLD
        case _:
            raise AnchorReproductionError(
                "unrecognized historical threshold scope token",
                subject=token,
                reason=AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD.value,
            )


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


def _reference_from_declaration(declaration: AnchorReference) -> AnchorMetricReference:
    if declaration.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
        raise AnchorReproductionError(
            "anchor protocol reference metric is not CV(FPR)",
            subject=declaration.metric,
            reason=AnchorDiscrepancyReason.WRONG_METRIC.value,
        )
    return AnchorMetricReference(
        seed=declaration.seed,
        population=ANCHOR_POPULATION,
        training_model=ANCHOR_TRAINING_MODEL,
        threshold_method=declaration.threshold_method,
        metric=declaration.metric,
        value=declaration.value,
        tolerance_rule=AbsoluteToleranceRule(absolute_tolerance=declaration.absolute_tolerance),
        checkpoint_status=ANCHOR_CHECKPOINT_STATUS,
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
        discrepancies.append(
            AnchorDiscrepancy(
                reason=seed_subset.reason or AnchorDiscrepancyReason.WRONG_SEED_SUBSET,
                seed=None,
                threshold_method=None,
                metric=None,
                expected_value=None,
                observed_value=None,
                signed_difference=None,
                relative_difference=None,
                tolerance_rule=None,
                artifact_path=None,
                artifact_checksum=None,
                detail=(
                    f"expected seeds {[seed.value for seed in seed_subset.expected_seeds]}; "
                    f"observed seeds {[seed.value for seed in seed_subset.observed_seeds]}"
                ),
            )
        )
    for comparison in comparisons:
        if comparison.decision is AnchorComparisonDecision.EQUIVALENT:
            continue
        observation = comparison.observation
        discrepancies.append(
            AnchorDiscrepancy(
                reason=comparison.reason or AnchorDiscrepancyReason.EXACT_MISMATCH,
                seed=comparison.reference.seed,
                threshold_method=comparison.reference.threshold_method,
                metric=comparison.reference.metric,
                expected_value=comparison.reference.value,
                observed_value=None if observation is None else observation.value,
                signed_difference=comparison.signed_difference,
                relative_difference=comparison.relative_difference,
                tolerance_rule=comparison.tolerance_rule,
                artifact_path=None if observation is None else observation.artifact_path,
                artifact_checksum=None if observation is None else observation.artifact_checksum,
                detail=_comparison_detail(comparison),
            )
        )
    if dependency_blocker is not None:
        discrepancies.append(
            AnchorDiscrepancy(
                reason=AnchorDiscrepancyReason.DEPENDENCY_BLOCKER,
                seed=None,
                threshold_method=None,
                metric=None,
                expected_value=None,
                observed_value=None,
                signed_difference=None,
                relative_difference=None,
                tolerance_rule=None,
                artifact_path=None,
                artifact_checksum=None,
                detail=dependency_blocker.detail,
            )
        )
    return tuple(discrepancies)


def _comparison_detail(comparison: AnchorMetricComparison) -> str:
    expected = comparison.reference.value.value
    observed = None if comparison.observation is None else comparison.observation.value.value
    return (
        f"seed={comparison.reference.seed.value} "
        f"method={comparison.reference.threshold_method.value} "
        f"metric={comparison.reference.metric.value} "
        f"expected={expected!r} observed={observed!r} "
        f"decision={comparison.decision.value} "
        f"reason={None if comparison.reason is None else comparison.reason.value}"
    )
