from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.analysis.contrasts import (
    CONFIRMATORY_RELATIVE_CV_REDUCTION_CUTOFF,
    ConfirmatoryDescriptiveEffect,
    ConfirmatoryDescriptiveEffects,
    PairedContrast,
    PairedContrasts,
    build_paired_contrast,
)
from datp_core.analysis.descriptive import (
    ClientEvaluationScoreSeries,
    ScoreGeometryResult,
    ScoreGeometryThresholdOverlay,
    score_geometry_from_client_vectors,
)
from datp_core.analysis.evidence import AnalyzeConfirmatoryEvidenceRequest, analyze_confirmatory_evidence
from datp_core.analysis.influence import leave_one_device_out_effects, summarize_leave_one_device_out_effects
from datp_core.analysis.mechanisms import (
    AbsorptionCornerEvidence,
    AssociationObservation,
    CalibrationSupportBurdenCampaignSummary,
    CalibrationSupportBurdenDeviceReport,
    CalibrationSupportBurdenSeedEvidence,
    CampaignFixedSupportStrata,
    ClientImpactCampaignSummary,
    ClientScoreVector,
    EquityUtilityParetoView,
    FamilyRecallPolicyCampaignSummary,
    FamilyRecallPolicyComparison,
    GroupDispersionObservation,
    GroupedDispersionResult,
    MechanismEvidence,
    SupportStratumCampaignSummary,
    SupportStratumOutcomeReport,
    ThresholdMovementCohort,
    calibration_support_burden_evidence,
    campaign_fixed_support_strata,
    compare_family_recall_policies,
    confirmatory_equity_utility_bundle,
    equity_utility_pareto,
    family_explanatory_adequacy,
    grouped_cv_fpr_recovery,
    grouped_dispersion,
    heterogeneity_benefit_association,
    jensen_shannon_from_client_scores,
    summarize_calibration_support_burden,
    summarize_calibration_support_burden_devices,
    summarize_client_impact,
    summarize_client_impact_campaign,
    summarize_family_recall_campaign,
    summarize_support_stratum_campaign,
    summarize_threshold_movements_across_seeds,
    support_stratum_seed_outcomes,
    threshold_movements_from_evaluations,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import ClientMetricResult, MetricStatus, metric_by_id
from datp_core.app.planning import PlanReason, expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    AnalysisReasonText,
    ClientIdentityToken,
    EvidenceRole,
    ExperimentId,
    FamilyIdentity,
    FederatedThresholdMethod,
    FigureTitle,
    MetricId,
    PopulationId,
    RegimeLabel,
    ScoreFrameColumn,
    TrainingModelId,
)
from datp_core.core.numeric import MetricValue, ModelCoefficientValue, Ratio, Seed, SeedObservationCount
from datp_core.data.nbaiot.schema import NBaIoTDevice, device_family
from datp_core.data.populations.contracts import ClientIdentity, FamilyAssignment
from datp_core.detector.scoring.models import FederatedScoreAssetName
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.seeds import CONFIRMATORY_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.confirmatory.spec import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document, population_metric
from datp_core.experiments.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    federated_training_directory,
)
from datp_core.experiments.execution.models import ProgressHook
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.presentation.client_impact_tables import (
    export_client_impact_strata_table,
    export_support_burden_table,
)
from datp_core.presentation.export import export_confirmatory_publication, export_mechanism_publication
from datp_core.presentation.figures import (
    FigureSpec,
    causal_intervention_map_figure,
    confirmatory_paired_effect_figure,
    equity_utility_pareto_figure,
    score_geometry_figure,
)
from datp_core.presentation.operational_accounting import export_threshold_stage_accounting
from datp_core.presentation.population_capabilities import export_population_capability_table
from datp_core.presentation.prior_art import export_prior_art_collision_table, export_prior_art_distinction_table
from datp_core.presentation.target_attainment import (
    export_confirmatory_operating_point_table,
    export_target_attainment_table,
)
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.thresholds.policies.cluster import GroupedThresholdResult
from datp_core.thresholds.protocols import ClusterFingerprintFeature


class ConfirmatoryAssetDirectory(StrEnum):
    ROOT = "confirmatory"
    ANALYSIS = "analysis"
    SCORE_GEOMETRY = "score_geometry"
    MECHANISMS = "mechanisms"
    SUPPORTIVE = "supportive"
    PHYSICAL_FAMILY_ADEQUACY = "physical_family_adequacy"
    CALIBRATION_SUPPORT_BURDEN = "calibration_support_burden"
    NATURAL_DEVICE_CLIENT_IMPACT = "natural_device_client_impact"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatorySeedResult:
    training_seed: Seed
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FedAvgCvFprEffectEvidence:
    seed: Seed
    shared: AbsorptionCornerEvidence
    local: AbsorptionCornerEvidence

    def __post_init__(self) -> None:
        if self.shared.seed != self.seed or self.local.seed != self.seed:
            raise ValueError("FedAvg CV(FPR) corners must match the observation seed")
        if self.shared.threshold_method is not FederatedThresholdMethod.SHARED_THRESHOLD:
            raise ValueError("FedAvg shared corner must use SHARED_THRESHOLD")
        if self.local.threshold_method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
            raise ValueError("FedAvg local corner must use LOCAL_THRESHOLD")
        if self.shared.model is not TrainingModelId.FEDAVG_AUTOENCODER:
            raise ValueError("FedAvg shared corner must use FEDAVG_AUTOENCODER")
        if self.local.model is not TrainingModelId.FEDAVG_AUTOENCODER:
            raise ValueError("FedAvg local corner must use FEDAVG_AUTOENCODER")

    @property
    def shared_cv(self) -> MetricValue:
        return self.shared.population_cv_fpr

    @property
    def local_cv(self) -> MetricValue:
        return self.local.population_cv_fpr

    @property
    def effect(self) -> MetricValue:
        return MetricValue(self.shared_cv.value - self.local_cv.value)


