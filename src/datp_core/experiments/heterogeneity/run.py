"""Controlled heterogeneity sweep and mechanism experiment execution.

The controlled heterogeneity sweep executes training on the declared Dirichlet
populations. Score geometry, heterogeneity-benefit association, and threshold
movement analyses reuse frozen confirmatory score artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.analysis.descriptive import (
    ScoreGeometryResult,
    ScoreGeometryThresholdOverlay,
    score_geometry_from_client_vectors,
)
from datp_core.analysis.mechanisms import (
    AssociationObservation,
    ClientScoreVector,
    MechanismEvidence,
    ThresholdMovementCohort,
    heterogeneity_benefit_association,
    jensen_shannon_from_client_scores,
    summarize_threshold_movements_across_seeds,
    threshold_movements_from_evaluations,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.protocols import FIXED_SCORE_AUROC_INVARIANCE_TOLERANCE
from datp_core.app.planning import expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    ScoreFrameColumn,
)
from datp_core.core.numeric import DirichletConcentration, MetricValue, Seed
from datp_core.data.populations.contracts import ClientIdentity, ControlledPartitionKind
from datp_core.data.populations.declarations import DIRICHLET_CONCENTRATIONS
from datp_core.detector.scoring.models import FederatedScoreAssetName
from datp_core.detector.training.models import FederatedTrainingCoordinate
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document, population_metric
from datp_core.experiments.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    federated_training_directory,
)
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.presentation.export import export_mechanism_publication
from datp_core.runtime.configuration import OUTPUTS_ROOT


class MechanismAnalysisDirectory(StrEnum):
    ROOT = "mechanisms"
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class HeterogeneitySweepSeedResult:
    training_seed: Seed
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


def run_controlled_heterogeneity_sweep_seed(
    training_seed: Seed,
    *,
    output_root: Path,
    overwrite: bool,
) -> HeterogeneitySweepSeedResult:
    declaration = _require_declaration(ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP)
    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(training_seed,)),
        reason="controlled heterogeneity sweep executes the locked Dirichlet population grid",
        output_root=output_root,
        overwrite=overwrite,
    )
    return HeterogeneitySweepSeedResult(
        training_seed=training_seed,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def analyze_controlled_heterogeneity_sweep(*, overwrite: bool) -> Path:
    output = (
        OUTPUTS_ROOT
        / MechanismAnalysisDirectory.ROOT
        / ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP.value
        / PopulationId.NBAIOT_DIRICHLET_CLIENTS.value
        / MechanismAnalysisDirectory.ANALYSIS
    )
    if overwrite and output.exists():
        from shutil import rmtree

        rmtree(output)

    mechanisms: list[MechanismEvidence] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        for concentration in DIRICHLET_CONCENTRATIONS:
            shared = _load_heterogeneity_evaluation(
                seed,
                FederatedThresholdMethod.SHARED_THRESHOLD,
                ControlledPartitionKind.DIRICHLET,
                concentration,
            )
            local = _load_heterogeneity_evaluation(
                seed,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                ControlledPartitionKind.DIRICHLET,
                concentration,
            )
            movement = threshold_movements_from_evaluations(
                shared=shared,
                local=local,
                experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            )
            mechanisms.append(movement)
            vectors, score_checksum = _client_score_vectors(shared)
            mechanisms.append(jensen_shannon_from_client_scores(vectors, source_score_checksum=score_checksum))
        iid_shared = _load_heterogeneity_evaluation(
            seed,
            FederatedThresholdMethod.SHARED_THRESHOLD,
            ControlledPartitionKind.IID,
            None,
        )
        iid_local = _load_heterogeneity_evaluation(
            seed,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            ControlledPartitionKind.IID,
            None,
        )
        mechanisms.append(
            threshold_movements_from_evaluations(
                shared=iid_shared,
                local=iid_local,
                experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            )
        )
        iid_vectors, iid_score_checksum = _client_score_vectors(iid_shared)
        mechanisms.append(jensen_shannon_from_client_scores(iid_vectors, source_score_checksum=iid_score_checksum))

    association_observations: list[AssociationObservation] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        for concentration in DIRICHLET_CONCENTRATIONS:
            shared = _load_heterogeneity_evaluation(
                seed,
                FederatedThresholdMethod.SHARED_THRESHOLD,
                ControlledPartitionKind.DIRICHLET,
                concentration,
            )
            local = _load_heterogeneity_evaluation(
                seed,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                ControlledPartitionKind.DIRICHLET,
                concentration,
            )
            shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
            local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
            vectors, score_checksum = _client_score_vectors(shared)
            divergence = jensen_shannon_from_client_scores(vectors, source_score_checksum=score_checksum)
            if divergence.aggregate is not None:
                association_observations.append(
                    AssociationObservation(
                        seed=seed,
                        experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
                        population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
                        regime_label=f"alpha_{concentration.value}",
                        heterogeneity=divergence.aggregate,
                        benefit=MetricValue(shared_cv.value - local_cv.value),
                    )
                )
        iid_shared = _load_heterogeneity_evaluation(
            seed,
            FederatedThresholdMethod.SHARED_THRESHOLD,
            ControlledPartitionKind.IID,
            None,
        )
        iid_local = _load_heterogeneity_evaluation(
            seed,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            ControlledPartitionKind.IID,
            None,
        )
        iid_vectors, iid_score_checksum = _client_score_vectors(iid_shared)
        iid_divergence = jensen_shannon_from_client_scores(iid_vectors, source_score_checksum=iid_score_checksum)
        if iid_divergence.aggregate is not None:
            association_observations.append(
                AssociationObservation(
                    seed=seed,
                    experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
                    population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
                    regime_label="IID",  # TODO: should not be hardcoded. Check what already exists. Do not use primitives for this, use something else. Check what already exists
                    heterogeneity=iid_divergence.aggregate,
                    benefit=MetricValue(
                        population_metric(iid_shared, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
                        - population_metric(iid_local, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
                    ),
                )
            )

    if association_observations:
        mechanisms.append(heterogeneity_benefit_association(tuple(association_observations)))

    movement_cohorts: list[ThresholdMovementCohort] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        for concentration in DIRICHLET_CONCENTRATIONS:
            movement_cohorts.append(
                threshold_movements_from_evaluations(
                    shared=_load_heterogeneity_evaluation(
                        seed,
                        FederatedThresholdMethod.SHARED_THRESHOLD,
                        ControlledPartitionKind.DIRICHLET,
                        concentration,
                    ),
                    local=_load_heterogeneity_evaluation(
                        seed,
                        FederatedThresholdMethod.LOCAL_THRESHOLD,
                        ControlledPartitionKind.DIRICHLET,
                        concentration,
                    ),
                    experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
                )
            )
    if movement_cohorts:
        mechanisms.append(
            summarize_threshold_movements_across_seeds(
                tuple(movement_cohorts),
                required_seed_count=CONFIRMATORY_SEED_COHORT.member_count.value,
            )
        )

    if mechanisms:
        export_mechanism_publication(
            tuple(mechanisms),
            experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            output_directory=output,
            evidence_role=EvidenceRole.MECHANISM,
        )
    return output


def analyze_per_client_score_geometry(*, overwrite: bool) -> Path:
    output = (
        OUTPUTS_ROOT
        / MechanismAnalysisDirectory.ROOT
        / ExperimentId.PER_CLIENT_SCORE_GEOMETRY.value
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / MechanismAnalysisDirectory.ANALYSIS
    )
    if overwrite and output.exists():
        from shutil import rmtree

        rmtree(output)

    geometries: list[ScoreGeometryResult] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = _load_confirmatory_evaluation(seed, FederatedThresholdMethod.SHARED_THRESHOLD)
        expected_clients = tuple(sorted(item.client for item in shared.clients))
        if not expected_clients:
            raise ScientificContractError(
                ErrorMessage(f"per-client score geometry requires evaluation clients for seed {seed.value}")
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
        geometries.append(
            score_geometry_from_client_vectors(
                seed=seed,
                source_score_checksum=shared.fixed_score_evidence.evaluation.score_checksum,
                benign_evaluation=benign_eval,
                attack_evaluation=attack_eval,
                threshold_overlays=_score_geometry_threshold_overlays(seed, expected_clients),
                attack_geometry_available=attack_available,
                attack_geometry_reason=None if attack_available else "attack evaluation scores unavailable",
            )
        )

    _persist_score_geometry(tuple(geometries), output / "score_geometry")
    if geometries:
        export_mechanism_publication(
            (),
            experiment=ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output,
            evidence_role=EvidenceRole.MECHANISM,
        )
    return output


def analyze_heterogeneity_benefit_association(*, overwrite: bool) -> Path:
    output = (
        OUTPUTS_ROOT
        / MechanismAnalysisDirectory.ROOT
        / ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION.value
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / MechanismAnalysisDirectory.ANALYSIS
    )
    if overwrite and output.exists():
        from shutil import rmtree

        rmtree(output)

    mechanisms: list[MechanismEvidence] = []
    association_observations: list[AssociationObservation] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = _load_confirmatory_evaluation(seed, FederatedThresholdMethod.SHARED_THRESHOLD)
        local = _load_confirmatory_evaluation(seed, FederatedThresholdMethod.LOCAL_THRESHOLD)
        shared_cv = population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        local_cv = population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION)
        vectors, score_checksum = _client_score_vectors(shared)
        divergence = jensen_shannon_from_client_scores(vectors, source_score_checksum=score_checksum)
        mechanisms.append(divergence)
        if divergence.aggregate is not None:
            association_observations.append(
                AssociationObservation(
                    seed=seed,
                    experiment=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
                    population=PopulationId.NBAIOT_NATURAL_DEVICES,
                    regime_label=f"seed_{seed.value}",
                    heterogeneity=divergence.aggregate,
                    benefit=MetricValue(shared_cv.value - local_cv.value),
                )
            )
    if association_observations:
        mechanisms.append(heterogeneity_benefit_association(tuple(association_observations)))

    if mechanisms:
        export_mechanism_publication(
            tuple(mechanisms),
            experiment=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output,
            evidence_role=EvidenceRole.MECHANISM,
        )
    return output


def analyze_threshold_movement_tradeoff(*, overwrite: bool) -> Path:
    output = (
        OUTPUTS_ROOT
        / MechanismAnalysisDirectory.ROOT
        / ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF.value
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / MechanismAnalysisDirectory.ANALYSIS
    )
    if overwrite and output.exists():
        from shutil import rmtree

        rmtree(output)

    mechanisms: list[MechanismEvidence] = []
    movement_cohorts: list[ThresholdMovementCohort] = []
    for seed in CONFIRMATORY_SEED_COHORT.values:
        shared = _load_confirmatory_evaluation(seed, FederatedThresholdMethod.SHARED_THRESHOLD)
        local = _load_confirmatory_evaluation(seed, FederatedThresholdMethod.LOCAL_THRESHOLD)
        movement = threshold_movements_from_evaluations(
            shared=shared,
            local=local,
            experiment=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        )
        movement_cohorts.append(movement)
        mechanisms.append(movement)
        _verify_auroc_invariance(shared, local)

    mechanisms.append(
        summarize_threshold_movements_across_seeds(
            tuple(movement_cohorts),
            required_seed_count=CONFIRMATORY_SEED_COHORT.member_count.value,
        )
    )

    export_mechanism_publication(
        tuple(mechanisms),
        experiment=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output,
        evidence_role=EvidenceRole.MECHANISM,
    )
    return output


def _verify_auroc_invariance(
    shared: FederatedEvaluationDocument,
    local: FederatedEvaluationDocument,
) -> None:
    shared_auroc = population_metric(shared, MetricId.AUROC)
    local_auroc = population_metric(local, MetricId.AUROC)
    difference = abs(shared_auroc.value - local_auroc.value)
    if difference > FIXED_SCORE_AUROC_INVARIANCE_TOLERANCE.value:
        raise ScientificContractError(
            ErrorMessage(
                "AUROC must be invariant across threshold-only policies; "
                f"shared={shared_auroc.value} local={local_auroc.value} difference={difference}"
            ),
            subject=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        )


def _require_declaration(experiment_id: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    if len(matches) != 1:
        raise ScientificContractError(ErrorMessage(f"experiment must be declared exactly once: {experiment_id.value}"))
    return matches[0]


def _confirmatory_coordinate(training_seed: Seed, method: FederatedThresholdMethod) -> ExperimentCoordinate:
    if method in {FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD}:
        declaration = _require_declaration(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    elif method is FederatedThresholdMethod.CLUSTER_THRESHOLD:
        declaration = _require_declaration(ExperimentId.FAMILY_AND_GROUPED_GRANULARITY)
    else:
        raise ScientificContractError(ErrorMessage(f"cannot resolve confirmatory coordinate for {method.value}"))
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(training_seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(f"evaluation coordinate for {method.value} must resolve exactly once")
        )
    return matches[0]


def _load_confirmatory_evaluation(training_seed: Seed, method: FederatedThresholdMethod) -> FederatedEvaluationDocument:
    coordinate = _confirmatory_coordinate(training_seed, method)
    eval_path = (
        evaluation_run_directory(OUTPUTS_ROOT, coordinate)
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    return load_evaluation_document(eval_path)


def _load_heterogeneity_evaluation(
    training_seed: Seed,
    method: FederatedThresholdMethod,
    partition_kind: ControlledPartitionKind,
    concentration: DirichletConcentration | None,
) -> FederatedEvaluationDocument:
    declaration = _require_declaration(ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(training_seed,)))
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
        and entry.coordinate.controlled_partition_kind is partition_kind
        and (
            (partition_kind is ControlledPartitionKind.IID and entry.coordinate.dirichlet_concentration is None)
            or (
                partition_kind is ControlledPartitionKind.DIRICHLET
                and concentration is not None
                and entry.coordinate.dirichlet_concentration is not None
                and entry.coordinate.dirichlet_concentration.value == concentration.value
            )
        )
    )
    if len(matches) != 1:
        alpha = concentration.value if concentration is not None else None
        raise ScientificContractError(
            ErrorMessage(
                f"heterogeneity evaluation coordinate for {method.value} partition={partition_kind.value} "
                f"alpha={alpha} must resolve exactly once"
            )
        )
    eval_path = (
        evaluation_run_directory(OUTPUTS_ROOT, matches[0])
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    return load_evaluation_document(eval_path)


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
                ErrorMessage(f"missing persisted benign calibration scores for JS divergence: {path}"),
                subject=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            )
        scores = tuple(
            MetricValue(float(value))
            for value in pl.read_parquet(path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
        )
        if not scores:
            raise ScientificContractError(
                ErrorMessage(f"empty calibration score vector for client {client_result.client.client_id}")
            )
        vectors.append(ClientScoreVector(client=client_result.client, scores=scores))
    if len(vectors) < 2:
        raise ScientificContractError(
            ErrorMessage("Jensen-Shannon construction requires at least two client score vectors")
        )
    return tuple(vectors), document.fixed_score_evidence.calibration.score_checksum


def _client_evaluation_scores(
    *,
    score_coordinate: FederatedTrainingCoordinate,
    document_clients: tuple[ClientIdentity, ...],
    expected_clients: tuple[ClientIdentity, ...],
    benign_only: bool,
) -> tuple[
    tuple[ClientIdentity, tuple[MetricValue, ...]], ...
]:  # TODO: should be handled better rather than tuple of tuples. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    from datp_core.data.populations.contracts import PopulationOutcomeLabel

    ordered_document_clients = tuple(sorted(document_clients))
    if frozenset(ordered_document_clients) != frozenset(expected_clients):
        missing = sorted(
            client.client_id for client in expected_clients if client not in frozenset(ordered_document_clients)
        )
        extra = sorted(
            client.client_id for client in ordered_document_clients if client not in frozenset(expected_clients)
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
    pairs: list[tuple[ClientIdentity, tuple[MetricValue, ...]]] = []
    benign_label = PopulationOutcomeLabel.BENIGN.value
    for client in expected_clients:
        path = score_root / client.client_id / FederatedScoreAssetName.EVALUATION.value
        if not path.is_file():
            raise ScientificContractError(
                ErrorMessage(f"missing evaluation score parquet for client {client.client_id}: {path}")
            )
        frame = pl.read_parquet(path)
        score_column = ScoreFrameColumn.RECONSTRUCTION_ERROR.value
        label_column = ScoreFrameColumn.OUTCOME_LABEL.value
        if score_column not in frame.columns:
            raise ScientificContractError(
                ErrorMessage(f"missing reconstruction_error column for client {client.client_id}: {path}")
            )
        if label_column not in frame.columns:
            raise ScientificContractError(
                ErrorMessage(f"missing outcome_label column for client {client.client_id}: {path}")
            )
        scores_raw = frame.get_column(score_column).to_list()
        labels = frame.get_column(label_column).to_list()
        if len(scores_raw) != len(labels):
            raise ScientificContractError(
                ErrorMessage(f"score and label columns are misaligned for client {client.client_id}: {path}")
            )
        scores = tuple(
            MetricValue(float(score))
            for score, label in zip(scores_raw, labels, strict=True)
            if (str(label) == benign_label) is benign_only
        )
        pairs.append((client, scores))
    return tuple(pairs)


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
            document = _load_confirmatory_evaluation(seed, method)
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


def _persist_score_geometry(
    geometries: tuple[ScoreGeometryResult, ...],
    output_directory: Path,
) -> None:
    from datp_core.artifacts.serializers.json import serialize_json_model

    output_directory.mkdir(parents=True, exist_ok=True)
    for geometry in geometries:
        serialize_json_model(geometry, output_directory / f"seed_{geometry.seed.value}.json")
