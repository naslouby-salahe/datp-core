from collections.abc import Callable
from dataclasses import fields, replace
from decimal import Decimal

import pytest

from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedModelIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
    FeatureSchemaIdentity,
    PartitionIdentity,
    SplitIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.datasets import Dataset, DatasetSpec, Regime
from datp_core.domain.data.partitioning import ClientDefinitionStrategy, NaturalDevicePartitionSpec
from datp_core.domain.data.preprocessing import (
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
    PreprocessingSpec,
)
from datp_core.domain.data.splitting import (
    BenignCalibrationSplitSpec,
    SplitCollectionSpec,
    TestSplitSpec,
    TrainingSplitSpec,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import (
    BootstrapResampleCount,
    CitedTrafficRateEvidence,
    TrafficRate,
    TrafficRateUnit,
)
from datp_core.domain.evaluation.metrics import METRIC_SPECS, MetricSpec, OperatingPointMetric
from datp_core.domain.evaluation.operating_points import AlertBurdenEvaluationSuiteSpec, StandardEvaluationSuiteSpec
from datp_core.domain.evaluation.statistical_results import (
    ClaimOutcome,
    ConfidenceLevel,
    StatisticalAnalysisSpec,
    StatisticalMethod,
)
from datp_core.domain.experiments.claims import ClaimTier, ExecutionStatus, ExperimentRole
from datp_core.domain.experiments.feasibility import FeasibilityStatus
from datp_core.domain.experiments.identities import ArchitectureCatalogueId, ExperimentId, ExperimentIdentity
from datp_core.domain.experiments.protocols import (
    ProtocolTrack,
    ReportingPolicy,
    ScientificProtocolField,
    ScientificProtocolSpec,
    policy_field_names,
)
from datp_core.domain.experiments.specifications import (
    CONFORMAL_ALPHA,
    ArtifactDependencySpec,
    CentralizedModelComparatorProfileSpec,
    CentralizedModelComparatorSpec,
    ConfirmatoryExperimentProfileSpec,
    FallbackPolicySpec,
    ManuscriptPlacement,
    ManuscriptRoleSpec,
    RegimeCompatibilitySpec,
    SweepAxis,
    SweepSpec,
)
from datp_core.domain.learning.checkpoints import (
    EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE,
    REGIME_A_SELECTION_RULE_VERSION,
    CheckpointSchedule,
    CheckpointSelectionSpec,
    CheckpointSelectionStrategy,
)
from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.scores import QuantileEstimatorType, ScoreGenerationSpec, ScoringBatchSpec
from datp_core.domain.learning.training import (
    AggregationStrategy,
    ClientBatchPartitioning,
    DeterminismLevel,
    FederationSpec,
    LrSchedulerType,
    ModelPersonalizationStrategy,
    OptimizerStepSemantics,
    OptimizerType,
    ParticipationStrategy,
    PrecisionMode,
    TrainingBatchSpec,
    TrainingSpec,
)
from datp_core.domain.runtime.admissibility import BatchSize, ChunkRowCount, GradientAccumulationSteps
from datp_core.domain.runtime.policies import PipelineStage
from datp_core.domain.runtime.seeds import EnumMap, RoundNumber, Seed, SeedTuple
from datp_core.domain.thresholding.policies import (
    FamilyThresholdSpec,
    LocalThresholdSpec,
    SharedThresholdConstruction,
    SharedThresholdSpec,
    ThresholdConstructionKind,
    ThresholdPercentile,
    ThresholdSuiteSpec,
)
from datp_core.domain.thresholding.variants import (
    RobustClusterMedianThresholdSpec,
    ShrinkageThresholdSpec,
    ShrinkageWeight,
)

type NonConfirmatoryConstruction = FamilyThresholdSpec | RobustClusterMedianThresholdSpec | ShrinkageThresholdSpec


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _metric(metric: OperatingPointMetric):
    return next(specification for specification in METRIC_SPECS if specification.metric is metric)


def _protocol() -> ScientificProtocolSpec:
    batch = BatchSize(value=8)
    return ScientificProtocolSpec(
        track=ProtocolTrack.DATP_ANCHOR,
        dataset=_dataset_specification(),
        partitioning=_partition_specification(),
        splits=_split_collection(),
        preprocessing=_preprocessing_specification(),
        training=_training_specification(batch),
        checkpointing=CheckpointSchedule(rounds=_checkpoint_rounds()),
        checkpoint_selection=_checkpoint_selection(),
        scoring=_score_generation_specification(batch),
        thresholds=_threshold_suite(),
        evaluation=StandardEvaluationSuiteSpec(
            primary_metric=OperatingPointMetric.CV_FPR,
            metrics=(_metric(OperatingPointMetric.CV_FPR),),
        ),
        statistics=_statistical_analysis_specification(),
        resource_costs=None,
    )


def _dataset_specification() -> DatasetSpec:
    return DatasetSpec(
        dataset=Dataset.N_BAIOT,
        input_dim=4,
        feature_schema_identity=FeatureSchemaIdentity(value=_fingerprint("a")),
        feature_count_verified=True,
    )


def _partition_specification() -> NaturalDevicePartitionSpec:
    return NaturalDevicePartitionSpec(strategy=ClientDefinitionStrategy.NATURAL_DEVICE, regime=Regime.A)


def _split_collection() -> SplitCollectionSpec:
    partition_identity = PartitionIdentity(value=_fingerprint("b"))
    return SplitCollectionSpec(
        training=TrainingSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint("c")), partition_identity=partition_identity
        ),
        calibration=BenignCalibrationSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint("d")), partition_identity=partition_identity
        ),
        test=TestSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint("e")), partition_identity=partition_identity
        ),
    )


