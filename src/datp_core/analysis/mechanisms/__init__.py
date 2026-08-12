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
    AssociationStatistics,
    LeaveOneOutAssociationDiagnostics,
    RegressionSlopeConfidenceInterval,
    heterogeneity_benefit_association,
)
from datp_core.analysis.mechanisms.client_impact import (
    ClientImpactCampaignSummary,
    ClientImpactDeviceFrequency,
    ClientImpactFraction,
    ClientImpactFractionSummary,
    ClientImpactMagnitudeSummary,
    ClientImpactSeedSummary,
    ParetoClientImpact,
    ParetoClientImpactFractions,
    summarize_client_impact,
    summarize_client_impact_campaign,
)
from datp_core.analysis.mechanisms.clustering import (
    ClusterContingencyMatrix,
    ClusterContingencyRow,
    ClusterEvidenceAvailability,
    ClusterEvidenceRecord,
    ClusterStabilityResult,
    RecoveryAssessment,
    cluster_evidence_from_grouped_result,
    cluster_stability,
    empty_cluster_evidence_record,
    local_threshold_dispersion,
)
from datp_core.analysis.mechanisms.dispersion import (
    GroupDispersionObservation,
    GroupDispersionSummary,
    GroupedDispersionResult,
    grouped_dispersion,
)
from datp_core.analysis.mechanisms.divergence import (
    ClientScoreVector,
    DivergenceBlocker,
    DivergenceResult,
    PairwiseJensenShannonDistance,
    blocked_jensen_shannon_divergence,
    jensen_shannon_divergence,
)
from datp_core.analysis.mechanisms.equity_utility import (
    ConfirmatoryEquityUtilityBundle,
    ConfirmatoryEquityUtilityMeasure,
    EquityUtilityMeasureSummary,
    EquityUtilitySeedObservation,
    confirmatory_equity_utility_bundle,
)
from datp_core.analysis.mechanisms.family_recall import (
    FamilyRecallDifference,
    FamilyRecallPolicyComparison,
    FamilyRecallPolicyEvidence,
    compare_family_recall_policies,
)
from datp_core.analysis.mechanisms.model_alignment import (
    AlignmentActivationLabel,
    AlignmentActivationSummary,
    AlignmentReductionOutcome,
    AlignmentReductionUnavailableReason,
    FedAvgAlignmentGrid,
    MeanAlignmentReduction,
    ModelAlignmentClientScores,
    ModelAlignmentCondition,
    ModelAlignmentMetric,
    ModelAlignmentMetricOutcome,
    ModelAlignmentResult,
    ModelAlignmentUnavailableReason,
    alignment_reductions,
    fedavg_alignment_grid,
    model_alignment,
    summarize_alignment_activation,
)
from datp_core.analysis.mechanisms.movement import (
    ThresholdMethodComparison,
    ThresholdMovement,
    ThresholdMovementCohort,
    ThresholdMovementMultiSeedUncertainty,
    ThresholdMovementSeedSummary,
    ThresholdOperatingPoint,
    summarize_threshold_movements,
    summarize_threshold_movements_across_seeds,
    threshold_movement,
)
from datp_core.analysis.mechanisms.support_burden import (
    CalibrationSupportBurdenCampaignSummary,
    CalibrationSupportBurdenClient,
    CalibrationSupportBurdenDeviceReport,
    CalibrationSupportBurdenDeviceSummary,
    CalibrationSupportBurdenSeedEvidence,
    SupportAssociationAvailability,
    SupportCorrelationDirectionSummary,
    calibration_support_burden_evidence,
    summarize_calibration_support_burden,
    summarize_calibration_support_burden_devices,
)
from datp_core.analysis.mechanisms.support_strata import (
    CalibrationSupportStratum,
    CampaignFixedSupportStrata,
    CampaignFixedSupportStratum,
    SupportStratumCampaignSummary,
    SupportStratumCrossSeedMetricSummary,
    SupportStratumCrossSeedSummary,
    SupportStratumOutcomeReport,
    SupportStratumSeedOutcome,
    campaign_fixed_support_strata,
    summarize_support_stratum_campaign,
    support_stratum_seed_outcomes,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
from datp_core.analysis.scientific_decision import ScientificDecisionResult
from datp_core.core.identifiers import ExperimentId, MetricId
from datp_core.core.numeric import Ratio

type MechanismEvidence = (
    AbsorptionCohortResult
    | AssociationResult
    | ClusterEvidenceRecord
    | ClusterStabilityResult
    | ClientImpactCampaignSummary
    | ClientImpactSeedSummary
    | DivergenceResult
    | ConfirmatoryEquityUtilityBundle
    | FamilyRecallPolicyComparison
    | GroupedDispersionResult
    | ModelAlignmentResult
    | ScientificDecisionResult
    | ThresholdMovement
    | ThresholdMovementCohort
    | ThresholdMovementMultiSeedUncertainty
    | CampaignFixedSupportStrata
    | SupportStratumOutcomeReport
    | SupportStratumCampaignSummary
    | CalibrationSupportBurdenSeedEvidence
    | CalibrationSupportBurdenCampaignSummary
    | CalibrationSupportBurdenDeviceReport
)

__all__ = (
    "AbsorptionCohortResult",
    "AbsorptionCornerEvidence",
    "AbsorptionFourCornerEvidence",
    "AbsorptionSeedObservation",
    "AssociationObservation",
    "AssociationResult",
    "AssociationStatistics",
    "AlignmentReductionOutcome",
    "AlignmentReductionUnavailableReason",
    "AlignmentActivationLabel",
    "AlignmentActivationSummary",
    "ClientScoreVector",
    "ClientImpactCampaignSummary",
    "ClientImpactDeviceFrequency",
    "ClientImpactFraction",
    "ClientImpactFractionSummary",
    "ClientImpactMagnitudeSummary",
    "ClientImpactSeedSummary",
    "ClusterEvidenceAvailability",
    "ClusterEvidenceRecord",
    "ClusterContingencyMatrix",
    "ClusterContingencyRow",
    "ClusterStabilityResult",
    "CalibrationSupportStratum",
    "CalibrationSupportBurdenClient",
    "CalibrationSupportBurdenSeedEvidence",
    "CalibrationSupportBurdenCampaignSummary",
    "CalibrationSupportBurdenDeviceReport",
    "CalibrationSupportBurdenDeviceSummary",
    "CampaignFixedSupportStrata",
    "CampaignFixedSupportStratum",
    "SupportStratumOutcomeReport",
    "SupportStratumCampaignSummary",
    "SupportStratumCrossSeedMetricSummary",
    "SupportStratumCrossSeedSummary",
    "SupportStratumSeedOutcome",
    "SupportAssociationAvailability",
    "SupportCorrelationDirectionSummary",
    "ConfirmatoryEquityUtilityBundle",
    "ConfirmatoryEquityUtilityMeasure",
    "FamilyRecallDifference",
    "FamilyRecallPolicyComparison",
    "FamilyRecallPolicyEvidence",
    "DivergenceBlocker",
    "DivergenceResult",
    "EquityUtilityMeasureSummary",
    "EquityUtilitySeedObservation",
    "LeaveOneOutAssociationDiagnostics",
    "PairwiseJensenShannonDistance",
    "ParetoClientImpact",
    "ParetoClientImpactFractions",
    "RegressionSlopeConfidenceInterval",
    "RecoveryAssessment",
    "GroupDispersionObservation",
    "GroupDispersionSummary",
    "GroupedDispersionResult",
    "MechanismEvidence",
    "MeanAlignmentReduction",
    "FedAvgAlignmentGrid",
    "ModelAlignmentClientScores",
    "ModelAlignmentCondition",
    "ModelAlignmentMetric",
    "ModelAlignmentMetricOutcome",
    "ModelAlignmentResult",
    "ModelAlignmentUnavailableReason",
    "ThresholdMovement",
    "ThresholdMovementCohort",
    "ThresholdMovementMultiSeedUncertainty",
    "ThresholdMovementSeedSummary",
    "ThresholdMethodComparison",
    "ThresholdOperatingPoint",
    "blocked_jensen_shannon_divergence",
    "calibration_support_burden_evidence",
    "campaign_fixed_support_strata",
    "alignment_reductions",
    "cluster_evidence_from_grouped_result",
    "cluster_stability",
    "confirmatory_equity_utility_bundle",
    "compare_family_recall_policies",
    "decide_absorption_cohort",
    "decide_model_absorption",
    "empty_cluster_evidence_record",
    "fedavg_alignment_grid",
    "grouped_dispersion",
    "heterogeneity_benefit_association",
    "jensen_shannon_divergence",
    "jensen_shannon_from_client_scores",
    "local_threshold_dispersion",
    "model_alignment",
    "summarize_alignment_activation",
    "summarize_client_impact",
    "summarize_client_impact_campaign",
    "summarize_threshold_movements",
    "summarize_threshold_movements_across_seeds",
    "summarize_support_stratum_campaign",
    "summarize_calibration_support_burden",
    "summarize_calibration_support_burden_devices",
    "support_stratum_seed_outcomes",
    "threshold_movement",
    "threshold_movements_from_evaluations",
)


def threshold_movements_from_evaluations(
    *,
    shared: FederatedEvaluationDocument,
    local: FederatedEvaluationDocument,
    experiment: ExperimentId,
) -> ThresholdMovementCohort:

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
            raise ValueError(
                f"threshold movement requires available FPR for client {shared_client.client.client_id.value}"
            )
        shared_tpr = metric_by_id(shared_client.metrics, MetricId.TRUE_POSITIVE_RATE)
        local_tpr = metric_by_id(local_client.metrics, MetricId.TRUE_POSITIVE_RATE)
        shared_balanced_accuracy = metric_by_id(shared_client.metrics, MetricId.BALANCED_ACCURACY)
        local_balanced_accuracy = metric_by_id(local_client.metrics, MetricId.BALANCED_ACCURACY)
        shared_macro_f1 = metric_by_id(shared_client.metrics, MetricId.BINARY_MACRO_F1)
        local_macro_f1 = metric_by_id(local_client.metrics, MetricId.BINARY_MACRO_F1)
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
        balanced_accuracy_shared = (
            Ratio(shared_balanced_accuracy.value.value)
            if shared_balanced_accuracy.status is MetricStatus.AVAILABLE and shared_balanced_accuracy.value is not None
            else None
        )
        balanced_accuracy_local = (
            Ratio(local_balanced_accuracy.value.value)
            if local_balanced_accuracy.status is MetricStatus.AVAILABLE and local_balanced_accuracy.value is not None
            else None
        )
        if (balanced_accuracy_shared is None) != (balanced_accuracy_local is None):
            balanced_accuracy_shared = None
            balanced_accuracy_local = None
        macro_f1_shared = (
            Ratio(shared_macro_f1.value.value)
            if shared_macro_f1.status is MetricStatus.AVAILABLE and shared_macro_f1.value is not None
            else None
        )
        macro_f1_local = (
            Ratio(local_macro_f1.value.value)
            if local_macro_f1.status is MetricStatus.AVAILABLE and local_macro_f1.value is not None
            else None
        )
        if (macro_f1_shared is None) != (macro_f1_local is None):
            macro_f1_shared = None
            macro_f1_local = None
        movements.append(
            threshold_movement(
                client=shared_client.client,
                shared=ThresholdOperatingPoint(
                    threshold=shared_client.threshold,
                    fpr=Ratio(shared_fpr.value.value),
                    tpr=tpr_shared,
                    balanced_accuracy=balanced_accuracy_shared,
                    macro_f1=macro_f1_shared,
                ),
                local=ThresholdOperatingPoint(
                    threshold=local_client.threshold,
                    fpr=Ratio(local_fpr.value.value),
                    tpr=tpr_local,
                    balanced_accuracy=balanced_accuracy_local,
                    macro_f1=macro_f1_local,
                ),
                experiment=experiment,
                coordinate=shared.score_coordinate,
            )
        )
    return summarize_threshold_movements(tuple(movements))


def jensen_shannon_from_client_scores(
    vectors: tuple[ClientScoreVector, ...],
) -> DivergenceResult:
    return jensen_shannon_divergence(vectors)