def run_confirmatory_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ConfirmatorySeedResult:
    declaration = _confirmatory_declaration()
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=PlanReason("the confirmatory entry point supplies the locked natural-device execution prerequisites"),
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    return ConfirmatorySeedResult(
        training_seed=training_seed,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def run_family_grouped_mechanism_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> ConfirmatorySeedResult:

    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.FAMILY_AND_GROUPED_GRANULARITY)
    if len(matches) != 1:
        raise ScientificContractError(ErrorMessage("family/grouped mechanism experiment must be declared exactly once"))
    declaration = matches[0]
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason=PlanReason(
            "the family/grouped mechanism entry point supplies the locked "
            "natural-device execution prerequisites for family/cluster threshold evidence"
        ),
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    return ConfirmatorySeedResult(
        training_seed=training_seed,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def analyze_confirmatory_campaign() -> Path:
    output = (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
    )
    mechanisms = _confirmatory_mechanisms()
    cluster_mechanisms = _confirmatory_cluster_mechanisms()
    all_mechanisms = mechanisms + cluster_mechanisms
    contrasts = PairedContrasts(values=tuple(_confirmatory_contrast(seed) for seed in CONFIRMATORY_SEED_COHORT.values))
    lodo_effects = tuple(
        effect
        for seed in CONFIRMATORY_SEED_COHORT.values
        for effect in leave_one_device_out_effects(
            shared=load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD)),
            local=load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD)),
        )
    )
    result = analyze_confirmatory_evidence(
        AnalyzeConfirmatoryEvidenceRequest(
            contrasts=contrasts,
            descriptive_effects=_confirmatory_descriptive_effects(),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
            output_directory=output,
            mechanisms=all_mechanisms,
            leave_one_device_out=summarize_leave_one_device_out_effects(
                lodo_effects,
                full_mean_delta=MetricValue(sum(delta.value for delta in contrasts.deltas) / len(contrasts)),
                required_seed_count=len(CONFIRMATORY_SEED_COHORT.values),
            ),
        )
    )
    geometries, figures = build_confirmatory_score_geometry()
    figures = (
        causal_intervention_map_figure(),
        *figures,
        confirmatory_paired_effect_figure(result.document.contrasts, result.document.interval),
    )
    persist_score_geometry(geometries, output / ConfirmatoryAssetDirectory.SCORE_GEOMETRY)
    export_confirmatory_publication(
        result.document,
        output,
        verified_anchor_gate=None,
        figures=figures,
    )
    export_population_capability_table(output / "population_capability_claim_boundary.md")
    export_prior_art_collision_table(output / "prior_art_collision_table.md")
    export_prior_art_distinction_table(output / "prior_art_distinction_table.md")
    pareto_views = _confirmatory_pareto_views()
    export_target_attainment_table(pareto_views[0], output / "calibration_target_attainment.md")
    export_confirmatory_operating_point_table(
        _confirmatory_operating_point_documents(),
        CONFIRMATORY_SEED_COHORT.values,
        output / "confirmatory_operating_point_record.md",
    )
    export_threshold_stage_accounting(
        _confirmatory_threshold_stage_documents(), output / "threshold_stage_accounting.md"
    )
    _export_client_impact_synthesis_tables(all_mechanisms, output)
    mechanism_evidence, supportive_evidence = _partition_confirmatory_descriptive_evidence(all_mechanisms)
    if mechanism_evidence:
        export_mechanism_publication(
            mechanism_evidence,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output / ConfirmatoryAssetDirectory.MECHANISMS,
            evidence_role=EvidenceRole.MECHANISM,
        )
    if supportive_evidence:
        export_mechanism_publication(
            supportive_evidence,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output / ConfirmatoryAssetDirectory.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
        )
    return output


def _partition_confirmatory_descriptive_evidence(
    mechanisms: tuple[MechanismEvidence, ...],
) -> tuple[tuple[MechanismEvidence, ...], tuple[MechanismEvidence, ...]]:
    supportive_types = (FamilyRecallPolicyComparison, FamilyRecallPolicyCampaignSummary, EquityUtilityParetoView)
    supportive = tuple(item for item in mechanisms if isinstance(item, supportive_types))
    mechanism = tuple(item for item in mechanisms if not isinstance(item, supportive_types))
    return mechanism, supportive