def _preprocessing_specification() -> PreprocessingSpec:
    chunk_rows = ChunkRowCount(value=8)
    return PreprocessingSpec(
        strategy=NormalizationStrategy.STANDARD,
        scope=NormalizationScope.GLOBAL_TRAIN,
        fitted_stat_policy=FittedStatisticPolicy.EXACT_TWO_PASS,
        chunking=PreprocessingChunkSpec(
            source_scan_batch_rows=chunk_rows,
            preprocessing_chunk_rows=chunk_rows,
            parquet_write_batch_rows=chunk_rows,
        ),
    )


def _training_specification(batch: BatchSize) -> TrainingSpec:
    return TrainingSpec(
        seed=Seed(value=7),
        autoencoder=AutoencoderSpec(
            input_dim=4, hidden_dims=(3,), bottleneck_dim=2, activation=ActivationFunction.RELU
        ),
        federation=FederationSpec(
            aggregation=AggregationStrategy.FEDAVG,
            local_epochs=1,
            participation=ParticipationStrategy.FULL,
            rounds_max=200,
            fedprox_mu=None,
        ),
        optimizer=OptimizerType.ADAM,
        lr=0.001,
        scheduler=LrSchedulerType.NONE,
        training_batch=_training_batch_specification(batch),
        precision=PrecisionMode.FP32,
        determinism=DeterminismLevel.STRICT,
        personalization=ModelPersonalizationStrategy.NONE,
    )


def _training_batch_specification(batch: BatchSize) -> TrainingBatchSpec:
    return TrainingBatchSpec(
        micro_batch_size=batch,
        gradient_accumulation_steps=GradientAccumulationSteps(value=1),
        effective_batch_size=batch,
        dataloader_batch_size=batch,
        client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
        optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
    )


def _checkpoint_rounds() -> tuple[RoundNumber, ...]:
    return tuple(RoundNumber(value=value) for value in (25, 50, 75, 100, 125, 150, 200))


def _checkpoint_selection() -> CheckpointSelectionSpec:
    return CheckpointSelectionSpec(
        strategy=CheckpointSelectionStrategy.REGIME_A_GLOBAL_PRIMARY,
        candidate_rounds=_checkpoint_rounds(),
        selection_rule_version=REGIME_A_SELECTION_RULE_VERSION,
        tie_break_rule=EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE,
    )


