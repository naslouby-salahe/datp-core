from datp_core.app.planning import PlanDisposition, PlanningEvidence, PlanReason, expand_experiment_plan
from datp_core.core.identifiers import (
    DatasetId,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.core.numeric import Seed
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.registry import ExperimentDeclaration


def test_plan_expansion_is_deterministic_and_records_complete_coordinates() -> None:
    declaration = ExperimentDeclaration(
        id=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        role=EvidenceRole.CONFIRMATORY,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        federated_thresholds=(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
        metrics=(MetricId.FPR_COEFFICIENT_OF_VARIATION,),
        readiness=ExperimentReadiness.DECLARED,
    )
    evidence = (
        PlanningEvidence(
            experiment=declaration.id,
            disposition=PlanDisposition.EXECUTABLE,
            reason=PlanReason("all prerequisites validated"),
        ),
    )
    first = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0), Seed(1))),
        evidence=evidence,
    )
    second = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0), Seed(1))),
        evidence=evidence,
    )
    assert first == second
    assert len(first.entries) == 4
    assert all(entry.disposition is PlanDisposition.EXECUTABLE for entry in first.entries)
    assert all(entry.coordinate.evidence_role is EvidenceRole.CONFIRMATORY for entry in first.entries)
    assert all(entry.coordinate.dataset is DatasetId.NBAIOT for entry in first.entries)
    assert all(entry.coordinate.split_protocol is SplitProtocolId.HISTORICAL_TEMPORAL_GAP for entry in first.entries)
    assert all(entry.coordinate.temporal_state is None for entry in first.entries)


def test_temporal_plan_uses_state_specific_split_protocols() -> None:
    declaration = ExperimentDeclaration(
        id=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        role=EvidenceRole.TEMPORAL_BOUNDARY,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.FPR_COEFFICIENT_OF_VARIATION,),
        readiness=ExperimentReadiness.DECLARED,
    )

    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
    )

    by_state = {entry.coordinate.temporal_state: entry.coordinate for entry in plan.entries}
    assert frozenset(by_state) == frozenset(
        (
            TemporalState.STATIC_REFERENCE,
            TemporalState.FROZEN_FUTURE,
            TemporalState.RECALIBRATED_FUTURE,
        )
    )
    assert all(coordinate.dataset is DatasetId.EDGE_IIOTSET for coordinate in by_state.values())
    assert by_state[TemporalState.STATIC_REFERENCE].split_protocol is SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE
    assert by_state[TemporalState.FROZEN_FUTURE].split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    assert by_state[TemporalState.RECALIBRATED_FUTURE].split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE


def test_planning_cannot_override_population_threshold_capabilities() -> None:
    declaration = ExperimentDeclaration(
        id=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
        role=EvidenceRole.APPLICABILITY_BOUNDARY,
        population=PopulationId.CICIOT_FILE_CLIENTS,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        federated_thresholds=(FederatedThresholdMethod.FAMILY_THRESHOLD,),
        metrics=(MetricId.FPR_COEFFICIENT_OF_VARIATION,),
        readiness=ExperimentReadiness.DECLARED,
    )
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("caller claims the campaign is executable"),
            ),
        ),
    )

    assert len(plan.entries) == 1
    assert plan.entries[0].disposition is PlanDisposition.INFEASIBLE
    assert "threshold_method_unsupported" in plan.entries[0].reason


def test_plan_expands_each_declared_preprocessing_protocol() -> None:
    declaration = ExperimentDeclaration(
        id=ExperimentId.PREPROCESSING_GEOMETRY_SENSITIVITY,
        role=EvidenceRole.SUPPORTIVE,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_model=TrainingModelId.FEDAVG_AUTOENCODER,
        preprocessing_protocol=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        supplementary_preprocessing_protocols=(PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,),
        federated_thresholds=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        metrics=(MetricId.FPR_COEFFICIENT_OF_VARIATION,),
        readiness=ExperimentReadiness.DECLARED,
    )

    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(Seed(0),)))

    assert tuple(entry.coordinate.preprocessing_protocol for entry in plan.entries) == (
        PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        PreprocessingProtocolId.FEDERATED_POOLED_MIN_MAX,
    )
