"""Paired-analysis sweep-cell expansion: every supported sweep axis, and the no-sweep default."""

from __future__ import annotations

from attrs import evolve

from datp_core.analysis.execution.plan import (
    PairedAnalysisCell,
    expand_paired_analysis_cells,
    resolve_sweep_dimensions,
)
from datp_core.core.identifiers import (
    CheckpointProfileId,
    EligibilityPolicyId,
    ExperimentId,
    SeedCohortId,
    StatisticalProfileId,
    TrainingProfileId,
)
from datp_core.experiments.models import (
    ConditionSweepRecord,
    EvidenceRole,
    ExperimentRecord,
    PairedThresholdAnalysisRecord,
    RunRequirement,
    SweepConditionAllocation,
    SweepConditionRecord,
    ValueSweepRecord,
)
from datp_core.learning.models import (
    CheckpointAuthorization,
    PersonalizationStrategy,
    TrainingProfileKind,
    TrainingProfileRecord,
)

_ANALYSIS = PairedThresholdAnalysisRecord(
    label="test_analysis",
    kind="paired_threshold_analysis",
    result_type="delta",
    statistical_profile=StatisticalProfileId("paired_seed_bca"),
    secondary_statistical_profile=None,
    first_evaluation="first",
    second_evaluation="second",
    primary_metric="cv_fpr",
    delta_orientation="first_minus_second",
    delta_interpretation="lower_is_better",
    required_direction=None,
    monotonicity_required=None,
    ordering_inversion_reporting=None,
    per_sweep_cell=None,
    full_curve_reporting=None,
    post_hoc_weight_selection=None,
)


def _training_profile(
    *, personalization: PersonalizationStrategy = PersonalizationStrategy.NONE, grid: tuple[float, ...] | None = None
) -> TrainingProfileRecord:
    return TrainingProfileRecord(
        identifier=TrainingProfileId("profile"),
        kind=TrainingProfileKind.FEDERATED_AVERAGING_TRAINING,
        model_architecture_id="arch",
        optimizer_id="optimizer",
        batching_profile_id="batching",
        local_epochs=None,
        participation=None,
        checkpoint_authorization=CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE,
        personalization=personalization,
        personalized_local_epochs=None,
        personalization_parameter_grid=grid,
        proximal_objective=None,
        mu_grid=None,
        mu_zero_forbidden_as_a_fedprox_condition=None,
        federation=None,
    )


def _experiment(**overrides: object) -> ExperimentRecord:
    defaults: dict[str, object] = dict(
        identifier=ExperimentId("experiment"),
        display_name="Experiment",
        evidence_role=EvidenceRole.EXPLORATORY,
        run_requirement=RunRequirement.OPTIONAL,
        population_ids=(),
        training_profile_id=TrainingProfileId("profile"),
        checkpoint_profile_id=CheckpointProfileId("checkpoint"),
        seed_cohort_id=SeedCohortId("cohort"),
        eligibility_policy_id=EligibilityPolicyId("eligibility"),
        prerequisites=(),
        capability_requirements=(),
        evaluations=(),
        analyses=(_ANALYSIS,),
        report_ids=(),
        sweeps=(),
        readiness_gates=(),
        validation_scope=None,
        never_promoted_to_confirmatory=None,
        outside_core_causal_ladder=None,
        faithful_reproduction_claim_forbidden=None,
        attack_sensitive_metrics_requested=None,
        unavailable_capability_reporting=(),
        independent_of_experiment=None,
        calibration_subset=None,
        method_naming_rule=None,
        personalization_parameter_selection_source=None,
        run_condition=None,
        unavailable_behavior=None,
        blocks_other_experiments_when_unavailable=None,
        estimate_basis=None,
        client_semantics_constraint=None,
        generalization_constraint=None,
        quantitative_claim_gate=None,
        population_equivalence_requirement=None,
        population_roles=None,
        scope_constraint=None,
        training_overrides=None,
        temporal_procedure=None,
        primary_coefficient_selection=None,
    )
    defaults.update(overrides)
    return ExperimentRecord(**defaults)  # pyright: ignore[reportArgumentType]