def analyze_physical_family_adequacy(*, overwrite: bool) -> Path:
    """Publish the §7.2A analysis from fixed confirmatory score/evaluation evidence."""

    output = (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
        / ConfirmatoryAssetDirectory.PHYSICAL_FAMILY_ADEQUACY
    )
    if overwrite and output.exists():
        from shutil import rmtree

        rmtree(output)
    records: list[MechanismEvidence] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        divergence = jensen_shannon_from_client_scores(_client_score_vectors(shared))
        family_assignments = _natural_device_family_assignments(tuple(item.client for item in local.clients))
        records.append(
            family_explanatory_adequacy(
                seed=seed,
                divergence=divergence,
                family_by_client=family_assignments,
                local_thresholds=tuple(
                    (assignment, next(item.threshold for item in local.clients if item.client == assignment.client))
                    for assignment in family_assignments
                ),
            )
        )
    export_mechanism_publication(
        tuple(records),
        experiment=ExperimentId.PHYSICAL_FAMILY_ADEQUACY,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output,
        evidence_role=EvidenceRole.MECHANISM,
    )
    return output


def analyze_calibration_support_burden(*, overwrite: bool) -> Path:
    """Publish the §7.5A descriptive analysis from paired confirmatory evidence."""

    output = (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
        / ConfirmatoryAssetDirectory.CALIBRATION_SUPPORT_BURDEN
    )
    if overwrite and output.exists():
        from shutil import rmtree

        rmtree(output)
    evidence: list[CalibrationSupportBurdenSeedEvidence] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        movement = threshold_movements_from_evaluations(
            shared=shared,
            local=local,
            experiment=ExperimentId.CALIBRATION_SUPPORT_BURDEN,
        )
        evidence.append(calibration_support_burden_evidence(shared, local, movement))
    records: tuple[MechanismEvidence, ...] = (
        *evidence,
        summarize_calibration_support_burden(tuple(evidence)),
        summarize_calibration_support_burden_devices(tuple(evidence)),
    )
    export_mechanism_publication(
        records,
        experiment=ExperimentId.CALIBRATION_SUPPORT_BURDEN,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output,
        evidence_role=EvidenceRole.MECHANISM,
    )
    return output


def analyze_natural_device_client_impact(*, overwrite: bool) -> Path:
    """Publish the §7.5B client-impact and fixed-support-strata bundle."""

    output = (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
        / ConfirmatoryAssetDirectory.NATURAL_DEVICE_CLIENT_IMPACT
    )
    if overwrite and output.exists():
        from shutil import rmtree

        rmtree(output)
    movements: list[ThresholdMovementCohort] = []
    pairs: list[tuple[FederatedEvaluationDocument, FederatedEvaluationDocument]] = []
    records: list[MechanismEvidence] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        movement = threshold_movements_from_evaluations(
            shared=shared, local=local, experiment=ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT
        )
        pairs.append((shared, local))
        movements.append(movement)
        records.append(summarize_client_impact(movement))
    strata = campaign_fixed_support_strata(tuple(shared for shared, _ in pairs))
    outcomes = support_stratum_seed_outcomes(strata, tuple(pairs), tuple(movements))
    records.extend(
        (
            summarize_client_impact_campaign(tuple(movements)),
            strata,
            outcomes,
            summarize_support_stratum_campaign(outcomes),
        )
    )
    export_mechanism_publication(
        tuple(records),
        experiment=ExperimentId.NATURAL_DEVICE_CLIENT_IMPACT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output,
        evidence_role=EvidenceRole.MECHANISM,
    )
    return output


def _confirmatory_descriptive_effects() -> ConfirmatoryDescriptiveEffects:
    effects: list[ConfirmatoryDescriptiveEffect] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        relative = (
            None
            if shared_cv.value <= CONFIRMATORY_RELATIVE_CV_REDUCTION_CUTOFF.value
            else MetricValue((shared_cv.value - local_cv.value) / shared_cv.value)
        )
        effects.append(
            ConfirmatoryDescriptiveEffect(
                seed=seed,
                shared_cv_fpr=shared_cv,
                local_cv_fpr=local_cv,
                relative_cv_reduction=relative,
                delta_worst_fpr=MetricValue(
                    population_metric(shared, MetricId.WORST_CLIENT_FPR).value
                    - population_metric(local, MetricId.WORST_CLIENT_FPR).value
                ),
                delta_iqr_fpr=MetricValue(
                    population_metric(shared, MetricId.FPR_IQR).value - population_metric(local, MetricId.FPR_IQR).value
                ),
            )
        )
    return ConfirmatoryDescriptiveEffects(values=tuple(effects))


def _export_client_impact_synthesis_tables(mechanisms: tuple[MechanismEvidence, ...], output: Path) -> None:
    support_campaign = next(item for item in mechanisms if isinstance(item, CalibrationSupportBurdenCampaignSummary))
    support_devices = next(item for item in mechanisms if isinstance(item, CalibrationSupportBurdenDeviceReport))
    strata = next(item for item in mechanisms if isinstance(item, CampaignFixedSupportStrata))
    stratum_outcomes = next(item for item in mechanisms if isinstance(item, SupportStratumOutcomeReport))
    stratum_campaign = next(item for item in mechanisms if isinstance(item, SupportStratumCampaignSummary))
    impact = next(item for item in mechanisms if isinstance(item, ClientImpactCampaignSummary))
    export_support_burden_table(support_campaign, support_devices, output / "calibration_support_burden.md")
    export_client_impact_strata_table(
        strata,
        stratum_outcomes,
        stratum_campaign,
        impact,
        output / "natural_device_helped_harmed_strata.md",
    )


