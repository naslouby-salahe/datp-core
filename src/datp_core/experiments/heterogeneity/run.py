"""Controlled heterogeneity sweep and mechanism experiment execution.

The controlled heterogeneity sweep executes training on the declared Dirichlet
populations. Score geometry, heterogeneity-benefit association, and threshold
movement analyses reuse frozen confirmatory score artifacts.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.analysis.mechanisms import (
    AssociationObservation,
    AssociationResult,
    ClientScoreVector,
    MechanismEvidence,
    ThresholdMovement,
    ThresholdMovementCohort,
    heterogeneity_benefit_association,
    jensen_shannon_from_client_scores,
    summarize_threshold_movements_across_seeds,
    threshold_movements_from_evaluations,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.protocols import FIXED_SCORE_AUROC_INVARIANCE_TOLERANCE
from datp_core.app.planning import PlanReason, expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    FigureLabel,
    FigureTitle,
    MetricId,
    PopulationId,
    RegimeLabel,
    ScoreFrameColumn,
)
from datp_core.core.numeric import DirichletConcentration, MetricValue, Seed
from datp_core.data.nbaiot.schema import NBaIoTDevice
from datp_core.data.populations.contracts import ControlledPartitionKind
from datp_core.data.populations.declarations import DIRICHLET_CONCENTRATIONS
from datp_core.detector.scoring.models import FederatedScoreAssetName
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.confirmatory.run import build_confirmatory_score_geometry, persist_score_geometry
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.evidence import load_evaluation_document, population_metric
from datp_core.experiments.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    federated_training_directory,
)
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.presentation.export import export_mechanism_publication
from datp_core.presentation.figures import FigureSpec, PairedMetricFigureSeries
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
        reason=PlanReason("controlled heterogeneity sweep executes the locked Dirichlet population grid"),
        output_root=output_root,
        overwrite=overwrite,
    )
    return HeterogeneitySweepSeedResult(
        training_seed=training_seed,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def _collect_heterogeneity_mechanisms() -> tuple[MechanismEvidence, ...]:
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
    return tuple(mechanisms)


def _collect_heterogeneity_associations() -> tuple[AssociationObservation, ...]:
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
                        regime_label=RegimeLabel(f"alpha_{concentration.value}"),
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
                    regime_label=RegimeLabel(ControlledPartitionKind.IID.value),
                    heterogeneity=iid_divergence.aggregate,
                    benefit=MetricValue(
                        population_metric(iid_shared, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
                        - population_metric(iid_local, MetricId.FPR_COEFFICIENT_OF_VARIATION).value
                    ),
                )
            )
    return tuple(association_observations)


def _collect_heterogeneity_movement_cohorts() -> tuple[ThresholdMovementCohort, ...]:
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
    return tuple(movement_cohorts)


def _controlled_heterogeneity_figures(
    observations: tuple[AssociationObservation, ...],
) -> tuple[FigureSpec, ...]:
    """Publish every declared severity/seed value, rather than a smoothed summary."""
    x_label = FigureLabel("locked benign-calibration Jensen-Shannon divergence")
    y_label = FigureLabel("shared-local CV(FPR) gain")
    by_regime: dict[RegimeLabel, list[AssociationObservation]] = {}
    for observation in observations:
        by_regime.setdefault(observation.regime_label, []).append(observation)
    if not by_regime:
        series = (
            PairedMetricFigureSeries(
                label=FigureLabel("no valid controlled heterogeneity observations"),
                x_label=x_label,
                y_label=y_label,
                availability=AvailabilityStatus.UNAVAILABLE,
                x_values=(),
                y_values=(),
                unavailable_reason=AnalysisReasonText("no valid controlled heterogeneity observations"),
            ),
        )
    else:
        series = tuple(
            PairedMetricFigureSeries(
                label=FigureLabel(str(regime)),
                x_label=x_label,
                y_label=y_label,
                availability=AvailabilityStatus.AVAILABLE,
                x_values=tuple(item.heterogeneity for item in ordered),
                y_values=tuple(item.benefit for item in ordered),
                point_labels=tuple(FigureLabel(f"seed_{item.seed.value}") for item in ordered),
            )
            for regime, values in sorted(by_regime.items(), key=lambda item: str(item[0]))
            for ordered in (tuple(sorted(values, key=lambda item: item.seed.value)),)
        )
    return (
        FigureSpec(
            title=FigureTitle(
                "Controlled non-IID seed distributions: Jensen-Shannon heterogeneity versus CV(FPR) gain"
            ),
            paired_metric_series=series,
        ),
    )


def _association_figure(result: AssociationResult) -> FigureSpec:
    x_label = FigureLabel("locked benign-calibration Jensen-Shannon divergence")
    y_label = FigureLabel("shared-local CV(FPR) gain")
    ordered = tuple(sorted(result.observations, key=lambda item: (item.seed.value, str(item.regime_label))))
    if not ordered:
        raw_series = PairedMetricFigureSeries(
            label=FigureLabel("valid regime/seed observations"),
            x_label=x_label,
            y_label=y_label,
            availability=AvailabilityStatus.UNAVAILABLE,
            x_values=(),
            y_values=(),
            unavailable_reason=result.reason or AnalysisReasonText("no valid association observations"),
        )
    else:
        raw_series = PairedMetricFigureSeries(
            label=FigureLabel("valid regime/seed observations"),
            x_label=x_label,
            y_label=y_label,
            availability=AvailabilityStatus.AVAILABLE,
            x_values=tuple(item.heterogeneity for item in ordered),
            y_values=tuple(item.benefit for item in ordered),
            point_labels=tuple(FigureLabel(f"{item.regime_label}:seed_{item.seed.value}") for item in ordered),
        )
    if result.statistics is None or not ordered:
        regression_series = PairedMetricFigureSeries(
            label=FigureLabel("pre-specified descriptive regression"),
            x_label=x_label,
            y_label=y_label,
            availability=AvailabilityStatus.UNAVAILABLE,
            x_values=(),
            y_values=(),
            unavailable_reason=result.reason or AnalysisReasonText("descriptive regression is unavailable"),
        )
    else:
        regression_x = tuple(sorted((item.heterogeneity for item in ordered), key=lambda item: item.value))
        regression_series = PairedMetricFigureSeries(
            label=FigureLabel("pre-specified descriptive regression"),
            x_label=x_label,
            y_label=y_label,
            availability=AvailabilityStatus.AVAILABLE,
            x_values=regression_x,
            y_values=tuple(
                MetricValue(
                    result.statistics.regression_intercept.value
                    + result.statistics.regression_slope.value * value.value
                )
                for value in regression_x
            ),
            point_labels=tuple(FigureLabel("fitted") for _ in regression_x),
        )
    return FigureSpec(
        title=FigureTitle("Heterogeneity–benefit association: observed points and descriptive regression"),
        paired_metric_series=(raw_series, regression_series),
    )


def _threshold_movement_figures(
    cohorts: tuple[ThresholdMovementCohort, ...],
) -> tuple[FigureSpec, ...]:
    movements = tuple(movement for cohort in cohorts for movement in cohort.movements)
    _require_complete_natural_device_movement_coverage(movements)
    return (
        _threshold_movement_figure(
            movements,
            title=FigureTitle("Threshold shift versus FPR change (all N-BaIoT devices and seeds)"),
            y_label=FigureLabel("local-minus-shared false-positive-rate change"),
            value_for=lambda movement: movement.delta_fpr,
            unavailable_reason=AnalysisReasonText("FPR movement is unavailable"),
        ),
        _threshold_movement_figure(
            movements,
            title=FigureTitle("Threshold shift versus TPR change (all N-BaIoT devices and seeds)"),
            y_label=FigureLabel("local-minus-shared true-positive-rate change"),
            value_for=lambda movement: movement.delta_tpr,
            unavailable_reason=AnalysisReasonText("attack-sensitive TPR movement is unavailable"),
        ),
    )


def _threshold_movement_figure(
    movements: tuple[ThresholdMovement, ...],
    *,
    title: FigureTitle,
    y_label: FigureLabel,
    value_for: Callable[[ThresholdMovement], MetricValue | None],
    unavailable_reason: AnalysisReasonText,
) -> FigureSpec:
    x_label = FigureLabel("local-minus-shared threshold shift")
    if not movements:
        return FigureSpec(
            title=title,
            paired_metric_series=(
                PairedMetricFigureSeries(
                    label=FigureLabel("no threshold movement observations"),
                    x_label=x_label,
                    y_label=y_label,
                    availability=AvailabilityStatus.UNAVAILABLE,
                    x_values=(),
                    y_values=(),
                    unavailable_reason=AnalysisReasonText("no threshold movement observations"),
                ),
            ),
        )
    series: list[PairedMetricFigureSeries] = []
    for movement in movements:
        value = value_for(movement)
        label = FigureLabel(f"{movement.client.client_id.value}:seed_{movement.seed.value}")
        if value is None:
            series.append(
                PairedMetricFigureSeries(
                    label=label,
                    x_label=x_label,
                    y_label=y_label,
                    availability=AvailabilityStatus.UNAVAILABLE,
                    x_values=(),
                    y_values=(),
                    unavailable_reason=unavailable_reason,
                )
            )
            continue
        series.append(
            PairedMetricFigureSeries(
                label=label,
                x_label=x_label,
                y_label=y_label,
                availability=AvailabilityStatus.AVAILABLE,
                x_values=(movement.delta_threshold,),
                y_values=(value,),
                point_labels=(FigureLabel(movement.client.client_id.value),),
            )
        )
    return FigureSpec(title=title, paired_metric_series=tuple(series))


def _require_complete_natural_device_movement_coverage(movements: tuple[ThresholdMovement, ...]) -> None:
    expected = frozenset(device.value for device in NBaIoTDevice)
    by_seed: dict[Seed, set[str]] = {}
    for movement in movements:
        by_seed.setdefault(movement.seed, set()).add(movement.client.client_id.value)
    for seed, observed in by_seed.items():
        observed_ids = frozenset(observed)
        if observed_ids != expected:
            raise ScientificContractError(
                ErrorMessage(
                    "threshold-movement figure must retain every declared natural device "
                    f"for seed {seed.value}; missing={sorted(expected - observed_ids)} "
                    f"extra={sorted(observed_ids - expected)}"
                )
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

    mechanisms = list(_collect_heterogeneity_mechanisms())

    associations = _collect_heterogeneity_associations()
    if associations:
        mechanisms.append(heterogeneity_benefit_association(associations))
    figures = _controlled_heterogeneity_figures(associations)

    movements = _collect_heterogeneity_movement_cohorts()
    if movements:
        mechanisms.append(
            summarize_threshold_movements_across_seeds(
                movements,
                required_seed_count=CONFIRMATORY_SEED_COHORT.member_count,
            )
        )

    if mechanisms:
        export_mechanism_publication(
            tuple(mechanisms),
            experiment=ExperimentId.CONTROLLED_HETEROGENEITY_SWEEP,
            population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            output_directory=output,
            evidence_role=EvidenceRole.MECHANISM,
            figures=figures,
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

    geometries, figures = build_confirmatory_score_geometry()
    persist_score_geometry(geometries, output / "score_geometry")
    if geometries:
        export_mechanism_publication(
            (),
            experiment=ExperimentId.PER_CLIENT_SCORE_GEOMETRY,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output,
            evidence_role=EvidenceRole.MECHANISM,
            figures=figures,
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
                    regime_label=RegimeLabel(f"seed_{seed.value}"),
                    heterogeneity=divergence.aggregate,
                    benefit=MetricValue(shared_cv.value - local_cv.value),
                )
            )
    association = heterogeneity_benefit_association(tuple(association_observations))
    mechanisms.append(association)

    if mechanisms:
        export_mechanism_publication(
            tuple(mechanisms),
            experiment=ExperimentId.HETEROGENEITY_BENEFIT_ASSOCIATION,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            output_directory=output,
            evidence_role=EvidenceRole.MECHANISM,
            figures=(_association_figure(association),),
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
            required_seed_count=CONFIRMATORY_SEED_COHORT.member_count,
        )
    )

    export_mechanism_publication(
        tuple(mechanisms),
        experiment=ExperimentId.THRESHOLD_MOVEMENT_TRADEOFF,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output,
        evidence_role=EvidenceRole.MECHANISM,
        figures=_threshold_movement_figures(tuple(movement_cohorts)),
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
                ErrorMessage(f"empty calibration score vector for client {client_result.client.client_id.value}")
            )
        vectors.append(ClientScoreVector(client=client_result.client, scores=scores))
    if len(vectors) < 2:
        raise ScientificContractError(
            ErrorMessage("Jensen-Shannon construction requires at least two client score vectors")
        )
    return tuple(vectors), document.fixed_score_evidence.calibration.score_checksum