def test_no_sweeps_configured_yields_a_single_cell_of_none_dimensions() -> None:
    dimensions = resolve_sweep_dimensions(_experiment(), _training_profile())
    cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert cells == (
        PairedAnalysisCell(
            partition_condition=None,
            proximal_mu=None,
            ditto_weight=None,
            threshold_quantile=None,
            shrinkage_weight=None,
            calibration_sample_count=None,
        ),
    )


def test_condition_sweep_axis_expands_one_cell_per_condition() -> None:
    sweep = ConditionSweepRecord(
        name="partition",
        conditions=(
            SweepConditionRecord(name="iid", allocation=SweepConditionAllocation.DIRICHLET, dirichlet_alpha=100.0),
            SweepConditionRecord(name="skewed", allocation=SweepConditionAllocation.DIRICHLET, dirichlet_alpha=0.1),
        ),
    )
    dimensions = resolve_sweep_dimensions(_experiment(sweeps=(sweep,)), _training_profile())
    cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert [cell.partition_condition for cell in cells] == ["iid", "skewed"]


def test_proximal_mu_sweep_axis_reads_the_named_value_sweep() -> None:
    sweep = ValueSweepRecord(name="mu_values", values=(0.01, 0.1, 1.0))
    experiment = _experiment(sweeps=(sweep,), training_overrides={"mu": {"from_sweep": "mu_values"}})
    dimensions = resolve_sweep_dimensions(experiment, _training_profile())
    cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert [cell.proximal_mu for cell in cells] == [0.01, 0.1, 1.0]


def test_ditto_weight_sweep_axis_comes_from_the_training_profile_grid() -> None:
    profile = _training_profile(personalization=PersonalizationStrategy.DITTO, grid=(0.1, 0.5))
    dimensions = resolve_sweep_dimensions(_experiment(), profile)
    cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert [cell.ditto_weight for cell in cells] == [0.1, 0.5]


def test_threshold_quantile_sweep_axis_reads_the_conventionally_named_value_sweep() -> None:
    sweep = ValueSweepRecord(name="threshold_quantile", values=(0.9, 0.95))
    dimensions = resolve_sweep_dimensions(_experiment(sweeps=(sweep,)), _training_profile())
    cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert [cell.threshold_quantile for cell in cells] == [0.9, 0.95]


def test_shrinkage_weight_sweep_axis_reads_the_conventionally_named_value_sweep() -> None:
    sweep = ValueSweepRecord(name="shrinkage_weight", values=(0.0, 0.5))
    dimensions = resolve_sweep_dimensions(_experiment(sweeps=(sweep,)), _training_profile())
    cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert [cell.shrinkage_weight for cell in cells] == [0.0, 0.5]


def test_calibration_sample_count_axis_only_applies_when_the_analysis_opts_in() -> None:
    analysis = evolve(_ANALYSIS, per_sweep_cell="calibration_sample_count")
    dimensions = evolve(
        resolve_sweep_dimensions(_experiment(), _training_profile()), calibration_sample_count_values=(5, 10)
    )
    opted_in_cells = expand_paired_analysis_cells(analysis, dimensions)
    assert [cell.calibration_sample_count for cell in opted_in_cells] == [5, 10]
    unrelated_cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert [cell.calibration_sample_count for cell in unrelated_cells] == [None]


def test_multiple_sweep_axes_form_the_full_cartesian_product() -> None:
    condition_sweep = ConditionSweepRecord(
        name="partition",
        conditions=(
            SweepConditionRecord(name="iid", allocation=SweepConditionAllocation.DIRICHLET, dirichlet_alpha=100.0),
        ),
    )
    quantile_sweep = ValueSweepRecord(name="threshold_quantile", values=(0.9, 0.95))
    dimensions = resolve_sweep_dimensions(_experiment(sweeps=(condition_sweep, quantile_sweep)), _training_profile())
    cells = expand_paired_analysis_cells(_ANALYSIS, dimensions)
    assert len(cells) == 2
    assert {cell.threshold_quantile for cell in cells} == {0.9, 0.95}