def _confirmatory_mechanisms() -> tuple[MechanismEvidence, ...]:
    movement_cohorts: list[ThresholdMovementCohort] = []
    policy_pairs: list[tuple[FederatedEvaluationDocument, FederatedEvaluationDocument]] = []
    support_burden_evidence: list[CalibrationSupportBurdenSeedEvidence] = []
    association_observations: list[AssociationObservation] = []
    mechanisms: list[MechanismEvidence] = []
    family_comparisons: list[FamilyRecallPolicyComparison] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        family = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.FAMILY_THRESHOLD))
        cluster = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.CLUSTER_THRESHOLD))
        policy_pairs.append((shared, local))
        movement = threshold_movements_from_evaluations(
            shared=shared,
            local=local,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        )
        movement_cohorts.append(movement)
        mechanisms.append(movement)
        burden = calibration_support_burden_evidence(shared, local, movement)
        mechanisms.append(burden)
        support_burden_evidence.append(burden)
        mechanisms.append(summarize_client_impact(movement))
        family_comparison = compare_family_recall_policies((shared, local, family, cluster))
        mechanisms.append(family_comparison)
        family_comparisons.append(family_comparison)
        shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        family_cv = population_metric(family, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        mechanisms.append(
            grouped_cv_fpr_recovery(
                seed=seed,
                method=FederatedThresholdMethod.FAMILY_THRESHOLD,
                shared_cv_fpr=shared_cv,
                grouped_cv_fpr=family_cv,
                local_cv_fpr=local_cv,
            )
        )
        benefit = MetricValue(shared_cv.value - local_cv.value)
        vectors = _client_score_vectors(shared)
        divergence = jensen_shannon_from_client_scores(vectors)
        mechanisms.append(divergence)
        family_assignments = _natural_device_family_assignments(tuple(item.client for item in local.clients))
        mechanisms.append(
            family_explanatory_adequacy(
                seed=seed,
                divergence=divergence,
                family_by_client=family_assignments,
                local_thresholds=tuple(
                    (assignment, next(item.threshold for item in local.clients if item.client == assignment.client))
                    for assignment in family_assignments
                ),
            )
        )
        if divergence.aggregate is not None:
            association_observations.append(
                AssociationObservation(
                    seed=seed,
                    experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                    population=PopulationId.NBAIOT_NATURAL_DEVICES,
                    regime_label=RegimeLabel(f"seed_{seed.value}"),
                    heterogeneity=divergence.aggregate,
                    benefit=benefit,
                )
            )
    mechanisms.append(
        summarize_threshold_movements_across_seeds(
            tuple(movement_cohorts),
            required_seed_count=CONFIRMATORY_SEED_COHORT.member_count,
        )
    )
    mechanisms.append(summarize_client_impact_campaign(tuple(movement_cohorts)))
    mechanisms.append(
        summarize_family_recall_campaign(
            tuple(family_comparisons),
            required_seed_count=SeedObservationCount(CONFIRMATORY_SEED_COHORT.member_count.value),
        )
    )
    mechanisms.append(summarize_calibration_support_burden(tuple(support_burden_evidence)))
    mechanisms.append(summarize_calibration_support_burden_devices(tuple(support_burden_evidence)))
    mechanisms.append(confirmatory_equity_utility_bundle(tuple(policy_pairs)))
    mechanisms.extend(_confirmatory_pareto_views())
    strata = campaign_fixed_support_strata(tuple(shared for shared, _ in policy_pairs))
    mechanisms.append(strata)
    stratum_outcomes = support_stratum_seed_outcomes(strata, tuple(policy_pairs), tuple(movement_cohorts))
    mechanisms.append(stratum_outcomes)
    mechanisms.append(summarize_support_stratum_campaign(stratum_outcomes))
    if association_observations:
        mechanisms.append(heterogeneity_benefit_association(tuple(association_observations)))
    return tuple(mechanisms)


def build_confirmatory_score_geometry() -> tuple[tuple[ScoreGeometryResult, ...], tuple[FigureSpec, ...]]:
    geometries: list[ScoreGeometryResult] = []
    figures: list[FigureSpec] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        expected_clients = tuple(sorted(item.client for item in shared.clients))
        if not expected_clients:
            raise ScientificContractError(
                ErrorMessage(f"confirmatory score geometry requires evaluation clients for seed {seed.value}")
            )
        benign_eval = _client_evaluation_scores(
            score_coordinate=shared.score_coordinate,
            document_clients=tuple(item.client for item in shared.clients),
            expected_clients=expected_clients,
            benign_only=True,
        )
        attack_eval = _client_evaluation_scores(
            score_coordinate=shared.score_coordinate,
            document_clients=tuple(item.client for item in shared.clients),
            expected_clients=expected_clients,
            benign_only=False,
        )
        attack_available = any(item.scores for item in attack_eval)
        geometry = score_geometry_from_client_vectors(
            seed=seed,
            benign_evaluation=benign_eval,
            attack_evaluation=attack_eval,
            threshold_overlays=_score_geometry_threshold_overlays(seed, expected_clients),
            attack_geometry_available=attack_available,
            attack_geometry_reason=(
                None if attack_available else AnalysisReasonText("attack evaluation scores unavailable")
            ),
        )
        geometries.append(geometry)
        figures.append(
            score_geometry_figure(
                geometry,
                title=FigureTitle(f"Per-client empirical score CDF (seed {geometry.seed.value})"),
            )
        )
        figures.append(
            score_geometry_figure(
                geometry,
                title=FigureTitle(f"Ennio Doorbell empirical score CDF (seed {geometry.seed.value})"),
                client_id=ClientIdentityToken(NBaIoTDevice.ENNIO_DOORBELL.value),
            )
        )
    for view in _confirmatory_pareto_views():
        figures.append(
            equity_utility_pareto_figure(
                view,
                title=FigureTitle(f"N-BaIoT equity–utility Pareto: CV(FPR) versus {view.utility_metric.value}"),
            )
        )
    return tuple(geometries), tuple(figures)


def _confirmatory_pareto_views() -> tuple[EquityUtilityParetoView, ...]:
    documents = tuple(
        load_evaluation_document(_evaluation_path(seed, method))
        for seed in CONFIRMATORY_SEED_COHORT.values
        for method in (
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
            FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
            FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD,
            FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
            FederatedThresholdMethod.FAMILY_THRESHOLD,
            FederatedThresholdMethod.CLUSTER_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
        )
    )
    fixed_shrinkage_documents = tuple(
        load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE))
        for seed in CONFIRMATORY_SEED_COHORT.values
    )
    return (
        equity_utility_pareto(
            documents,
            utility_metric=MetricId.P10_BINARY_MACRO_F1,
            fixed_shrinkage_documents=fixed_shrinkage_documents,
        ),
        equity_utility_pareto(
            documents,
            utility_metric=MetricId.WORST_CLIENT_BALANCED_ACCURACY,
            fixed_shrinkage_documents=fixed_shrinkage_documents,
        ),
    )


