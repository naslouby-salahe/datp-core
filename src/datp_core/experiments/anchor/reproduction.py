"""Historical five-seed anchor reproduction without confirmatory-cohort substitution."""

from json import loads
from pathlib import Path

from pydantic import ValidationError

from datp_core.analysis.inference.bootstrap.contracts import BcaOutcome, BcaReason, BootstrapInterval
from datp_core.analysis.inference.bootstrap.estimation import seed_level_bca_interval
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    AnchorReproductionError,
    ErrorMessage,
)
from datp_core.core.identifiers import (
    CheckpointStatus,
    ContractSubject,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TrainingModelId,
)
from datp_core.core.numeric import ClientCount, MetricValue, Seed, SeedCount
from datp_core.data.populations.declarations import NBAIOT_NATURAL_DEVICES
from datp_core.experiments.anchor.comparison import compare_anchor_metric
from datp_core.experiments.anchor.contracts import (
    AbsoluteToleranceRule,
    AnchorArtifactFileName,
    AnchorBcaComparison,
    AnchorComparisonDecision,
    AnchorDependencyBlocker,
    AnchorDependencyKind,
    AnchorDetail,
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
    HistoricalMetricsDocument,
    HistoricalRegimeToken,
)
from datp_core.experiments.anchor.spec import (
    ANCHOR_DECISION_PROTOCOL,
    ANCHOR_INFERENCE_PROTOCOL,
    ANCHOR_MAXIMUM_OPERATIVE_WIDTH,
    ANCHOR_REFERENCE_INTERVAL,
    HISTORICAL_ANCHOR_SEED_COHORT,
    AnchorDecisionProtocol,
)
from datp_core.experiments.common.seeds import ANCHOR_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT, SeedCohort

ANCHOR_EXPERIMENT: ExperimentId = ExperimentId.HISTORICAL_DATP_REPRODUCTION
ANCHOR_POPULATION: PopulationId = PopulationId.NBAIOT_NATURAL_DEVICES
ANCHOR_TRAINING_MODEL: TrainingModelId = TrainingModelId.FEDAVG_AUTOENCODER
ANCHOR_METRIC: MetricId = MetricId.FPR_COEFFICIENT_OF_VARIATION
ANCHOR_CHECKPOINT_STATUS: CheckpointStatus = CheckpointStatus.HISTORICAL_ENDPOINT
ANCHOR_EVIDENCE_ROLE: EvidenceRole = EvidenceRole.ANCHOR_REPRODUCTION
ANCHOR_HISTORICAL_SEED_COUNT: SeedCount = HISTORICAL_ANCHOR_SEED_COHORT.member_count
CONFIRMATORY_PAIRED_SEED_COUNT: SeedCount = CONFIRMATORY_SEED_COHORT.member_count
HISTORICAL_ELIGIBLE_CLIENT_COUNT: ClientCount = NBAIOT_NATURAL_DEVICES.client_count

DECLARED_NON_BLOCKING_DISCREPANCY_REASONS: frozenset[AnchorDiscrepancyReason] = frozenset()

_CONFIRMATORY_ONLY_SEEDS: frozenset[Seed] = frozenset(
    Seed(value)
    for value in range(CONFIRMATORY_PAIRED_SEED_COUNT.value)
    if Seed(value) not in HISTORICAL_ANCHOR_SEED_COHORT.values
)


