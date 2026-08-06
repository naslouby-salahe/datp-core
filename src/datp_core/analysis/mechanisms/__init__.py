"""Mechanism-specific analysis contracts and algorithms."""

from datp_core.analysis.mechanisms.absorption import (
    AbsorptionCohortResult,
    AbsorptionSeedObservation,
    decide_absorption_cohort,
    decide_model_absorption,
)
from datp_core.analysis.mechanisms.association import (
    AssociationObservation,
    AssociationResult,
    heterogeneity_benefit_association,
)
from datp_core.analysis.mechanisms.clustering import (
    ClusterEvidenceRecord,
    ClusterStabilityResult,
    cluster_evidence_from_grouped_result,
    cluster_stability,
    local_threshold_dispersion,
)
from datp_core.analysis.mechanisms.dispersion import (
    GroupDispersionObservation,
    GroupedDispersionResult,
    grouped_dispersion,
)
from datp_core.analysis.mechanisms.divergence import (
    ClientScoreVector,
    DivergenceBlocker,
    DivergenceResult,
    blocked_jensen_shannon_divergence,
    jensen_shannon_divergence,
)
from datp_core.analysis.mechanisms.movement import (
    ThresholdMovement,
    ThresholdMovementCohort,
    ThresholdOperatingPoint,
    summarize_threshold_movements,
    threshold_movement,
)
from datp_core.analysis.scientific_decision import ScientificDecisionResult
from datp_core.domain.enums import ExperimentId, MetricId
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import ClusterIndex
from datp_core.domain.values.ratios import MetricValue, Ratio
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.thresholding.methods.cluster import GroupedThresholdResult

type MechanismEvidence = (
    AbsorptionCohortResult
    | AssociationResult
    | ClusterEvidenceRecord
    | ClusterStabilityResult
    | DivergenceResult
    | GroupedDispersionResult
    | ScientificDecisionResult
    | ThresholdMovement
    | ThresholdMovementCohort
)

__all__ = (
    "AbsorptionCohortResult",
    "AbsorptionSeedObservation",
    "AssociationObservation",
    "AssociationResult",
    "ClientScoreVector",
    "ClusterEvidenceRecord",
    "ClusterStabilityResult",
    "DivergenceBlocker",
    "DivergenceResult",
    "GroupDispersionObservation",
    "GroupedDispersionResult",
    "MechanismEvidence",
    "ThresholdMovement",
    "ThresholdMovementCohort",
    "ThresholdOperatingPoint",
    "blocked_jensen_shannon_divergence",
    "cluster_evidence_from_grouped_result",
    "cluster_mechanism_bundle",
    "cluster_stability",
    "decide_absorption_cohort",
    "decide_model_absorption",
    "grouped_dispersion",
    "heterogeneity_association_from_observations",
    "heterogeneity_benefit_association",
    "jensen_shannon_divergence",
    "jensen_shannon_from_client_scores",
    "local_threshold_dispersion",
    "summarize_threshold_movements",
    "threshold_movement",
    "threshold_movements_from_evaluations",
)


def threshold_movements_from_evaluations(
    *,
    shared: FederatedEvaluationDocument,
    local: FederatedEvaluationDocument,
    experiment: ExperimentId,
) -> ThresholdMovementCohort:
    """Build per-client threshold/operating-point movement evidence from paired evaluation documents."""
    local_by_client = {item.client: item for item in local.clients}
    movements: list[ThresholdMovement] = []
    for shared_client in shared.clients:
        local_client = local_by_client.get(shared_client.client)
        if local_client is None:
            continue
        shared_fpr = metric_by_id(shared_client.metrics, MetricId.FALSE_POSITIVE_RATE)
        local_fpr = metric_by_id(local_client.metrics, MetricId.FALSE_POSITIVE_RATE)
        if (
            shared_fpr.status is not MetricStatus.AVAILABLE
            or local_fpr.status is not MetricStatus.AVAILABLE
            or shared_fpr.value is None
            or local_fpr.value is None
        ):
            continue
        shared_tpr = metric_by_id(shared_client.metrics, MetricId.TRUE_POSITIVE_RATE)
        local_tpr = metric_by_id(local_client.metrics, MetricId.TRUE_POSITIVE_RATE)
        tpr_shared = (
            Ratio(shared_tpr.value.value)
            if shared_tpr.status is MetricStatus.AVAILABLE and shared_tpr.value is not None
            else None
        )
        tpr_local = (
            Ratio(local_tpr.value.value)
            if local_tpr.status is MetricStatus.AVAILABLE and local_tpr.value is not None
            else None
        )
        if (tpr_shared is None) != (tpr_local is None):
            tpr_shared = None
            tpr_local = None
        movements.append(
            threshold_movement(
                client=shared_client.client,
                shared=ThresholdOperatingPoint(
                    threshold=shared_client.threshold,
                    fpr=Ratio(shared_fpr.value.value),
                    tpr=tpr_shared,
                ),
                local=ThresholdOperatingPoint(
                    threshold=local_client.threshold,
                    fpr=Ratio(local_fpr.value.value),
                    tpr=tpr_local,
                ),
                experiment=experiment,
                coordinate=shared.score_coordinate,
                score_checksum=shared.fixed_score_evidence.evaluation.score_checksum,
                evaluation_checksum=shared.fixed_score_evidence.evaluation.label_checksum,
            )
        )
    return summarize_threshold_movements(tuple(movements))


def cluster_mechanism_bundle(
    *,
    left: GroupedThresholdResult,
    right: GroupedThresholdResult,
    left_checksum: Checksum,
    right_checksum: Checksum,
    local_dispersion: MetricValue | None,
    group_false_positive_rates: tuple[tuple[Ratio, ...], ...] | None = None,
) -> tuple[ClusterEvidenceRecord, ClusterStabilityResult, GroupedDispersionResult]:
    """Assemble cluster evidence, stability, and optional grouped dispersion from persisted results."""
    evidence = cluster_evidence_from_grouped_result(
        left,
        source_threshold_checksum=left_checksum,
        local_dispersion=local_dispersion,
    )
    stability = cluster_stability(
        left.clusters,
        right.clusters,
        left_source_checksum=left_checksum,
        right_source_checksum=right_checksum,
        left_declared_group_count=left.group_count.value,
        right_declared_group_count=right.group_count.value,
    )
    if group_false_positive_rates is None or len(group_false_positive_rates) != len(left.clusters):
        dispersion = grouped_dispersion(())
    else:
        observations = tuple(
            GroupDispersionObservation(
                group_index=ClusterIndex(index),
                thresholds=tuple(item.value for item in membership.contributing_local_quantiles),
                false_positive_rates=group_false_positive_rates[index],
            )
            for index, membership in enumerate(left.clusters)
            if membership.contributing_local_quantiles and group_false_positive_rates[index]
        )
        dispersion = grouped_dispersion(observations)
    return evidence, stability, dispersion


def heterogeneity_association_from_observations(
    observations: tuple[AssociationObservation, ...],
) -> AssociationResult:
    return heterogeneity_benefit_association(observations)


def jensen_shannon_from_client_scores(
    vectors: tuple[ClientScoreVector, ...],
    *,
    source_score_checksum: Checksum,
) -> DivergenceResult:
    return jensen_shannon_divergence(vectors, source_score_checksum=source_score_checksum)