def _confirmatory_operating_point_documents() -> tuple[FederatedEvaluationDocument, ...]:
    return tuple(
        load_evaluation_document(_evaluation_path(seed, method))
        for seed in CONFIRMATORY_SEED_COHORT.values
        for method in (
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        )
    )


def _confirmatory_threshold_stage_documents() -> tuple[FederatedEvaluationDocument, ...]:
    methods = (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
        FederatedThresholdMethod.FAMILY_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE,
        FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE,
    )
    return tuple(
        load_evaluation_document(_evaluation_path(seed, method))
        for seed in CONFIRMATORY_SEED_COHORT.values
        for method in methods
    )


def persist_score_geometry(geometries: tuple[ScoreGeometryResult, ...], output_directory: Path) -> None:
    from datp_core.artifacts.serializers.json import serialize_json_model

    output_directory.mkdir(parents=True, exist_ok=True)
    for geometry in geometries:
        serialize_json_model(geometry, output_directory / f"seed_{geometry.seed.value}.json")


def _score_geometry_threshold_overlays(
    seed: Seed,
    expected_clients: tuple[ClientIdentity, ...],
) -> tuple[ScoreGeometryThresholdOverlay, ...]:
    expected = frozenset(expected_clients)
    overlays: list[ScoreGeometryThresholdOverlay] = []
    for method in (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
    ):
        document = load_evaluation_document(_evaluation_path(seed, method))
        for client_result in sorted(document.clients, key=lambda item: item.client):
            if client_result.client not in expected:
                continue
            overlays.append(
                ScoreGeometryThresholdOverlay(
                    method=method,
                    threshold=MetricValue(client_result.threshold.value),
                    client=client_result.client,
                    benign_exceedance=_client_metric_value(client_result, MetricId.FALSE_POSITIVE_RATE),
                    attack_acceptance=_attack_acceptance(client_result),
                    balanced_accuracy=_client_metric_value(client_result, MetricId.BALANCED_ACCURACY),
                    macro_f1=_client_metric_value(client_result, MetricId.BINARY_MACRO_F1),
                )
            )
    required = frozenset(
        (method, client)
        for method in (
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            FederatedThresholdMethod.CLUSTER_THRESHOLD,
        )
        for client in expected_clients
    )
    observed = frozenset((item.method, item.client) for item in overlays)
    if observed != required:
        missing = sorted(f"{method.value}:{client.client_id.value}" for method, client in required - observed)
        extra = sorted(
            f"{method.value}:{client.client_id.value}" for method, client in observed - required if client is not None
        )
        raise ScientificContractError(
            ErrorMessage(f"score geometry threshold overlays are incomplete missing={missing} extra={extra}")
        )
    return tuple(overlays)


def _client_metric_value(client_result: ClientMetricResult, metric_id: MetricId) -> MetricValue | None:
    metric = metric_by_id(client_result.metrics, metric_id)
    return metric.value


def _attack_acceptance(client_result: ClientMetricResult) -> MetricValue | None:
    true_positive_rate = _client_metric_value(client_result, MetricId.TRUE_POSITIVE_RATE)
    return None if true_positive_rate is None else MetricValue(1.0 - true_positive_rate.value)