def references_from_protocol(
    protocol: AnchorDecisionProtocol = ANCHOR_DECISION_PROTOCOL,
) -> tuple[AnchorMetricReference, ...]:
    validate_historical_seed_cohort(protocol.seed_cohort)

    def _generate():
        for item in protocol.references:
            if item.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION:
                raise AnchorReproductionError(
                    ErrorMessage("anchor protocol reference metric is not CV(FPR)"),
                    subject=item.metric,
                    reason=AnchorDiscrepancyReason.WRONG_METRIC,
                )
            yield AnchorMetricReference(
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

    return tuple(_generate())


def validate_historical_seed_cohort(seed_cohort: SeedCohort) -> SeedCohort:
    member_count = seed_cohort.member_count
    if member_count == CONFIRMATORY_PAIRED_SEED_COUNT or seed_cohort == CONFIRMATORY_SEED_COHORT:
        raise AnchorReproductionError(
            ErrorMessage("confirmatory ten-seed paired cohort cannot enter anchor reproduction"),
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.CONFIRMATORY_TEN_SEED_COHORT_REJECTED,
        )
    if member_count != ANCHOR_HISTORICAL_SEED_COUNT:
        raise AnchorReproductionError(
            ErrorMessage("anchor reproduction requires exactly the historical five-seed cohort"),
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.WRONG_SEED_SUBSET,
        )

    values = seed_cohort.values
    if len(set(values)) != len(values):
        raise AnchorReproductionError(
            ErrorMessage("anchor seed cohort contains duplicate seeds"),
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.DUPLICATE_SEED,
        )
    if seed_cohort != HISTORICAL_ANCHOR_SEED_COHORT:
        raise AnchorReproductionError(
            ErrorMessage("anchor seed cohort must match the declared historical five-seed cohort"),
            subject=ContractSubject.SEED,
            reason=AnchorDiscrepancyReason.WRONG_SEED_SUBSET,
        )
    return seed_cohort


def independent_reproduction_dependency_blocker() -> AnchorDependencyBlocker:
    return AnchorDependencyBlocker(
        kind=AnchorDependencyKind.FEDERATED_TRAINING_CHECKPOINTING_AND_SCORING,
        detail=AnchorDetail(
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
        artifact_checksum=Checksum.from_file(path),
        model_checkpoint_identity=document.provenance.model_checkpoint_identity,
        evidence_role=ANCHOR_EVIDENCE_ROLE,
    )


def _read_historical_metrics_document(path: Path) -> HistoricalMetricsDocument:
    if not path.is_file():
        raise AnchorReproductionError(
            ErrorMessage("historical metrics artifact is missing"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
        )
    try:
        return HistoricalMetricsDocument.model_validate(loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError, TypeError) as error:
        raise AnchorReproductionError(
            ErrorMessage("historical metrics artifact failed schema validation"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.STALE_OR_MISMATCHED_ARTIFACT,
        ) from error


def _validate_historical_document(
    document: HistoricalMetricsDocument,
    source: HistoricalMetricArtifactSource,
) -> None:
    if document.seed != source.seed:
        raise AnchorReproductionError(
            ErrorMessage("historical metrics seed does not match the artifact coordinate"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_SEED_SUBSET,
        )
    if document.dataset is not HistoricalDatasetToken.NBAIOT:
        raise AnchorReproductionError(
            ErrorMessage("historical metrics artifact is not N-BaIoT"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_POPULATION,
        )
    if document.regime is not HistoricalRegimeToken.PHYSICAL_DEVICE_ANCHOR:
        raise AnchorReproductionError(
            ErrorMessage("historical metrics artifact is not the physical-device anchor regime"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.STALE_OR_MISMATCHED_ARTIFACT,
        )
    if document.client_count != HISTORICAL_ELIGIBLE_CLIENT_COUNT:
        raise AnchorReproductionError(
            ErrorMessage("historical metrics artifact client count is not the locked nine-device population"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_POPULATION,
        )
    if document.eligible_count != HISTORICAL_ELIGIBLE_CLIENT_COUNT:
        raise AnchorReproductionError(
            ErrorMessage("historical metrics artifact eligible count is not the locked nine-device population"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_POPULATION,
        )
    if document.threshold_scope.to_threshold_method() is not source.threshold_method:
        raise AnchorReproductionError(
            ErrorMessage("historical threshold scope does not match the artifact coordinate"),
            subject=ContractSubject.ARTIFACT_PATH,
            reason=AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD,
        )


def load_historical_observations(
    sources: tuple[HistoricalMetricArtifactSource, ...],
) -> tuple[AnchorObservedMetric, ...]:
    if not sources:
        raise AnchorReproductionError(
            ErrorMessage("historical observation sources are required"),
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
        )

    coordinates = tuple((source.seed, source.threshold_method) for source in sources)
    if len(set(coordinates)) != len(coordinates):
        raise AnchorReproductionError(
            ErrorMessage("duplicate historical observation coordinates"),
            reason=AnchorDiscrepancyReason.DUPLICATE_SEED,
        )

    return tuple(load_historical_observation(source) for source in sources)


def historical_sources_for_seed_directories(
    shared_root: Path,
    local_root: Path,
    seed_cohort: SeedCohort = HISTORICAL_ANCHOR_SEED_COHORT,
) -> tuple[HistoricalMetricArtifactSource, ...]:
    """Build typed sources from descriptive shared/local result directories."""
    validate_historical_seed_cohort(seed_cohort)

    def _generate():
        for seed in seed_cohort.values:
            seed_directory = f"{AnchorSeedDirectoryPrefix.SEED.value}{seed.value}"
            yield HistoricalMetricArtifactSource(
                path=shared_root / seed_directory / AnchorArtifactFileName.METRICS.value,
                seed=seed,
                threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
            )
            yield HistoricalMetricArtifactSource(
                path=local_root / seed_directory / AnchorArtifactFileName.METRICS.value,
                seed=seed,
                threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            )

    return tuple(_generate())


def reproduce_anchor(
    *,
    protocol: AnchorDecisionProtocol = ANCHOR_DECISION_PROTOCOL,
    observations: tuple[AnchorObservedMetric, ...] | None = None,
    dependency_blocker: AnchorDependencyBlocker | None = None,
) -> AnchorReproductionResult:
    """Compare protocol references to observations for the historical five-seed cohort."""
    seed_cohort = validate_historical_seed_cohort(protocol.seed_cohort)
    references = references_from_protocol(protocol)
    resolved_observations = observations or ()

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

    bca_comparison = _anchor_bca_comparison(resolved_observations, seed_cohort)

    discrepancies = _collect_discrepancies(comparisons, seed_subset, bca_comparison, dependency_blocker)

    return AnchorReproductionResult(
        experiment=ANCHOR_EXPERIMENT,
        evidence_role=ANCHOR_EVIDENCE_ROLE,
        seed_cohort=seed_cohort,
        references=references,
        observations=resolved_observations,
        seed_subset_comparison=seed_subset,
        metric_comparisons=comparisons,
        bca_comparison=bca_comparison,
        discrepancies=discrepancies,
        dependency_blocker=dependency_blocker,
    )


def _compare_seed_subsets(
    seed_cohort: SeedCohort,
    observations: tuple[AnchorObservedMetric, ...],
) -> AnchorSeedSubsetComparison:
    expected = seed_cohort.values
    if not observations:
        return AnchorSeedSubsetComparison(
            expected_seeds=expected,
            observed_seeds=(),
            decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
        )

    observed = tuple(sorted({item.seed for item in observations}, key=lambda seed: seed.value))

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
            ErrorMessage("confirmatory ten-seed cohort cannot supply anchor observations"),
            reason=AnchorDiscrepancyReason.CONFIRMATORY_TEN_SEED_COHORT_REJECTED,
        )
    if seeds & _CONFIRMATORY_ONLY_SEEDS:
        raise AnchorReproductionError(
            ErrorMessage("observations include confirmatory-only seeds outside the historical five-seed cohort"),
            reason=AnchorDiscrepancyReason.CONFIRMATORY_TEN_SEED_COHORT_REJECTED,
        )


def _reject_non_historical_checkpoint(observations: tuple[AnchorObservedMetric, ...]) -> None:
    """Reject non-historical checkpoint candidates as a cohort-level structural failure."""
    if any(item.checkpoint_status is not ANCHOR_CHECKPOINT_STATUS for item in observations):
        raise AnchorReproductionError(
            ErrorMessage("non-historical checkpoint selection cannot enter historical anchor reproduction"),
            subject=ANCHOR_CHECKPOINT_STATUS,
            reason=AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS,
        )


def _collect_discrepancies(
    comparisons: tuple[AnchorMetricComparison, ...],
    seed_subset: AnchorSeedSubsetComparison,
    bca_comparison: AnchorBcaComparison,
    dependency_blocker: AnchorDependencyBlocker | None,
) -> tuple[AnchorDiscrepancy, ...]:
    def _generate():
        if seed_subset.decision is not AnchorComparisonDecision.EQUIVALENT:
            yield AnchorDiscrepancy.from_seed_subset(seed_subset)
        for comparison in comparisons:
            if comparison.decision is not AnchorComparisonDecision.EQUIVALENT:
                yield AnchorDiscrepancy.from_comparison(comparison)
        if bca_comparison.decision is not AnchorComparisonDecision.EQUIVALENT:
            yield AnchorDiscrepancy.from_bca_comparison(bca_comparison)
        if dependency_blocker is not None:
            yield AnchorDiscrepancy.from_dependency_blocker(dependency_blocker)

    return tuple(_generate())


def _anchor_bca_comparison(
    observations: tuple[AnchorObservedMetric, ...],
    seed_cohort: SeedCohort,
) -> AnchorBcaComparison:
    """Reproduced shared-minus-local CV(FPR) BCa interval over the historical five-seed cohort."""
    shared = {
        item.seed: item.value
        for item in observations
        if item.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD
    }
    local = {
        item.seed: item.value
        for item in observations
        if item.threshold_method is FederatedThresholdMethod.LOCAL_THRESHOLD
    }
    expected_seeds = frozenset(seed_cohort.values)
    if frozenset(shared) != expected_seeds or frozenset(local) != expected_seeds:
        interval = BootstrapInterval.blocked(
            protocol=ANCHOR_INFERENCE_PROTOCOL,
            analysis_seed=ANCHOR_ANALYSIS_SEED,
            point_estimate=None,
            reason=BcaReason.SEED_COHORT_MISMATCH,
        )
    else:
        deltas = tuple(MetricValue(shared[seed].value - local[seed].value) for seed in seed_cohort.values)
        interval = seed_level_bca_interval(
            deltas,
            protocol=ANCHOR_INFERENCE_PROTOCOL,
            analysis_seed=ANCHOR_ANALYSIS_SEED,
        )
    return _classify_bca_comparison(interval)


def _classify_bca_comparison(interval: BootstrapInterval) -> AnchorBcaComparison:
    if interval.outcome is not BcaOutcome.AVAILABLE or interval.lower_bound is None or interval.upper_bound is None:
        return AnchorBcaComparison(
            interval=interval,
            reference_interval=ANCHOR_REFERENCE_INTERVAL,
            maximum_operative_width=ANCHOR_MAXIMUM_OPERATIVE_WIDTH,
            decision=AnchorComparisonDecision.UNAVAILABLE,
            reason=AnchorDiscrepancyReason.BCA_INTERVAL_UNAVAILABLE,
        )

    lower = interval.lower_bound.value
    upper = interval.upper_bound.value
    reference = ANCHOR_REFERENCE_INTERVAL
    if lower <= 0.0:
        reason = AnchorDiscrepancyReason.BCA_INTERVAL_NOT_ENTIRELY_POSITIVE
    elif lower > reference.upper.value or upper < reference.lower.value:
        reason = AnchorDiscrepancyReason.BCA_INTERVAL_DOES_NOT_OVERLAP_REFERENCE
    elif (upper - lower) > ANCHOR_MAXIMUM_OPERATIVE_WIDTH.value:
        reason = AnchorDiscrepancyReason.BCA_INTERVAL_WIDTH_EXCEEDS_MAXIMUM
    else:
        reason = None

    decision = AnchorComparisonDecision.EQUIVALENT if reason is None else AnchorComparisonDecision.MATERIAL_DISCREPANCY
    return AnchorBcaComparison(
        interval=interval,
        reference_interval=reference,
        maximum_operative_width=ANCHOR_MAXIMUM_OPERATIVE_WIDTH,
        decision=decision,
        reason=reason,
    )