def _score_generation_specification(batch: BatchSize) -> ScoreGenerationSpec:
    return ScoreGenerationSpec(
        scoring_batch=ScoringBatchSpec(calibration_batch_size=batch, test_batch_size=batch, temporal_batch_size=batch),
        precision=PrecisionMode.FP32,
        numeric_equivalence_policy="exact_fp32",
    )


def _threshold_suite() -> ThresholdSuiteSpec:
    return ThresholdSuiteSpec(
        constructions=(
            SharedThresholdSpec(
                kind=ThresholdConstructionKind.SHARED,
                percentile=ThresholdPercentile(value=0.95),
                construction=SharedThresholdConstruction.MEAN,
                estimator=QuantileEstimatorType.LOCAL_EXACT,
            ),
        )
    )


def _statistical_analysis_specification() -> StatisticalAnalysisSpec:
    return StatisticalAnalysisSpec(
        method=StatisticalMethod.BCA_BOOTSTRAP,
        confidence=ConfidenceLevel(value=0.95),
        resamples=BootstrapResampleCount(value=10),
        paired_seed_count=10,
    )


def confirmatory_profile() -> ConfirmatoryExperimentProfileSpec:
    base_protocol = _protocol()
    protocol = replace(
        base_protocol,
        thresholds=ThresholdSuiteSpec(
            constructions=(
                base_protocol.thresholds.constructions[0],
                LocalThresholdSpec(
                    kind=ThresholdConstructionKind.LOCAL,
                    percentile=ThresholdPercentile(value=0.95),
                    estimator=QuantileEstimatorType.LOCAL_EXACT,
                ),
            )
        ),
    )
    identity = ExperimentIdentity(
        experiment_id=ExperimentId(value="E-C1"),
        evidence_role=ExperimentRole.CONFIRMATORY,
        tier=ClaimTier.TIER_1,
        execution_status=ExecutionStatus.MANDATORY,
    )
    return ConfirmatoryExperimentProfileSpec(
        catalogue_id=identity.experiment_id,
        identity=identity,
        regime_compatibility=RegimeCompatibilitySpec(
            regime=Regime.A,
            dataset=Dataset.N_BAIOT,
            client_strategy=ClientDefinitionStrategy.NATURAL_DEVICE,
            client_count=9,
            feasibility_status=FeasibilityStatus.FEASIBLE,
            boundary_only=False,
            timestamp_evidence=None,
        ),
        authorized_protocols=(protocol,),
        authorized_seed_plan=SeedTuple(values=tuple(Seed(value=value) for value in range(10))),
        primary_metrics=(OperatingPointMetric.CV_FPR,),
        secondary_metrics=(),
        statistical_procedure=protocol.statistics,
        artifact_dependencies=ArtifactDependencySpec(required_artifacts=(ArtifactType.CALIBRATION_SCORE_SET,)),
        fallback_policy=FallbackPolicySpec(outcomes=(ClaimOutcome.NULL, ClaimOutcome.OPPOSITE)),
        manuscript_role=ManuscriptRoleSpec(placement=ManuscriptPlacement.MAIN, report_artifacts=()),
    )


def test_scientific_protocol_is_the_only_aggregate_with_scientific_field_placement() -> None:
    protocol = _protocol()

    assert tuple(field.name for field in fields(ScientificProtocolSpec)) == tuple(
        field.value for field in ScientificProtocolField
    )
    assert {input_.field for input_ in protocol.identity_inputs()} == set(ScientificProtocolField)
    assert not set(field.name for field in fields(ScientificProtocolSpec)).intersection(
        name for policy_fields in policy_field_names() for name in policy_fields
    )


def test_policy_aggregates_are_structurally_disjoint() -> None:
    assert all(
        left.isdisjoint(right)
        for index, left in enumerate(map(set, policy_field_names()))
        for right in tuple(map(set, policy_field_names()))[index + 1 :]
    )


