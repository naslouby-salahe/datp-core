"""Mechanism-specific analysis contracts and algorithms."""

from datp_core.analysis.mechanisms.absorption import (
    AbsorptionCohortResult,
    AbsorptionCornerEvidence,
    AbsorptionFourCornerEvidence,
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
    ClusterEvidenceAvailability,
    ClusterEvidenceRecord,
    ClusterStabilityResult,
    cluster_evidence_from_grouped_result,
    cluster_stability,
    empty_cluster_evidence_record,
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
    ThresholdMovementMultiSeedUncertainty,
    ThresholdMovementSeedSummary,
    ThresholdOperatingPoint,
    summarize_threshold_movements,
    summarize_threshold_movements_across_seeds,
    threshold_movement,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.analysis.scientific_decision import ScientificDecisionResult
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import ExperimentId, MetricId
from datp_core.core.numeric import Ratio

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
    | ThresholdMovementMultiSeedUncertainty
)

__all__ = (
    "AbsorptionCohortResult",
    "AbsorptionCornerEvidence",
    "AbsorptionFourCornerEvidence",
    "AbsorptionSeedObservation",
    "AssociationObservation",
    "AssociationResult",
    "ClientScoreVector",
    "ClusterEvidenceAvailability",
    "ClusterEvidenceRecord",
    "ClusterStabilityResult",
    "DivergenceBlocker",
    "DivergenceResult",
    "GroupDispersionObservation",
    "GroupedDispersionResult",
    "MechanismEvidence",
    "ThresholdMovement",
    "ThresholdMovementCohort",
    "ThresholdMovementMultiSeedUncertainty",
    "ThresholdMovementSeedSummary",
    "ThresholdOperatingPoint",
    "blocked_jensen_shannon_divergence",
    "cluster_evidence_from_grouped_result",
    "cluster_stability",
    "decide_absorption_cohort",
    "decide_model_absorption",
    "empty_cluster_evidence_record",
    "grouped_dispersion",
    "heterogeneity_benefit_association",
    "jensen_shannon_divergence",
    "jensen_shannon_from_client_scores",
    "local_threshold_dispersion",
    "summarize_threshold_movements",
    "summarize_threshold_movements_across_seeds",
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
    shared_clients = {item.client for item in shared.clients}
    local_clients = {item.client for item in local.clients}
    if shared_clients != local_clients:
        raise ValueError("threshold movement requires identical client inventories on paired evaluations")
    local_by_client = {item.client: item for item in local.clients}
    movements: list[ThresholdMovement] = []
    for shared_client in sorted(shared.clients, key=lambda item: item.client):
        local_client = local_by_client[shared_client.client]
        shared_fpr = metric_by_id(shared_client.metrics, MetricId.FALSE_POSITIVE_RATE)
        local_fpr = metric_by_id(local_client.metrics, MetricId.FALSE_POSITIVE_RATE)
        if (
            shared_fpr.status is not MetricStatus.AVAILABLE
            or local_fpr.status is not MetricStatus.AVAILABLE
            or shared_fpr.value is None
            or local_fpr.value is None
        ):
            raise ValueError(f"threshold movement requires available FPR for client {shared_client.client.client_id}")
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


def jensen_shannon_from_client_scores(
    vectors: tuple[ClientScoreVector, ...],
    *,
    source_score_checksum: Checksum,
) -> DivergenceResult:
    return jensen_shannon_divergence(vectors, source_score_checksum=source_score_checksum)