def _client_evaluation_scores(
    *,
    score_coordinate: FederatedTrainingCoordinate,
    document_clients: tuple[ClientIdentity, ...],
    expected_clients: tuple[ClientIdentity, ...],
    benign_only: bool,
) -> tuple[ClientEvaluationScoreSeries, ...]:
    from datp_core.data.populations.contracts import PopulationOutcomeLabel

    ordered_document_clients = tuple(sorted(document_clients))
    if frozenset(ordered_document_clients) != frozenset(expected_clients):
        missing = sorted(
            client.client_id.value for client in expected_clients if client not in frozenset(ordered_document_clients)
        )
        extra = sorted(
            client.client_id.value for client in ordered_document_clients if client not in frozenset(expected_clients)
        )
        raise ScientificContractError(
            ErrorMessage(
                "evaluation document clients do not match the expected score-geometry client set"
                f" missing={missing} extra={extra}"
            )
        )
    if len(ordered_document_clients) != len(frozenset(ordered_document_clients)):
        raise ScientificContractError(ErrorMessage("evaluation document clients must be unique for score geometry"))

    score_root = federated_training_directory(score_coordinate, OUTPUTS_ROOT) / ExecutionArtifactDirectory.SCORES
    pairs: list[ClientEvaluationScoreSeries] = []
    benign_label = PopulationOutcomeLabel.BENIGN.value
    for client in expected_clients:
        path = score_root / client.client_id.value / FederatedScoreAssetName.EVALUATION.value
        if not path.is_file():
            raise ScientificContractError(
                ErrorMessage(f"missing evaluation score parquet for client {client.client_id.value}: {path}")
            )
        frame = pl.read_parquet(path)
        score_column = ScoreFrameColumn.RECONSTRUCTION_ERROR.value
        label_column = ScoreFrameColumn.OUTCOME_LABEL.value
        if score_column not in frame.columns:
            raise ScientificContractError(
                ErrorMessage(f"missing reconstruction_error column for client {client.client_id.value}: {path}")
            )
        if label_column not in frame.columns:
            raise ScientificContractError(
                ErrorMessage(f"missing outcome_label column for client {client.client_id.value}: {path}")
            )
        scores_raw = frame.get_column(score_column).to_list()
        labels = frame.get_column(label_column).to_list()
        if len(scores_raw) != len(labels):
            raise ScientificContractError(
                ErrorMessage(f"score and label columns are misaligned for client {client.client_id.value}: {path}")
            )
        if benign_only:
            scores = tuple(
                MetricValue(float(score))
                for score, label in zip(scores_raw, labels, strict=True)
                if str(label) == benign_label
            )
        else:
            scores = tuple(
                MetricValue(float(score))
                for score, label in zip(scores_raw, labels, strict=True)
                if str(label) != benign_label
            )
        pairs.append(ClientEvaluationScoreSeries(client=client, scores=scores))
    return tuple(pairs)