def test_alert_burden_suite_requires_traffic_evidence() -> None:
    metrics = (_metric(OperatingPointMetric.CV_FPR), _metric(OperatingPointMetric.ALERT_BURDEN))
    evidence = CitedTrafficRateEvidence(
        traffic_rate=TrafficRate(value=Decimal("1"), unit=TrafficRateUnit.EVENTS_PER_SECOND),
        scope_identity=_fingerprint("f"),
        source_reference="published-rate",
        applicability_period="one-day",
    )

    suite = AlertBurdenEvaluationSuiteSpec(
        primary_metric=OperatingPointMetric.CV_FPR,
        metrics=metrics,
        traffic_rate_evidence=evidence,
    )

    assert suite.traffic_rate_evidence is evidence
    with pytest.raises(DomainValidationError):
        _alert_burden_suite_without_traffic_evidence(metrics=metrics)


def _alert_burden_suite_without_traffic_evidence(*, metrics: tuple[MetricSpec, ...]) -> AlertBurdenEvaluationSuiteSpec:
    return _construct_alert_burden_suite_without_traffic_evidence(AlertBurdenEvaluationSuiteSpec, metrics=metrics)


def _construct_alert_burden_suite_without_traffic_evidence(
    constructor: Callable[..., AlertBurdenEvaluationSuiteSpec], *, metrics: tuple[MetricSpec, ...]
) -> AlertBurdenEvaluationSuiteSpec:
    return constructor(
        primary_metric=OperatingPointMetric.CV_FPR,
        metrics=metrics,
        traffic_rate_evidence=None,
    )


def test_protocol_rechecks_the_exact_static_split_roles() -> None:
    protocol = _protocol()
    assert tuple(input_.earliest_stage for input_ in protocol.identity_inputs()) == (
        PipelineStage.SOURCE_INSPECTION,
        PipelineStage.SOURCE_INSPECTION,
        PipelineStage.PARTITION,
        PipelineStage.SPLIT_BUILD,
        PipelineStage.PREPROCESSOR_FIT,
        PipelineStage.TRAIN,
        PipelineStage.CHECKPOINT_SELECT,
        PipelineStage.CHECKPOINT_SELECT,
        PipelineStage.CALIBRATION_SCORE,
        PipelineStage.THRESHOLD,
        PipelineStage.EVALUATE,
        PipelineStage.ANALYZE,
        PipelineStage.RESOURCE_COST,
    )


def test_confirmatory_profile_rejects_an_alternate_primary_metric() -> None:
    profile = confirmatory_profile()

    with pytest.raises(DomainValidationError):
        replace(profile, primary_metrics=(OperatingPointMetric.CV_TPR,))


@pytest.mark.parametrize(
    "non_confirmatory_construction",
    (
        lambda: FamilyThresholdSpec(
            kind=ThresholdConstructionKind.FAMILY,
            percentile=ThresholdPercentile(value=0.95),
            family_manifest_identity=_fingerprint("a"),
        ),
        lambda: RobustClusterMedianThresholdSpec(
            kind=ThresholdConstructionKind.ROBUST_CLUSTER_MEDIAN,
            canonical_assignment_identity=_fingerprint("b"),
        ),
        lambda: ShrinkageThresholdSpec(
            kind=ThresholdConstructionKind.SHRINKAGE,
            percentile=ThresholdPercentile(value=0.95),
            shrinkage_weight=ShrinkageWeight(value=0.5),
        ),
    ),
)
def test_confirmatory_profile_rejects_b3_b4_and_variant_arms(
    non_confirmatory_construction: Callable[[], NonConfirmatoryConstruction],
) -> None:
    profile = confirmatory_profile()
    protocol = profile.authorized_protocols[0]
    unauthorized_protocol = replace(
        protocol,
        thresholds=ThresholdSuiteSpec(
            constructions=(protocol.thresholds.constructions[0], non_confirmatory_construction())
        ),
    )

    with pytest.raises(DomainValidationError):
        replace(profile, authorized_protocols=(unauthorized_protocol,))


