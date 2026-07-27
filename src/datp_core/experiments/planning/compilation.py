"""Compile an experiment by resolving all configuration references once.

Phase 2 of the DATP-Core simplification roadmap: ``CompiledExperiment`` holds
every referenced record from ``ResolvedProjectConfiguration`` so that downstream
planning and execution never navigate the configuration registry directly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from datp_core.config.models import ResolvedProjectConfiguration
from datp_core.config.report_profiles import ReportProfileRecord
from datp_core.core.identifiers import DatasetId, ExperimentId
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.data.contracts.eligibility import EligibilityPolicyRecord
from datp_core.evaluation.definitions.bundles import MetricBundleRecord
from datp_core.experiments.catalogue.analyses import AnalysisRecord
from datp_core.experiments.catalogue.evaluations import EvaluationSpecRecord
from datp_core.experiments.catalogue.models import ExperimentRecord, PopulationRecord
from datp_core.learning.contracts.checkpoints import CheckpointProfileRecord
from datp_core.learning.contracts.seeds import SeedCohortRecord
from datp_core.learning.contracts.training import TrainingProfileRecord
from datp_core.thresholding import ThresholdPolicyRecord


@dataclass(frozen=True, slots=True)
class CompiledEvaluation:
    """One evaluation with all configuration references resolved.

    ``population``, ``threshold_policy``, and ``metric_bundle`` are guaranteed
    to exist in the configuration registries.
    """

    record: EvaluationSpecRecord
    population: PopulationRecord
    threshold_policy: ThresholdPolicyRecord
    metric_bundle: MetricBundleRecord


@dataclass(frozen=True, slots=True)
class CompiledExperiment:
    """One experiment with all configuration references resolved once.

    Every referenced record is guaranteed to exist in the configuration
    registries.  Downstream code consumes these resolved records directly
    instead of navigating ``ResolvedProjectConfiguration`` by ID.
    """

    record: ExperimentRecord
    populations: tuple[PopulationRecord, ...]
    training_profile: TrainingProfileRecord
    checkpoint_profile: CheckpointProfileRecord
    seed_cohort: SeedCohortRecord
    eligibility_policy: EligibilityPolicyRecord
    evaluations: tuple[CompiledEvaluation, ...]
    analyses: tuple[AnalysisRecord, ...]
    report_profiles: tuple[ReportProfileRecord, ...]
    datasets: Mapping[DatasetId, ResolvedDataset]


def _compile_evaluation(
    config: ResolvedProjectConfiguration,
    experiment: ExperimentRecord,
    evaluation: EvaluationSpecRecord,
) -> CompiledEvaluation:
    """Resolve all configuration references for a single evaluation."""
    population_id = evaluation.population_id
    if population_id is None:
        if not experiment.population_ids:
            raise ValueError(
                f"Experiment '{experiment.identifier.value}' has no populations, "
                f"but evaluation '{evaluation.label}' requires a default population"
            )
        population_id = experiment.population_ids[0]

    try:
        population = config.populations.get(population_id)
    except KeyError as err:
        raise KeyError(
            f"Evaluation '{evaluation.label}' in experiment "
            f"'{experiment.identifier.value}' references unknown population "
            f"'{population_id.value}'"
        ) from err

    try:
        threshold_policy = config.threshold_policies.get(evaluation.threshold_policy_id)
    except KeyError as err:
        raise KeyError(
            f"Evaluation '{evaluation.label}' in experiment "
            f"'{experiment.identifier.value}' references unknown threshold policy "
            f"'{evaluation.threshold_policy_id.value}'"
        ) from err

    try:
        metric_bundle = config.metric_bundles.get(population.metric_bundle_id)
    except KeyError as err:
        raise KeyError(
            f"Evaluation '{evaluation.label}' in experiment "
            f"'{experiment.identifier.value}' references population "
            f"'{population_id.value}' with unknown metric bundle "
            f"'{population.metric_bundle_id.value}'"
        ) from err

    return CompiledEvaluation(
        record=evaluation,
        population=population,
        threshold_policy=threshold_policy,
        metric_bundle=metric_bundle,
    )


def compile_experiment(
    config: ResolvedProjectConfiguration,
    experiment_id: ExperimentId,
) -> CompiledExperiment:
    """Resolve all configuration references for one experiment.

    Performs eager lookup of every ID referenced by the experiment and its
    evaluations, failing fast on missing or unresolvable references.

    Args:
        config: The resolved project configuration.
        experiment_id: The identifier of the experiment to compile.

    Returns:
        An immutable ``CompiledExperiment`` with all references resolved.

    Raises:
        KeyError: If any referenced ID is not found in the configuration
            registries.
        ValueError: If the experiment has no populations and an evaluation
            requires a default.
    """
    try:
        experiment = config.experiments.get(experiment_id)
    except KeyError as err:
        raise KeyError(f"Experiment '{experiment_id.value}' not found in configuration") from err

    # Resolve direct record references ----------------------------------------

    try:
        training_profile = config.training_profiles.get(experiment.training_profile_id)
    except KeyError as err:
        raise KeyError(
            f"Experiment '{experiment_id.value}' references unknown training "
            f"profile '{experiment.training_profile_id.value}'"
        ) from err

    try:
        checkpoint_profile = config.checkpoint_profiles.get(experiment.checkpoint_profile_id)
    except KeyError as err:
        raise KeyError(
            f"Experiment '{experiment_id.value}' references unknown checkpoint "
            f"profile '{experiment.checkpoint_profile_id.value}'"
        ) from err

    try:
        seed_cohort = config.seed_cohorts.get(experiment.seed_cohort_id)
    except KeyError as err:
        raise KeyError(
            f"Experiment '{experiment_id.value}' references unknown seed cohort '{experiment.seed_cohort_id.value}'"
        ) from err

    try:
        eligibility_policy = config.eligibility_policies.get(experiment.eligibility_policy_id)
    except KeyError as err:
        raise KeyError(
            f"Experiment '{experiment_id.value}' references unknown eligibility "
            f"policy '{experiment.eligibility_policy_id.value}'"
        ) from err

    # Resolve populations -----------------------------------------------------

    populations: list[PopulationRecord] = []
    for pid in experiment.population_ids:
        try:
            population = config.populations.get(pid)
        except KeyError as err:
            raise KeyError(f"Experiment '{experiment_id.value}' references unknown population '{pid.value}'") from err
        populations.append(population)

    # Resolve datasets --------------------------------------------------------

    datasets: dict[DatasetId, ResolvedDataset] = {}
    for population in populations:
        if population.dataset_id in datasets:
            continue
        try:
            dataset = config.datasets.get(population.dataset_id)
        except KeyError as err:
            raise KeyError(
                f"Experiment '{experiment_id.value}' references population "
                f"'{population.identifier.value}' with unknown dataset "
                f"'{population.dataset_id.value}'"
            ) from err
        datasets[population.dataset_id] = dataset

    # Resolve evaluations -----------------------------------------------------

    evaluations = tuple(_compile_evaluation(config, experiment, evaluation) for evaluation in experiment.evaluations)

    # Resolve report profiles -------------------------------------------------

    report_profiles: list[ReportProfileRecord] = []
    for rid in experiment.report_ids:
        try:
            profile = config.report_profiles.get(rid)
        except KeyError as err:
            raise KeyError(f"Experiment '{experiment_id.value}' references unknown report profile '{rid}'") from err
        report_profiles.append(profile)

    return CompiledExperiment(
        record=experiment,
        populations=tuple(populations),
        training_profile=training_profile,
        checkpoint_profile=checkpoint_profile,
        seed_cohort=seed_cohort,
        eligibility_policy=eligibility_policy,
        evaluations=evaluations,
        analyses=experiment.analyses,
        report_profiles=tuple(report_profiles),
        datasets=datasets,
    )