def _confirmatory_cluster_mechanisms() -> tuple[MechanismEvidence, ...]:
    from datp_core.analysis.mechanisms import (
        ClusterEvidenceRecord,
        cluster_assignment_switch_frequencies,
        cluster_evidence_from_grouped_result,
        cluster_feature_ablation_evidence,
        cluster_score_divergence,
        cluster_silhouette_from_grouped_result,
        cluster_stability,
        local_threshold_dispersion,
    )

    available, unavailable, corrupt = _load_cluster_threshold_results()

    if corrupt:
        raise ScientificContractError(
            ErrorMessage(
                "cluster threshold cohort has corrupt publications; "
                f"available={[seed.value for seed, _ in available]} "
                f"unavailable={[seed.value for seed in unavailable]} "
                f"corrupt={[seed.value for seed in corrupt]}"
            )
        )
    if not available:
        return ()
    if unavailable or len(available) != CONFIRMATORY_SEED_COHORT.member_count.value:
        raise ScientificContractError(
            ErrorMessage(
                "cluster threshold cohort is partial and must cover every confirmatory seed or none; "
                f"available={[seed.value for seed, _ in available]} "
                f"unavailable={[seed.value for seed in unavailable]} "
                f"corrupt={[seed.value for seed in corrupt]}"
            )
        )

    mechanisms: list[MechanismEvidence] = []
    cluster_records: list[ClusterEvidenceRecord] = []
    for seed, result in available:
        shared_cv = population_metric(
            load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD)),
            MetricId.FPR_COEFFICIENT_OF_VARIATION,
        )
        local_document = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        local_cv = population_metric(local_document, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        cluster_document = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.CLUSTER_THRESHOLD))
        cluster_cv = population_metric(cluster_document, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        local_thresholds = tuple(item.threshold for item in local_document.clients)
        local_dispersion = local_threshold_dispersion(local_thresholds) if local_thresholds else None
        cluster_record = cluster_evidence_from_grouped_result(
            result,
            local_dispersion=local_dispersion,
            shared_cv_fpr=shared_cv,
            local_cv_fpr=local_cv,
            cluster_cv_fpr=cluster_cv,
        )
        mechanisms.append(cluster_record)
        cluster_records.append(cluster_record)
        mechanisms.append(cluster_silhouette_from_grouped_result(result))
        score_divergence = jensen_shannon_from_client_scores(_client_score_vectors(cluster_document))
        mechanisms.append(cluster_score_divergence(cluster_record, score_divergence))
        mechanisms.append(_grouped_dispersion_evidence(result, cluster_document))
    for left, right in zip(available, available[1:], strict=False):
        mechanisms.append(
            cluster_stability(
                left[1].clusters,
                right[1].clusters,
                left_declared_group_count=left[1].group_count,
                right_declared_group_count=right[1].group_count,
            )
        )
    mechanisms.append(cluster_assignment_switch_frequencies(tuple(cluster_records)))
    canonical_by_seed = {seed: result for seed, result in available}
    for omitted_feature in ClusterFingerprintFeature:
        ablations, ablation_unavailable, ablation_corrupt = _load_cluster_threshold_results(omitted_feature)
        if ablation_unavailable or ablation_corrupt or len(ablations) != len(available):
            raise ScientificContractError(
                ErrorMessage(
                    f"cluster feature ablation is incomplete for {omitted_feature.value}; "
                    f"available={[seed.value for seed, _ in ablations]} "
                    f"unavailable={[seed.value for seed in ablation_unavailable]} "
                    f"corrupt={[seed.value for seed in ablation_corrupt]}"
                )
            )
        for seed, ablation in ablations:
            document = load_evaluation_document(
                _evaluation_path(
                    seed,
                    FederatedThresholdMethod.CLUSTER_THRESHOLD,
                    cluster_fingerprint_omission=omitted_feature,
                )
            )
            mechanisms.append(
                cluster_feature_ablation_evidence(
                    canonical_by_seed[seed],
                    ablation,
                    omitted_feature=omitted_feature,
                    cv_fpr=population_metric(document, MetricId.FPR_COEFFICIENT_OF_VARIATION),
                    worst_client_fpr=population_metric(document, MetricId.WORST_CLIENT_FPR),
                )
            )
    return tuple(mechanisms)


def _load_cluster_threshold_results(
    cluster_fingerprint_omission: ClusterFingerprintFeature | None = None,
) -> tuple[
    list[tuple[Seed, GroupedThresholdResult]],
    list[Seed],
    list[Seed],
]:
    from pydantic import TypeAdapter, ValidationError

    from datp_core.artifacts.repositories.thresholds import FederatedThresholdAssetName

    adapter: TypeAdapter[GroupedThresholdResult] = TypeAdapter(GroupedThresholdResult)
    available: list[tuple[Seed, GroupedThresholdResult]] = []
    unavailable: list[Seed] = []
    corrupt: list[Seed] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        coordinate = _confirmatory_coordinate(
            seed,
            FederatedThresholdMethod.CLUSTER_THRESHOLD,
            cluster_fingerprint_omission=cluster_fingerprint_omission,
        )
        directory = evaluation_run_directory(OUTPUTS_ROOT, coordinate) / EvaluationRunAssetDirectory.THRESHOLD
        result_path = directory / FederatedThresholdAssetName.RESULT
        if not result_path.is_file():
            unavailable.append(seed)
            continue
        try:
            result = adapter.validate_json(result_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, ValidationError):
            corrupt.append(seed)
            continue
        available.append((seed, result))
    return available, unavailable, corrupt


def _grouped_dispersion_evidence(
    result: GroupedThresholdResult,
    cluster_document: FederatedEvaluationDocument,
) -> GroupedDispersionResult:

    fpr_by_client = {
        item.client: metric_by_id(item.metrics, MetricId.FALSE_POSITIVE_RATE) for item in cluster_document.clients
    }
    observations: list[GroupDispersionObservation] = []
    for membership in result.clusters:
        if not membership.contributing_local_quantiles:
            continue
        thresholds = tuple(item.value for item in membership.contributing_local_quantiles)
        false_positive_rates: list[Ratio] = []
        complete = True
        for member in membership.members:
            metric = fpr_by_client.get(member)
            if metric is None or metric.status is not MetricStatus.AVAILABLE or metric.value is None:
                complete = False
                break
            false_positive_rates.append(Ratio(metric.value.value))
        if not complete or not false_positive_rates:
            continue
        observations.append(
            GroupDispersionObservation(
                group_index=membership.cluster_index,
                thresholds=thresholds,
                false_positive_rates=tuple(false_positive_rates),
            )
        )
    return grouped_dispersion(tuple(observations))


def _client_score_vectors(document: FederatedEvaluationDocument) -> tuple[ClientScoreVector, ...]:
    score_root = (
        federated_training_directory(document.score_coordinate, OUTPUTS_ROOT) / ExecutionArtifactDirectory.SCORES
    )
    vectors: list[ClientScoreVector] = []
    for client_result in sorted(document.clients, key=lambda item: item.client):
        path = score_root / client_result.client.client_id.value / FederatedScoreAssetName.CALIBRATION.value
        if not path.is_file():
            raise ScientificContractError(
                ErrorMessage(f"missing persisted benign calibration scores for JS divergence: {path}"),
                subject=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            )
        scores = tuple(
            MetricValue(float(value))
            for value in pl.read_parquet(path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
        )
        if not scores:
            raise ScientificContractError(
                ErrorMessage(f"empty calibration score vector for client {client_result.client.client_id.value}"),
                subject=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            )
        vectors.append(ClientScoreVector(client=client_result.client, scores=scores))
    if len(vectors) < 2:
        raise ScientificContractError(
            ErrorMessage("Jensen-Shannon construction requires at least two client score vectors")
        )
    return tuple(vectors)


def _natural_device_family_assignments(clients: tuple[ClientIdentity, ...]) -> tuple[FamilyAssignment, ...]:
    if not clients or any(client.population is not PopulationId.NBAIOT_NATURAL_DEVICES for client in clients):
        raise ScientificContractError(ErrorMessage("family adequacy requires N-BaIoT natural-device clients"))
    assignments: list[FamilyAssignment] = []
    for client in sorted(clients):
        try:
            device = NBaIoTDevice(client.client_id.value)
        except ValueError as error:
            raise ScientificContractError(
                ErrorMessage(f"unrecognized N-BaIoT natural-device identity: {client.client_id.value}")
            ) from error
        assignments.append(FamilyAssignment(client=client, family=FamilyIdentity(device_family(device).value)))
    return tuple(assignments)


def _confirmatory_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    if len(matches) != 1:
        raise ScientificContractError(ErrorMessage("the confirmatory experiment must be declared exactly once"))
    return matches[0]


def _declaration_for_threshold_method(method: FederatedThresholdMethod) -> ExperimentDeclaration:
    if method in {FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD}:
        return _confirmatory_declaration()
    if method in {
        FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
        FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD,
        FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS,
    }:
        return _declaration_by_id(ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY)
    if method is FederatedThresholdMethod.LOCAL_GLOBAL_SHRINKAGE:
        return _declaration_by_id(ExperimentId.FIXED_SHRINKAGE_CURVE)
    if method is FederatedThresholdMethod.SIZE_AWARE_SHRINKAGE:
        return _declaration_by_id(ExperimentId.SIZE_AWARE_SHRINKAGE)
    if method in {FederatedThresholdMethod.FAMILY_THRESHOLD, FederatedThresholdMethod.CLUSTER_THRESHOLD}:
        return _declaration_by_id(ExperimentId.FAMILY_AND_GROUPED_GRANULARITY)
    raise ScientificContractError(
        ErrorMessage(f"confirmatory experiment cannot resolve a publication coordinate for {method.value}")
    )


def _declaration_by_id(experiment_id: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    if len(matches) != 1:
        raise ScientificContractError(ErrorMessage(f"{experiment_id.value} must be declared exactly once"))
    return matches[0]


def _confirmatory_coordinate(
    training_seed: Seed,
    method: FederatedThresholdMethod,
    *,
    cluster_fingerprint_omission: ClusterFingerprintFeature | None = None,
) -> ExperimentCoordinate:
    declaration = _declaration_for_threshold_method(method)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(training_seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
        and entry.coordinate.cluster_fingerprint_omission is cluster_fingerprint_omission
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(
                f"evaluation coordinate for {method.value} must resolve exactly once under {declaration.id.value}"
            )
        )
    return matches[0]


def _confirmatory_contrast(training_seed: Seed) -> PairedContrast:
    shared = load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.SHARED_THRESHOLD))
    local = load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
    metric = MetricId.FPR_COEFFICIENT_OF_VARIATION
    return build_paired_contrast(
        left=shared,
        right=local,
        metric=metric,
        left_value=population_metric(shared, metric),
        right_value=population_metric(local, metric),
        evidence_role=EvidenceRole.CONFIRMATORY,
    )


def load_fedavg_cv_fpr_effect(training_seed: Seed, *, experiment: ExperimentId) -> FedAvgCvFprEffectEvidence:
    shared_document = load_evaluation_document(
        _evaluation_path(training_seed, FederatedThresholdMethod.SHARED_THRESHOLD)
    )
    local_document = load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
    return FedAvgCvFprEffectEvidence(
        seed=training_seed,
        shared=absorption_corner_from_evaluation_document(shared_document, experiment=experiment),
        local=absorption_corner_from_evaluation_document(local_document, experiment=experiment),
    )


def absorption_corner_from_evaluation_document(
    document: FederatedEvaluationDocument,
    *,
    experiment: ExperimentId,
) -> AbsorptionCornerEvidence:
    coordinate = document.score_coordinate
    coefficient = (
        ModelCoefficientValue(coordinate.model_coefficient.value) if coordinate.model_coefficient is not None else None
    )
    return AbsorptionCornerEvidence(
        seed=coordinate.training_seed,
        experiment=experiment,
        population=coordinate.population,
        model=coordinate.model,
        threshold_method=document.threshold_method,
        coefficient=coefficient,
        population_cv_fpr=population_metric(document, MetricId.FPR_COEFFICIENT_OF_VARIATION),
    )


def _evaluation_path(
    training_seed: Seed,
    method: FederatedThresholdMethod,
    *,
    cluster_fingerprint_omission: ClusterFingerprintFeature | None = None,
) -> Path:
    coordinate = _confirmatory_coordinate(
        training_seed,
        method,
        cluster_fingerprint_omission=cluster_fingerprint_omission,
    )
    path = (
        evaluation_run_directory(OUTPUTS_ROOT, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(ErrorMessage(f"missing completed evaluation document: {path}"))
    return path
