"""Confirmatory campaign execution and paired evidence analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.analysis.contrasts import PairedContrast, build_paired_contrast
from datp_core.analysis.descriptive import (
    ScoreGeometryResult,
    ScoreGeometryThresholdOverlay,
    score_geometry_from_client_vectors,
)
from datp_core.analysis.mechanisms import (
    AbsorptionCornerEvidence,
    AssociationObservation,
    ClientScoreVector,
    MechanismEvidence,
    ThresholdMovementCohort,
    heterogeneity_benefit_association,
    jensen_shannon_from_client_scores,
    summarize_threshold_movements_across_seeds,
    threshold_movements_from_evaluations,
)
from datp_core.datasets.partitioning.contracts import ClientIdentity
from datp_core.domain.enums import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    ScoreFrameColumn,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.ratios import MetricValue, ModelCoefficientValue
from datp_core.evaluation.federated.contracts import FederatedEvaluationDocument
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.pipeline.coordinates import ExperimentCoordinate
from datp_core.pipeline.decision.evidence import AnalyzeConfirmatoryEvidenceRequest, analyze_confirmatory_evidence
from datp_core.pipeline.execution.engine import (
    CompletionRecordOutputStore,
    PipelineStageRunner,
    build_campaign,
    execute_campaign,
)
from datp_core.pipeline.execution.evidence import load_evaluation_document, population_metric
from datp_core.pipeline.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    federated_training_directory,
)
from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.pipeline.publication.layout import evaluation_run_directory
from datp_core.pipeline.scoring.models import FederatedScoreAssetName
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration
from datp_core.protocols.seeds import CONFIRMATORY_ANALYSIS_SEED, CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.reporting.export import (
    export_confirmatory_publication,
    export_mechanism_publication,
)
from datp_core.reporting.figures import FigureSpec
from datp_core.runtime.configuration import OUTPUTS_ROOT


class ConfirmatoryAssetDirectory(StrEnum):
    ROOT = "confirmatory"
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatorySeedResult:
    training_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatoryCampaignResult:
    seeds: tuple[ConfirmatorySeedResult, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FedAvgCvFprEffectEvidence:
    """Artifact-bound FedAvg SHARED/LOCAL CV(FPR) corners and paired effect for one seed."""

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
    output_root: Path | None = None,
    overwrite: bool = False,
) -> ConfirmatorySeedResult:
    declaration = _confirmatory_declaration()
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(training_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="the confirmatory entry point supplies the locked natural-device execution prerequisites",
            ),
        ),
    )
    campaign = build_campaign(plan)
    if not campaign.entries:
        raise ScientificContractError("confirmatory planning produced no executable coordinates")
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=PipelineStageRunner(),
        output_store=CompletionRecordOutputStore(),
        output_root=OUTPUTS_ROOT if output_root is None else output_root,
        overwrite=overwrite,
    )
    failed = tuple(result for result in execution.experiments if not result.successful)
    if failed:
        blocked = ", ".join(result.coordinate.stable_key for result in failed)
        raise ScientificContractError(f"confirmatory execution did not complete: {blocked}")
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return ConfirmatorySeedResult(
        training_seed=training_seed,
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )


def run_confirmatory_campaign() -> ConfirmatoryCampaignResult:
    seeds = tuple(run_confirmatory_seed(seed) for seed in CONFIRMATORY_SEED_COHORT.values)
    return ConfirmatoryCampaignResult(seeds=seeds)


def run_family_grouped_mechanism_seed(
    training_seed: Seed,
    *,
    output_root: Path | None = None,
    overwrite: bool = False,
) -> ConfirmatorySeedResult:
    """Execute the family/grouped mechanism ladder for one seed under fixed FedAvg detector.

    Publishes FAMILY_THRESHOLD and CLUSTER_THRESHOLD (with the rest of the locked
    ladder methods declared on FAMILY_AND_GROUPED_GRANULARITY) so confirmatory
    analysis can attach B3/B4 mechanism evidence when present.
    """
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.FAMILY_AND_GROUPED_GRANULARITY)
    if len(matches) != 1:
        raise ScientificContractError("family/grouped mechanism experiment must be declared exactly once")
    declaration = matches[0]
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(training_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=(
                    "the family/grouped mechanism entry point supplies the locked "
                    "natural-device execution prerequisites for B3/B4 evidence"
                ),
            ),
        ),
    )
    campaign = build_campaign(plan)
    if not campaign.entries:
        raise ScientificContractError("family/grouped planning produced no executable coordinates")
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=PipelineStageRunner(),
        output_store=CompletionRecordOutputStore(),
        output_root=OUTPUTS_ROOT if output_root is None else output_root,
        overwrite=overwrite,
    )
    failed = tuple(result for result in execution.experiments if not result.successful)
    if failed:
        blocked = ", ".join(result.coordinate.stable_key for result in failed)
        raise ScientificContractError(f"family/grouped execution did not complete: {blocked}")
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return ConfirmatorySeedResult(
        training_seed=training_seed,
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )


def run_family_grouped_mechanism_campaign() -> ConfirmatoryCampaignResult:
    seeds = tuple(run_family_grouped_mechanism_seed(seed) for seed in CONFIRMATORY_SEED_COHORT.values)
    return ConfirmatoryCampaignResult(seeds=seeds)


def analyze_confirmatory_campaign(
    *,
    anchor_gate_diagnostics_directory: Path | None = None,
) -> Path:
    """Analyze confirmatory campaign and export publication artifacts.

    Confirmatory claims require a checksum-verified anchor-gate artifact and a
    programme-bound confirmatory handoff. Missing or stale gate evidence fails closed.
    """
    from datp_core.anchor.gate import (
        load_anchor_confirmatory_handoff,
        load_verified_anchor_gate_artifact,
    )

    output = (
        OUTPUTS_ROOT
        / ConfirmatoryAssetDirectory.ROOT
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / ConfirmatoryAssetDirectory.ANALYSIS
    )
    gate_directory = anchor_gate_diagnostics_directory or (OUTPUTS_ROOT / "anchor" / "diagnostics")
    verified_gate = load_verified_anchor_gate_artifact(gate_directory)
    load_anchor_confirmatory_handoff(gate_directory, verified_gate=verified_gate)
    mechanisms = _confirmatory_mechanisms()
    cluster_mechanisms = _confirmatory_cluster_mechanisms()
    all_mechanisms = mechanisms + cluster_mechanisms
    result = analyze_confirmatory_evidence(
        AnalyzeConfirmatoryEvidenceRequest(
            contrasts=tuple(_confirmatory_contrast(seed) for seed in CONFIRMATORY_SEED_COHORT.values),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=CONFIRMATORY_ANALYSIS_SEED,
            output_directory=output,
            overwrite=False,
            mechanisms=all_mechanisms,
        )
    )
    geometries, figures = _confirmatory_score_geometry()
    _persist_score_geometry(geometries, output / "score_geometry")
    export_confirmatory_publication(
        result.document,
        output,
        verified_anchor_gate=verified_gate,
        figures=figures,
    )
    if all_mechanisms:
        export_mechanism_publication(
            all_mechanisms,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output / "mechanisms",
        )
    return output


def _confirmatory_mechanisms() -> tuple[MechanismEvidence, ...]:
    movement_cohorts: list[ThresholdMovementCohort] = []
    association_observations: list[AssociationObservation] = []
    mechanisms: list[MechanismEvidence] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        local = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        movement = threshold_movements_from_evaluations(
            shared=shared,
            local=local,
            experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        )
        movement_cohorts.append(movement)
        mechanisms.append(movement)
        shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        benefit = MetricValue(shared_cv.value - local_cv.value)
        vectors, score_checksum = _client_score_vectors(shared)
        divergence = jensen_shannon_from_client_scores(vectors, source_score_checksum=score_checksum)
        mechanisms.append(divergence)
        if divergence.aggregate is not None:
            association_observations.append(
                AssociationObservation(
                    seed=seed,
                    experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
                    population=PopulationId.NBAIOT_NATURAL_DEVICES,
                    regime_label=f"seed_{seed.value}",
                    heterogeneity=divergence.aggregate,
                    benefit=benefit,
                )
            )
    mechanisms.append(
        summarize_threshold_movements_across_seeds(
            tuple(movement_cohorts),
            required_seed_count=CONFIRMATORY_SEED_COHORT.member_count.value,
        )
    )
    if association_observations:
        mechanisms.append(heterogeneity_benefit_association(tuple(association_observations)))
    return tuple(mechanisms)


def _confirmatory_score_geometry() -> tuple[tuple[ScoreGeometryResult, ...], tuple[FigureSpec, ...]]:
    """Build per-seed score geometry evidence and empirical-CDF figure specs.

    Every evaluation-document client is retained. Missing score artifacts raise.
    Unavailable roles become typed unavailable CDF series rather than silent omission.
    """
    geometries: list[ScoreGeometryResult] = []
    figures: list[FigureSpec] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD))
        expected_clients = tuple(sorted(item.client for item in shared.clients))
        if not expected_clients:
            raise ScientificContractError(
                f"confirmatory score geometry requires evaluation clients for seed {seed.value}"
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
        attack_available = any(scores for _, scores in attack_eval)
        geometry = score_geometry_from_client_vectors(
            seed=seed,
            source_score_checksum=shared.fixed_score_evidence.evaluation.score_checksum,
            benign_evaluation=benign_eval,
            attack_evaluation=attack_eval,
            threshold_overlays=_score_geometry_threshold_overlays(seed, expected_clients),
            attack_geometry_available=attack_available,
            attack_geometry_reason=None if attack_available else "attack evaluation scores unavailable",
        )
        geometries.append(geometry)
        figures.append(_empirical_cdf_figure_from_geometry(geometry))
    return tuple(geometries), tuple(figures)


def _persist_score_geometry(
    geometries: tuple[ScoreGeometryResult, ...],
    output_directory: Path,
) -> None:
    from datp_core.domain.provenance import serialize_json_model

    output_directory.mkdir(parents=True, exist_ok=True)
    for geometry in geometries:
        serialize_json_model(geometry, output_directory / f"seed_{geometry.seed.value}.json")


def _empirical_cdf_figure_from_geometry(geometry: ScoreGeometryResult) -> FigureSpec:
    from datp_core.reporting.figures import EmpiricalCdfFigureSeries, empirical_cdf_series_from_points

    series: list[EmpiricalCdfFigureSeries] = []
    for client_geometry in geometry.clients:
        label = f"seed{geometry.seed.value}:{client_geometry.client.client_id}:{client_geometry.score_role.value}"
        overlays = _client_threshold_overlay_pairs(geometry.threshold_overlays, client_geometry.client)
        if client_geometry.unavailable_reason is not None:
            series.append(
                empirical_cdf_series_from_points(
                    label=label,
                    points=(),
                    client_id=client_geometry.client.client_id,
                    seed=geometry.seed,
                    score_role=client_geometry.score_role.value,
                    threshold_overlays=(),
                    source_checksum=geometry.source_score_checksum,
                    unavailable_reason=client_geometry.unavailable_reason,
                )
            )
            continue
        points = tuple(
            (point.score, MetricValue(point.cumulative_probability.value)) for point in client_geometry.empirical_cdf
        )
        series.append(
            empirical_cdf_series_from_points(
                label=label,
                points=points,
                client_id=client_geometry.client.client_id,
                seed=geometry.seed,
                score_role=client_geometry.score_role.value,
                threshold_overlays=overlays,
                source_checksum=geometry.source_score_checksum,
            )
        )
    if not series:
        raise ScientificContractError(
            f"confirmatory score geometry produced no client series for seed {geometry.seed.value}"
        )
    return FigureSpec(
        title=f"Per-client empirical score CDF (seed {geometry.seed.value})",
        empirical_cdf_series=tuple(series),
    )


def _client_threshold_overlay_pairs(
    overlays: tuple[ScoreGeometryThresholdOverlay, ...],
    client: ClientIdentity,
) -> tuple[tuple[str, float], ...]:
    return tuple(
        (item.method.value, item.threshold.value) for item in overlays if item.client is None or item.client == client
    )


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
        try:
            document = load_evaluation_document(_evaluation_path(seed, method))
        except ScientificContractError:
            continue
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
    return tuple(overlays)


def _client_evaluation_scores(
    *,
    score_coordinate: FederatedTrainingCoordinate,
    document_clients: tuple[ClientIdentity, ...],
    expected_clients: tuple[ClientIdentity, ...],
    benign_only: bool,
) -> tuple[tuple[ClientIdentity, tuple[MetricValue, ...]], ...]:
    from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel

    ordered_document_clients = tuple(sorted(document_clients))
    if frozenset(ordered_document_clients) != frozenset(expected_clients):
        missing = sorted(
            client.client_id for client in expected_clients if client not in frozenset(ordered_document_clients)
        )
        extra = sorted(
            client.client_id for client in ordered_document_clients if client not in frozenset(expected_clients)
        )
        raise ScientificContractError(
            "evaluation document clients do not match the expected score-geometry client set"
            f" missing={missing} extra={extra}"
        )
    if len(ordered_document_clients) != len(frozenset(ordered_document_clients)):
        raise ScientificContractError("evaluation document clients must be unique for score geometry")

    score_root = federated_training_directory(score_coordinate, OUTPUTS_ROOT) / ExecutionArtifactDirectory.SCORES
    pairs: list[tuple[ClientIdentity, tuple[MetricValue, ...]]] = []
    benign_label = PopulationOutcomeLabel.BENIGN.value
    for client in expected_clients:
        path = score_root / client.client_id / FederatedScoreAssetName.EVALUATION.value
        if not path.is_file():
            raise ScientificContractError(f"missing evaluation score parquet for client {client.client_id}: {path}")
        frame = pl.read_parquet(path)
        score_column = ScoreFrameColumn.RECONSTRUCTION_ERROR.value
        label_column = ScoreFrameColumn.OUTCOME_LABEL.value
        if score_column not in frame.columns:
            raise ScientificContractError(f"missing reconstruction_error column for client {client.client_id}: {path}")
        if label_column not in frame.columns:
            raise ScientificContractError(f"missing outcome_label column for client {client.client_id}: {path}")
        scores_raw = frame.get_column(score_column).to_list()
        labels = frame.get_column(label_column).to_list()
        if len(scores_raw) != len(labels):
            raise ScientificContractError(
                f"score and label columns are misaligned for client {client.client_id}: {path}"
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
        pairs.append((client, scores))
    return tuple(pairs)


def _confirmatory_cluster_mechanisms() -> tuple[MechanismEvidence, ...]:
    """Load CLUSTER_THRESHOLD mechanism evidence when a complete cohort is present.

    Confirmatory B1-versus-B2 analysis does not require B4. A completely absent
    cluster cohort yields no mechanism records. A partial or corrupt cohort fails
    closed so incomplete mechanism execution cannot look complete.
    """
    from pydantic import TypeAdapter, ValidationError

    from datp_core.analysis.mechanisms import (
        cluster_evidence_from_grouped_result,
        cluster_stability,
        local_threshold_dispersion,
    )
    from datp_core.thresholding.methods.cluster import GroupedThresholdResult
    from datp_core.thresholding.publication import (
        FederatedThresholdAssetName,
        federated_threshold_publication_checksum,
        threshold_result_checksum,
    )

    adapter: TypeAdapter[GroupedThresholdResult] = TypeAdapter(GroupedThresholdResult)
    available: list[tuple[Seed, GroupedThresholdResult, Checksum]] = []
    unavailable: list[Seed] = []
    corrupt: list[Seed] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        coordinate = _confirmatory_coordinate(seed, FederatedThresholdMethod.CLUSTER_THRESHOLD)
        directory = evaluation_run_directory(OUTPUTS_ROOT, coordinate) / EvaluationRunAssetDirectory.THRESHOLD
        result_path = directory / FederatedThresholdAssetName.RESULT
        complete_path = directory / FederatedThresholdAssetName.COMPLETE
        if not result_path.is_file() or not complete_path.is_file():
            unavailable.append(seed)
            continue
        try:
            result = adapter.validate_json(result_path.read_text(encoding="utf-8"))
            complete_marker = complete_path.read_text(encoding="utf-8").strip()
            expected_marker = federated_threshold_publication_checksum(result, None).value
            if complete_marker != expected_marker:
                corrupt.append(seed)
                continue
        except (OSError, ValueError, TypeError, ValidationError):
            corrupt.append(seed)
            continue
        available.append((seed, result, threshold_result_checksum(result)))

    if corrupt:
        raise ScientificContractError(
            "cluster threshold cohort has corrupt publications; "
            f"available={[seed.value for seed, _, _ in available]} "
            f"unavailable={[seed.value for seed in unavailable]} "
            f"corrupt={[seed.value for seed in corrupt]}"
        )
    if not available:
        return ()
    if unavailable or len(available) != CONFIRMATORY_SEED_COHORT.member_count.value:
        raise ScientificContractError(
            "cluster threshold cohort is partial and must cover every confirmatory seed or none; "
            f"available={[seed.value for seed, _, _ in available]} "
            f"unavailable={[seed.value for seed in unavailable]} "
            f"corrupt={[seed.value for seed in corrupt]}"
        )

    mechanisms: list[MechanismEvidence] = []
    for seed, result, checksum in available:
        shared_cv = population_metric(
            load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.SHARED_THRESHOLD)),
            MetricId.FPR_COEFFICIENT_OF_VARIATION,
        )
        local_document = load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
        local_cv = population_metric(local_document, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        cluster_cv = population_metric(
            load_evaluation_document(_evaluation_path(seed, FederatedThresholdMethod.CLUSTER_THRESHOLD)),
            MetricId.FPR_COEFFICIENT_OF_VARIATION,
        )
        local_thresholds = tuple(item.threshold for item in local_document.clients)
        local_dispersion = local_threshold_dispersion(local_thresholds) if local_thresholds else None
        mechanisms.append(
            cluster_evidence_from_grouped_result(
                result,
                source_threshold_checksum=checksum,
                local_dispersion=local_dispersion,
                shared_cv_fpr=shared_cv,
                local_cv_fpr=local_cv,
                cluster_cv_fpr=cluster_cv,
            )
        )
    for left, right in zip(available, available[1:], strict=False):
        mechanisms.append(
            cluster_stability(
                left[1].clusters,
                right[1].clusters,
                left_source_checksum=left[2],
                right_source_checksum=right[2],
                left_declared_group_count=left[1].group_count.value,
                right_declared_group_count=right[1].group_count.value,
            )
        )
    return tuple(mechanisms)


def _client_score_vectors(
    document: FederatedEvaluationDocument,
) -> tuple[tuple[ClientScoreVector, ...], Checksum]:
    score_root = (
        federated_training_directory(document.score_coordinate, OUTPUTS_ROOT) / ExecutionArtifactDirectory.SCORES
    )
    vectors: list[ClientScoreVector] = []
    for client_result in sorted(document.clients, key=lambda item: item.client):
        path = score_root / client_result.client.client_id / FederatedScoreAssetName.CALIBRATION.value
        if not path.is_file():
            raise ScientificContractError(
                f"missing persisted benign calibration scores for JS divergence: {path}",
                subject=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            )
        scores = tuple(
            MetricValue(float(value))
            for value in pl.read_parquet(path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
        )
        if not scores:
            raise ScientificContractError(
                f"empty calibration score vector for client {client_result.client.client_id}",
                subject=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            )
        vectors.append(ClientScoreVector(client=client_result.client, scores=scores))
    if len(vectors) < 2:
        raise ScientificContractError("Jensen-Shannon construction requires at least two client score vectors")
    return tuple(vectors), document.fixed_score_evidence.calibration.score_checksum


def _confirmatory_declaration() -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    if len(matches) != 1:
        raise ScientificContractError("the confirmatory experiment must be declared exactly once")
    return matches[0]


def _declaration_for_threshold_method(method: FederatedThresholdMethod) -> ExperimentDeclaration:
    """Map threshold methods to the experiment declaration that publishes their run layout."""
    if method in {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    }:
        return _confirmatory_declaration()
    if method is FederatedThresholdMethod.CLUSTER_THRESHOLD:
        matches = tuple(item for item in EXPERIMENTS if item.id is ExperimentId.FAMILY_AND_GROUPED_GRANULARITY)
        if len(matches) != 1:
            raise ScientificContractError("family/grouped mechanism experiment must be declared exactly once")
        return matches[0]
    raise ScientificContractError(f"confirmatory workflow cannot resolve a publication coordinate for {method.value}")


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
            f"evaluation coordinate for {method.value} must resolve exactly once under {declaration.id.value}"
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
        left_value=_required_metric(shared, metric),
        right_value=_required_metric(local, metric),
        evidence_role=EvidenceRole.CONFIRMATORY,
    )


def load_fedavg_cv_fpr_effect(
    training_seed: Seed,
    *,
    experiment: ExperimentId,
) -> FedAvgCvFprEffectEvidence:
    """Load FedAvg SHARED/LOCAL CV(FPR) corners with evaluation provenance from confirmatory artifacts.

    ``experiment`` stamps the absorption (or other consumer) observation identity onto the corners.
    """
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
    """Map one federated evaluation document into typed absorption corner provenance."""
    coordinate = document.score_coordinate
    evidence = document.fixed_score_evidence
    coefficient = (
        ModelCoefficientValue(coordinate.model_coefficient.value) if coordinate.model_coefficient is not None else None
    )
    return AbsorptionCornerEvidence(
        seed=coordinate.training_seed,
        experiment=experiment,
        population=coordinate.population.value,
        model=coordinate.model,
        threshold_method=document.threshold_method,
        coefficient=coefficient,
        checkpoint_checksum=document.score_checkpoint_checksum,
        preprocessing_checksum=document.preprocessing_state_set_checksum,
        split_checksum=document.split_manifest_checksum,
        calibration_score_checksum=evidence.calibration.score_checksum,
        evaluation_score_checksum=evidence.evaluation.score_checksum,
        evaluation_checksum=canonical_checksum(document),
        client_inventory_checksum=evidence.population.client_inventory_checksum,
        eligibility_checksum=evidence.population.eligibility_cohort_checksum,
        population_cv_fpr=population_metric(document, MetricId.FPR_COEFFICIENT_OF_VARIATION),
    )


def _required_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    return population_metric(document, metric)


def _evaluation_path(training_seed: Seed, method: FederatedThresholdMethod) -> Path:
    coordinate = _confirmatory_coordinate(training_seed, method)
    path = (
        evaluation_run_directory(OUTPUTS_ROOT, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(f"missing completed evaluation document: {path}")
    return path