def test_confirmatory_profile_rejects_an_alternate_shared_policy() -> None:
    profile = confirmatory_profile()
    protocol = profile.authorized_protocols[0]
    shared = protocol.thresholds.constructions[0]
    assert type(shared) is SharedThresholdSpec
    unauthorized_protocol = replace(
        protocol,
        thresholds=ThresholdSuiteSpec(
            constructions=(
                replace(shared, construction=SharedThresholdConstruction.POOLED),
                protocol.thresholds.constructions[1],
            )
        ),
    )

    with pytest.raises(DomainValidationError):
        replace(profile, authorized_protocols=(unauthorized_protocol,))


def _protocol_with_unauthorized_dataset(protocol: ScientificProtocolSpec) -> ScientificProtocolSpec:
    return replace(protocol, dataset=replace(protocol.dataset, dataset=Dataset.EDGE_IIOTSET))


def _protocol_with_unauthorized_regime(protocol: ScientificProtocolSpec) -> ScientificProtocolSpec:
    return replace(protocol, partitioning=replace(protocol.partitioning, regime=Regime.C))


@pytest.mark.parametrize(
    "unauthorized_protocol",
    (_protocol_with_unauthorized_dataset, _protocol_with_unauthorized_regime),
)
def test_profile_rejects_unauthorized_dataset_and_regime_combinations(
    unauthorized_protocol: Callable[[ScientificProtocolSpec], ScientificProtocolSpec],
) -> None:
    profile = confirmatory_profile()

    with pytest.raises(DomainValidationError):
        replace(profile, authorized_protocols=(unauthorized_protocol(profile.authorized_protocols[0]),))


def test_b0_requires_the_disjoint_centralized_profile_route() -> None:
    profile = confirmatory_profile()
    with pytest.raises(DomainValidationError):
        replace(profile, catalogue_id=ArchitectureCatalogueId(value="B0_CENTRALIZED_COMPARATOR"))

    centralized = CentralizedModelComparatorProfileSpec(
        catalogue_id=ArchitectureCatalogueId(value="B0_CENTRALIZED_COMPARATOR"),
        identity=replace(
            profile.identity,
            experiment_id=ExperimentId(value="E-S1"),
            evidence_role=ExperimentRole.SUPPORTIVE,
            tier=ClaimTier.TIER_2,
        ),
        comparator=CentralizedModelComparatorSpec(
            model_identity=CentralizedModelIdentity(value=_fingerprint("a")),
            checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("b")),
            calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("c")),
            test_score_identity=CentralizedTestScoringIdentity(value=_fingerprint("d")),
            threshold_identity=CentralizedThresholdIdentity(value=_fingerprint("e")),
            evaluation_identity=CentralizedEvaluationIdentity(value=_fingerprint("f")),
        ),
        reporting_policy=ReportingPolicy(
            tables=(),
            figures=(),
            report_artifacts=(),
            formats=EnumMap(entries=(), allowed_keys=(), is_sparse=False),
            wording_outcomes=(),
        ),
    )

    assert type(centralized.comparator.model_identity) is CentralizedModelIdentity


def test_artifact_dependency_requires_non_empty_unique_artifacts() -> None:
    with pytest.raises(DomainValidationError):
        ArtifactDependencySpec(required_artifacts=())

    with pytest.raises(DomainValidationError):
        ArtifactDependencySpec(
            required_artifacts=(ArtifactType.CALIBRATION_SCORE_SET, ArtifactType.CALIBRATION_SCORE_SET)
        )


def test_fallback_policy_requires_non_empty_unique_outcomes() -> None:
    with pytest.raises(DomainValidationError):
        FallbackPolicySpec(outcomes=())

    with pytest.raises(DomainValidationError):
        FallbackPolicySpec(outcomes=(ClaimOutcome.NULL, ClaimOutcome.NULL))


def test_sweep_rejects_an_unauthorized_grid_value() -> None:
    with pytest.raises(DomainValidationError):
        SweepSpec(axis=SweepAxis.QUANTILE, values=(ThresholdPercentile(value=0.80),))


def test_profile_catalogue_uses_the_e_v3_fpr_target() -> None:
    assert CONFORMAL_ALPHA.value == Decimal("0.05")
