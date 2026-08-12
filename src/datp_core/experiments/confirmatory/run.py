from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.analysis.contrasts import PairedContrast, PairedContrasts, build_paired_contrast
from datp_core.analysis.descriptive import (
    ClientEvaluationScoreSeries,
    ScoreGeometryResult,
    ScoreGeometryThresholdOverlay,
    score_geometry_from_client_vectors,
)
from datp_core.analysis.evidence import AnalyzeConfirmatoryEvidenceRequest, analyze_confirmatory_evidence
from datp_core.analysis.mechanisms import (
    AbsorptionCornerEvidence,
    AssociationObservation,
    ClientScoreVector,
    GroupDispersionObservation,
    GroupedDispersionResult,
    MechanismEvidence,
    ThresholdMovementCohort,
    campaign_fixed_support_strata,
    confirmatory_equity_utility_bundle,
    grouped_dispersion,
    heterogeneity_benefit_association,
    jensen_shannon_from_client_scores,
    summarize_client_impact,
    summarize_client_impact_campaign,
    summarize_support_stratum_campaign,
    summarize_threshold_movements_across_seeds,
    support_stratum_seed_outcomes,
    threshold_movements_from_evaluations,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import MetricStatus, metric_by_id
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
    FederatedThresholdMethod,
    FigureTitle,
    MetricId,
    PopulationId,
    RegimeLabel,
    ScoreFrameColumn,
    TrainingModelId,
)
from datp_core.core.numeric import MetricValue, ModelCoefficientValue, Ratio, Seed
from datp_core.data.nbaiot.schema import NBaIoTDevice
from datp_core.data.populations.contracts import ClientIdentity
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
from datp_core.presentation.export import export_confirmatory_publication, export_mechanism_publication
from datp_core.presentation.figures import FigureSpec, score_geometry_figure
from datp_core.runtime.configuration import OUTPUTS_ROOT
from datp_core.thresholds.policies.cluster import GroupedThresholdResult


class ConfirmatoryAssetDirectory(StrEnum):
    ROOT = "confirmatory"
    ANALYSIS = "analysis"
    SCORE_GEOMETRY = "score_geometry"
    MECHANISMS = "mechanisms"


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
    result = analyze_confirmatory_evidence(
        AnalyzeConfirmatoryEvidenceRequest(
            contrasts=PairedContrasts(
                values=tuple(_confirmatory_contrast(seed) for seed in CONFIRMATORY_SEED_COHORT.values)
            ),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
            output_directory=output,
            mechanisms=all_mechanisms,
        )
    )
    geometries, figures = build_confirmatory_score_geometry()
    persist_score_geometry(geometries, output / ConfirmatoryAssetDirectory.SCORE_GEOMETRY)
    export_confirmatory_publication(
        result.document,
        output,
        verified_anchor_gate=None,
        figures=figures,
    )
    if all_mechanisms:
        export_mechanism_publication(
            all_mechanisms,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output / ConfirmatoryAssetDirectory.MECHANISMS,
            evidence_role=EvidenceRole.MECHANISM,
        )
    return output


def _confirmatory_mechanisms() -> tuple[MechanismEvidence, ...]:
    movement_cohorts: list[ThresholdMovementCohort] = []
    policy_pairs: list[tuple[FederatedEvaluationDocument, FederatedEvaluationDocument]] = []
    association_observations: list[AssociationObservation] = []
    mechanisms: list[MechanismEvidence] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        policy_pairs.append((shared, local))
        movement = threshold_movements_from_evaluations(
            shared=shared,
            local=local,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        )
        movement_cohorts.append(movement)
        mechanisms.append(movement)
        mechanisms.append(summarize_client_impact(movement))
        shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        benefit = MetricValue(shared_cv.value - local_cv.value)
        vectors = _client_score_vectors(shared)
        divergence = jensen_shannon_from_client_scores(vectors)
        mechanisms.append(divergence)
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
    mechanisms.append(confirmatory_equity_utility_bundle(tuple(policy_pairs)))
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
    return tuple(geometries), tuple(figures)


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
        cluster_evidence_from_grouped_result,
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
        mechanisms.append(
            cluster_evidence_from_grouped_result(
                result,
                local_dispersion=local_dispersion,
                shared_cv_fpr=shared_cv,
                local_cv_fpr=local_cv,
                cluster_cv_fpr=cluster_cv,
            )
        )
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
    return tuple(mechanisms)


def _load_cluster_threshold_results() -> tuple[
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
        coordinate = _confirmatory_coordinate(seed, FederatedThresholdMethod.CLUSTER_THRESHOLD)
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


def _confirmatory_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    if len(matches) != 1:
        raise ScientificContractError(ErrorMessage("the confirmatory experiment must be declared exactly once"))
    return matches[0]


def _declaration_for_threshold_method(method: FederatedThresholdMethod) -> ExperimentDeclaration:
    if method in {FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD}:
        return _confirmatory_declaration()
    if method is FederatedThresholdMethod.CLUSTER_THRESHOLD:
        matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.FAMILY_AND_GROUPED_GRANULARITY)
        if len(matches) != 1:
            raise ScientificContractError(
                ErrorMessage("family/grouped mechanism experiment must be declared exactly once")
            )
        return matches[0]
    raise ScientificContractError(
        ErrorMessage(f"confirmatory experiment cannot resolve a publication coordinate for {method.value}")
    )


def _confirmatory_coordinate(training_seed: Seed, method: FederatedThresholdMethod) -> ExperimentCoordinate:
    declaration = _declaration_for_threshold_method(method)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(training_seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
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


def _evaluation_path(training_seed: Seed, method: FederatedThresholdMethod) -> Path:
    coordinate = _confirmatory_coordinate(training_seed, method)
    path = (
        evaluation_run_directory(OUTPUTS_ROOT, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(ErrorMessage(f"missing completed evaluation document: {path}"))
    return path
