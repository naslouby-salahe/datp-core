from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from datp_core.config.documents import ConfigurationDocument
from datp_core.config.loader import ValidatedSchema, load_yaml_document
from datp_core.config.mapping.execution import (
    map_execution_profile_config,
    map_scoring_batch_config,
    map_streaming_chunk_config,
)
from datp_core.config.mapping.scientific import (
    ExperimentConfigSchema,
    ResolveExperimentProfileRequest,
    map_absorption_gate_config,
    map_anchor_checkpoint_termination_config,
    map_anchor_reference_interval_config,
    map_b0_pooled_threshold_config,
    map_calibration_size_grid_config,
    map_canonical_temporal_config,
    map_centralized_comparator_config,
    map_conformal_alpha_config,
    map_dirichlet_alpha_grid_config,
    map_experiment_schema,
    map_fed_stats_supplementary_k_config,
    map_federation_config,
    map_partitioning_config,
    map_q_sensitivity_grid_config,
    map_regime_a_preprocessing_config,
    map_regime_a_static_split_config,
    map_shrinkage_weight_grid_config,
    map_temporal_recovery_gate_config,
    resolve_experiment_profile,
)
from datp_core.config.schemas.artifacts import ArtifactConfig, ArtifactSerializationConfig
from datp_core.config.schemas.execution import (
    ExecutionConfig,
    ExecutionProfileConfig,
    ExecutionProfilesConfig,
    ParallelismConfig,
    RecoveryConfig,
    ResourceBudgetConfig,
    ResourcePressureConfig,
    ScoringBatchConfig,
    StageExecutionConfig,
    StreamingChunkConfig,
)
from datp_core.config.schemas.reporting import ReportingConfig
from datp_core.config.schemas.scientific import (
    AbsorptionGateConfig,
    AnchorCheckpointTerminationConfig,
    AnchorReferenceIntervalConfig,
    B0PooledThresholdConfig,
    BcaBootstrapStatisticalConfig,
    CalibrationSizeGridConfig,
    CanonicalTemporalConfig,
    CentralizedComparatorConfig,
    ConformalAlphaConfig,
    ConformalThresholdConfig,
    DirichletAlphaGridConfig,
    DirichletPartitionConfig,
    EvaluationConfig,
    FedAvgFederationConfig,
    FedProxFederationConfig,
    FedStatsSupplementaryKConfig,
    LocalThresholdConfig,
    NaturalDevicePartitionConfig,
    QSensitivityGridConfig,
    RegimeAPreprocessingConfig,
    RegimeAStaticSplitConfig,
    ScientificConfig,
    SharedThresholdConfig,
    ShrinkageWeightGridConfig,
    TemporalRecoveryGateConfig,
)
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    ArtifactRetentionPolicy,
    SerializationFormat,
    WriteDisposition,
)
from datp_core.domain.artifacts.lineage import (
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedModelIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.datasets import Regime, TimestampEvidenceKind
from datp_core.domain.data.partitioning import (
    ClientDefinitionStrategy,
    DirichletAlpha,
    DirichletAlphaSentinel,
    DirichletPartitionSpec,
)
from datp_core.domain.data.preprocessing import (
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
)
from datp_core.domain.data.splitting import LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY, ConformalQuantileIndexRule
from datp_core.domain.errors import ConfigurationError
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.metrics import OperatingPointMetric
from datp_core.domain.evaluation.statistical_results import AnchorReferenceInterval
from datp_core.domain.experiments.claims import ClaimTier, ExperimentRole
from datp_core.domain.experiments.identities import ArchitectureCatalogueId, ExperimentId
from datp_core.domain.experiments.protocols import ProtocolTrack, ReportingPolicy
from datp_core.domain.experiments.specifications import (
    LOCKED_B0_CENTRALIZED_COMPARATOR_PROFILE,
    CentralizedModelComparatorProfileSpec,
    CentralizedModelComparatorSpec,
)
from datp_core.domain.learning.checkpoints import LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY, RecoveryCadence
from datp_core.domain.learning.scores import QuantileEstimatorType
from datp_core.domain.learning.training import AggregationStrategy, ParticipationStrategy
from datp_core.domain.runtime.admissibility import ChunkRowCount
from datp_core.domain.runtime.policies import (
    DevicePolicy,
    ExecutionMode,
    PauseDecision,
    PipelineStage,
    ProcessStartMethod,
    StageConcurrency,
)
from datp_core.domain.runtime.seeds import EnumMap, SeedRole
from datp_core.domain.thresholding.federated_statistics import FED_STATS_SUPPLEMENTARY_K_VALUES
from datp_core.domain.thresholding.policies import (
    B0PooledThresholdSpec,
    FprTarget,
    SharedThresholdConstruction,
    ThresholdPercentile,
)
from tests.support.composed_configuration import composed_profile_catalogue
from tests.unit.domain.test_protocol_aggregates import confirmatory_profile


def _load_schema[Schema: ValidatedSchema](text: str, schema_type: type[Schema]) -> Schema:
    return load_yaml_document(
        text=text,
        schema_type=schema_type,
        document=ConfigurationDocument.SCIENTIFIC_THRESHOLDS,
    )


def _execution_config(*, mode: ExecutionMode, unresolved_fields: tuple[str, ...] = ()) -> ExecutionConfig:
    return ExecutionConfig(
        mode=mode,
        device_policy=DevicePolicy.CPU_ALLOWED,
        gpu_index=None,
        budget=ResourceBudgetConfig(
            maximum_ram_bytes=1024,
            maximum_vram_bytes=1024,
            maximum_worker_count=1,
            maximum_prefetch_capacity=0,
            maximum_disk_bytes=2048,
            storage_safety_reserve=1024,
        ),
        parallelism=ParallelismConfig(
            maximum_cpu_workers=1,
            maximum_gpu_jobs=0,
            stage_execution=(
                StageExecutionConfig(
                    stage=PipelineStage.SOURCE_INSPECTION,
                    concurrency=StageConcurrency.SEQUENTIAL,
                    start_method=ProcessStartMethod.SPAWN,
                    reason="deterministic synthetic test",
                ),
            ),
            thread_limit=1,
        ),
        seed_roles=(SeedRole.TRAINING_INIT,),
        resource_pressure=ResourcePressureConfig(
            ram_pressure_fraction=Decimal("0.8"),
            vram_pressure_fraction=Decimal("0.8"),
            load_pressure_fraction=Decimal("0.8"),
            elevated_response=PauseDecision.PAUSE_AT_SAFE_BOUNDARY,
            critical_response=PauseDecision.EXIT_AFTER_RECOVERY_COMMIT,
        ),
        recovery=RecoveryConfig(
            cadence=RecoveryCadence.COMPLETED_ROUND,
            cadence_interval=1,
            retention=1,
            compatibility_identity="a" * 64,
        ),
        unresolved_fields=unresolved_fields,
    )


def _artifact_config() -> ArtifactConfig:
    return ArtifactConfig(
        policy_id="test",
        namespace=ArtifactNamespace.DATP_ANCHOR,
        write_disposition=WriteDisposition.CREATE_IF_ABSENT,
        retention=ArtifactRetentionPolicy.RETAIN_ALWAYS,
        serialization_defaults=tuple(
            ArtifactSerializationConfig(artifact_type=artifact_type, serialization_format=SerializationFormat.JSON)
            for artifact_type in ArtifactType
        ),
    )


def _scientific_config(*, protocol_track: ProtocolTrack = ProtocolTrack.DATP_ANCHOR) -> ScientificConfig:
    return ScientificConfig(
        protocol_track=protocol_track,
        partitioning=NaturalDevicePartitionConfig(
            strategy=ClientDefinitionStrategy.NATURAL_DEVICE,
            regime=Regime.A,
        ),
        threshold_constructions=(
            SharedThresholdConfig(
                kind="shared",
                percentile=Decimal("0.95"),
                construction=SharedThresholdConstruction.MEAN,
                estimator=QuantileEstimatorType.LOCAL_EXACT,
            ),
            LocalThresholdConfig(
                kind="local",
                percentile=Decimal("0.95"),
                estimator=QuantileEstimatorType.LOCAL_EXACT,
            ),
        ),
        evaluation=EvaluationConfig(primary=OperatingPointMetric.CV_FPR, controls=()),
        statistics=BcaBootstrapStatisticalConfig(
            method="bca_bootstrap",
            confidence=Decimal("0.95"),
            paired_seed_count=10,
            resamples=10,
        ),
        federation=FedAvgFederationConfig(
            aggregation=AggregationStrategy.FEDAVG,
            local_epochs=1,
            participation=ParticipationStrategy.FULL,
            rounds_max=200,
            fedprox_mu=None,
            selection_source="not_applicable",
        ),
        canonical_temporal=None,
    )


def experiment_config() -> ExperimentConfigSchema:
    profile = confirmatory_profile()
    return ExperimentConfigSchema(
        profile_request=ResolveExperimentProfileRequest(
            experiment_id=profile.identity.experiment_id,
            profiles=(profile,),
        ),
        scientific=_scientific_config(),
        execution=_execution_config(mode=ExecutionMode.DEVELOPMENT),
        artifacts=_artifact_config(),
        reporting=ReportingConfig(
            policy_id="test",
            tables=(),
            figures=(),
            report_artifacts=(),
            formats=(),
            wording_outcomes=(),
        ),
    )


def _centralized_profile() -> CentralizedModelComparatorProfileSpec:
    profile = confirmatory_profile()
    comparator = CentralizedModelComparatorSpec(
        model_identity=CentralizedModelIdentity(value=StageFingerprint(value="a" * 64)),
        checkpoint_identity=CentralizedCheckpointIdentity(value=StageFingerprint(value="b" * 64)),
        calibration_score_identity=CentralizedCalibrationScoringIdentity(value=StageFingerprint(value="c" * 64)),
        test_score_identity=CentralizedTestScoringIdentity(value=StageFingerprint(value="d" * 64)),
        threshold_identity=CentralizedThresholdIdentity(value=StageFingerprint(value="e" * 64)),
        evaluation_identity=CentralizedEvaluationIdentity(value=StageFingerprint(value="f" * 64)),
    )
    return CentralizedModelComparatorProfileSpec(
        catalogue_id=ArchitectureCatalogueId(value="B0_CENTRALIZED_COMPARATOR"),
        identity=replace(
            profile.identity,
            experiment_id=ExperimentId(value="E-S1"),
            evidence_role=ExperimentRole.SUPPORTIVE,
            tier=ClaimTier.TIER_2,
        ),
        comparator=comparator,
        reporting_policy=ReportingPolicy(
            tables=(),
            figures=(),
            report_artifacts=(),
            formats=EnumMap(entries=(), allowed_keys=(), is_sparse=False),
            wording_outcomes=(),
        ),
    )


def test_profile_resolution_precedes_closed_cell_mapping() -> None:
    schema = experiment_config()
    mapped = map_experiment_schema(schema, catalogue=composed_profile_catalogue())
    request = ResolveExperimentProfileRequest(
        experiment_id=ExperimentId(value="E-S1"),
        profiles=schema.profile_request.profiles,
    )

    assert mapped.scientific_protocol in mapped.profile.authorized_protocols
    with pytest.raises(ConfigurationError):
        resolve_experiment_profile(request)


def test_fedprox_mapping_rejects_zero_and_requires_the_frozen_grid() -> None:
    configuration = FedProxFederationConfig(
        aggregation=AggregationStrategy.FEDPROX,
        local_epochs=1,
        participation=ParticipationStrategy.FULL,
        rounds_max=200,
        fedprox_mu=Decimal(0),
        selection_source="pre_registered_grid",
    )

    with pytest.raises(ConfigurationError):
        map_federation_config(configuration)


def test_b0_uses_the_dedicated_centralized_comparator_mapper() -> None:
    profile = _centralized_profile()
    mapped = map_centralized_comparator_config(
        CentralizedComparatorConfig(
            model_identity="a" * 64,
            checkpoint_identity="b" * 64,
            calibration_score_identity="c" * 64,
            test_score_identity="d" * 64,
            threshold_identity="e" * 64,
            evaluation_identity="f" * 64,
        ),
        profile,
    )

    assert type(mapped) is CentralizedModelComparatorSpec


def test_b0_mapping_rejects_an_identity_that_does_not_match_the_locked_profile() -> None:
    profile = LOCKED_B0_CENTRALIZED_COMPARATOR_PROFILE
    mismatched_schema = CentralizedComparatorConfig(
        model_identity="9" * 64,
        checkpoint_identity=profile.comparator.checkpoint_identity.value.value,
        calibration_score_identity=profile.comparator.calibration_score_identity.value.value,
        test_score_identity=profile.comparator.test_score_identity.value.value,
        threshold_identity=profile.comparator.threshold_identity.value.value,
        evaluation_identity=profile.comparator.evaluation_identity.value.value,
    )

    with pytest.raises(ConfigurationError):
        map_centralized_comparator_config(mismatched_schema, profile)


def test_canonical_temporal_mapping_rejects_pseudo_time() -> None:
    configuration = CanonicalTemporalConfig(
        historical_fraction=Decimal("0.70"),
        timestamp_evidence_kind=TimestampEvidenceKind.GENUINE_CAPTURE_TIME,
        capture_timestamp_field="file_order",
        boundary_identity="b" * 64,
    )

    with pytest.raises(ConfigurationError):
        map_canonical_temporal_config(configuration)


def test_canonical_temporal_schema_rejects_a_non_70_30_boundary() -> None:
    historical_fraction = Decimal("0.60")

    with pytest.raises(ValidationError):
        CanonicalTemporalConfig(
            historical_fraction=historical_fraction,
            timestamp_evidence_kind=TimestampEvidenceKind.GENUINE_CAPTURE_TIME,
            capture_timestamp_field="capture_time",
            boundary_identity="b" * 64,
        )


def test_regime_a_static_split_schema_rejects_a_non_locked_fraction() -> None:
    non_locked_train_fraction = Decimal("0.50")
    gap_fraction = Decimal("0.01")
    calibration_fraction = Decimal("0.20")

    with pytest.raises(ValidationError):
        RegimeAStaticSplitConfig(
            train_fraction=non_locked_train_fraction,
            gap_fraction=gap_fraction,
            calibration_fraction=calibration_fraction,
        )


def test_regime_a_static_split_mapping_produces_the_locked_boundary() -> None:
    configuration = RegimeAStaticSplitConfig(
        train_fraction=Decimal("0.60"),
        gap_fraction=Decimal("0.01"),
        calibration_fraction=Decimal("0.20"),
    )

    assert map_regime_a_static_split_config(configuration) == LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY


def test_anchor_checkpoint_termination_schema_rejects_a_non_locked_rounds_max() -> None:
    payload = {"rounds_initial": 40, "rounds_max": 200}

    with pytest.raises(ValidationError):
        AnchorCheckpointTerminationConfig.model_validate(payload)


def test_anchor_checkpoint_termination_mapping_produces_the_locked_policy() -> None:
    configuration = AnchorCheckpointTerminationConfig(rounds_initial=40, rounds_max=150)

    assert map_anchor_checkpoint_termination_config(configuration) == LOCKED_ANCHOR_CHECKPOINT_TERMINATION_POLICY


def test_anchor_reference_interval_schema_rejects_a_non_locked_bound() -> None:
    with pytest.raises(ValidationError):
        AnchorReferenceIntervalConfig.model_validate({"lower": 0.6, "upper": 0.769, "tolerance_multiplier": 1.2})


def test_anchor_reference_interval_mapping_produces_the_locked_interval() -> None:
    configuration = AnchorReferenceIntervalConfig(lower=0.647, upper=0.769, tolerance_multiplier=1.2)

    assert map_anchor_reference_interval_config(configuration) == AnchorReferenceInterval(
        lower=0.647, upper=0.769, tolerance_multiplier=1.2
    )


def test_b0_pooled_threshold_schema_rejects_a_non_locked_percentile() -> None:
    with pytest.raises(ValidationError):
        B0PooledThresholdConfig.model_validate({"percentile": 90})


def test_b0_pooled_threshold_mapping_produces_the_locked_spec() -> None:
    configuration = B0PooledThresholdConfig(percentile=95)

    mapped = map_b0_pooled_threshold_config(configuration)

    assert mapped == B0PooledThresholdSpec(percentile=ThresholdPercentile(value="0.95"))


def test_absorption_gate_schema_rejects_an_out_of_range_fraction() -> None:
    with pytest.raises(ValidationError):
        AbsorptionGateConfig(
            strongly_useful_fraction=Decimal("1.50"),
            partial_absorption_fraction=Decimal("0.25"),
            alternative_path_distance=Decimal("0.05"),
        )


def test_absorption_gate_mapping_produces_the_locked_catalogue() -> None:
    configuration = AbsorptionGateConfig(
        strongly_useful_fraction=Decimal("0.75"),
        partial_absorption_fraction=Decimal("0.25"),
        alternative_path_distance=Decimal("0.05"),
    )

    assert map_absorption_gate_config(configuration) == composed_profile_catalogue().absorption_gates


def test_temporal_recovery_gate_schema_rejects_an_out_of_range_fraction() -> None:
    with pytest.raises(ValidationError):
        TemporalRecoveryGateConfig(meaningful_recovery_fraction=Decimal("-0.10"))


def test_temporal_recovery_gate_mapping_produces_the_locked_catalogue() -> None:
    configuration = TemporalRecoveryGateConfig(meaningful_recovery_fraction=Decimal("0.50"))

    assert map_temporal_recovery_gate_config(configuration) == composed_profile_catalogue().temporal_recovery_gate


def test_fed_stats_supplementary_k_mapping_produces_the_locked_grid() -> None:
    configuration = FedStatsSupplementaryKConfig(values=(Decimal("2.0"), Decimal("2.5"), Decimal("3.0")))

    assert map_fed_stats_supplementary_k_config(configuration) == FED_STATS_SUPPLEMENTARY_K_VALUES


def test_fed_stats_supplementary_k_schema_rejects_a_non_locked_value() -> None:
    with pytest.raises(ValidationError):
        FedStatsSupplementaryKConfig(values=(Decimal("2.0"), Decimal("2.5"), Decimal("4.0")))


def test_dirichlet_partitioning_rejects_an_unauthorized_alpha() -> None:
    unauthorized_partitioning = DirichletPartitionConfig(
        strategy=ClientDefinitionStrategy.DIRICHLET_SYNTHETIC,
        regime=Regime.C,
        alpha=0.2,
    )

    with pytest.raises(ConfigurationError):
        map_partitioning_config(unauthorized_partitioning, catalogue=composed_profile_catalogue())


def test_dirichlet_partitioning_accepts_an_authorized_alpha() -> None:
    authorized_partitioning = DirichletPartitionConfig(
        strategy=ClientDefinitionStrategy.DIRICHLET_SYNTHETIC,
        regime=Regime.C,
        alpha=0.3,
    )

    mapped = map_partitioning_config(authorized_partitioning, catalogue=composed_profile_catalogue())

    assert mapped == DirichletPartitionSpec(
        strategy=ClientDefinitionStrategy.DIRICHLET_SYNTHETIC,
        regime=Regime.C,
        alpha=DirichletAlpha(value=0.3),
    )


def test_conformal_threshold_schema_rejects_an_out_of_range_alpha() -> None:
    with pytest.raises(ValidationError):
        ConformalThresholdConfig(
            kind="conformal",
            mode="split",
            alpha=Decimal("1.10"),
            percentile=Decimal("0.95"),
            quantile_index_rule=ConformalQuantileIndexRule.CEILING_N_PLUS_ONE,
        )


def test_shared_threshold_configuration_rejects_an_unauthorized_percentile() -> None:
    schema = experiment_config()
    unauthorized_shared = schema.scientific.threshold_constructions[0].model_copy(
        update={"percentile": Decimal("0.93")}
    )
    unauthorized_scientific = schema.scientific.model_copy(
        update={"threshold_constructions": (unauthorized_shared, schema.scientific.threshold_constructions[1])}
    )
    unauthorized_schema = replace(schema, scientific=unauthorized_scientific)

    with pytest.raises(ConfigurationError):
        map_experiment_schema(unauthorized_schema, catalogue=composed_profile_catalogue())


def test_q_sensitivity_grid_mapping_produces_ordered_typed_percentiles() -> None:
    configuration = QSensitivityGridConfig(values=(Decimal("0.90"), Decimal("0.95"), Decimal("0.975"), Decimal("0.99")))

    mapped = map_q_sensitivity_grid_config(configuration)

    assert mapped == tuple(ThresholdPercentile(value=value) for value in configuration.values)


def test_q_sensitivity_grid_schema_rejects_a_duplicate_value() -> None:
    with pytest.raises(ValidationError):
        QSensitivityGridConfig(values=(Decimal("0.90"), Decimal("0.90")))


def test_streaming_chunk_schema_rejects_a_non_positive_value() -> None:
    with pytest.raises(ValidationError):
        StreamingChunkConfig(csv_block_bytes=0, parquet_batch_rows=50_000)


def test_streaming_chunk_mapping_produces_typed_domain_values() -> None:
    configuration = StreamingChunkConfig(csv_block_bytes=8 * 1024 * 1024, parquet_batch_rows=50_000)

    mapped = map_streaming_chunk_config(configuration)

    assert mapped.csv_block_bytes.value == 8 * 1024 * 1024
    assert mapped.parquet_batch_rows.value == 50_000


def test_scoring_batch_schema_rejects_a_non_positive_value() -> None:
    with pytest.raises(ValidationError):
        ScoringBatchConfig(calibration_batch_size=0, test_batch_size=256, temporal_batch_size=256)


def test_scoring_batch_mapping_produces_typed_domain_values() -> None:
    configuration = ScoringBatchConfig(calibration_batch_size=256, test_batch_size=128, temporal_batch_size=64)

    mapped = map_scoring_batch_config(configuration)

    assert mapped.calibration_batch_size.value == 256
    assert mapped.test_batch_size.value == 128
    assert mapped.temporal_batch_size.value == 64


def test_execution_profile_schema_rejects_a_non_positive_scoring_batch() -> None:
    with pytest.raises(ValidationError):
        ExecutionProfileConfig(
            profile_id="invalid",
            scoring_batch=ScoringBatchConfig(calibration_batch_size=0, test_batch_size=256, temporal_batch_size=256),
            streaming_chunk=StreamingChunkConfig(csv_block_bytes=8 * 1024 * 1024, parquet_batch_rows=50_000),
        )


def test_execution_profile_yaml_loads_once_and_derives_b0_batching() -> None:
    yaml_path = Path(__file__).resolve().parents[3] / "configs" / "execution" / "profiles.yaml"
    schema = load_yaml_document(
        text=yaml_path.read_text(),
        schema_type=ExecutionProfilesConfig,
        document=ConfigurationDocument.EXECUTION_PROFILES,
    )

    mapped = map_execution_profile_config(schema.profiles[0])

    assert mapped.scoring_batch.calibration_batch_size.value == 256
    assert mapped.scoring_batch.test_batch_size.value == 256
    assert mapped.scoring_batch.temporal_batch_size.value == 256
    assert mapped.b0_scoring_batch.calibration_batch_size == mapped.scoring_batch.calibration_batch_size
    assert mapped.b0_scoring_batch.test_batch_size == mapped.scoring_batch.test_batch_size
    assert mapped.streaming_chunk.csv_block_bytes.value == 8 * 1024 * 1024
    assert mapped.streaming_chunk.parquet_batch_rows.value == 50_000


def test_regime_a_preprocessing_schema_rejects_a_non_locked_strategy() -> None:
    with pytest.raises(ValidationError):
        RegimeAPreprocessingConfig.model_validate(
            {"strategy": "min_max", "scope": "per_client_train", "fitted_stat_policy": "exact_two_pass"}
        )


def test_regime_a_preprocessing_mapping_carries_the_injected_chunking() -> None:
    configuration = RegimeAPreprocessingConfig(
        strategy=NormalizationStrategy.STANDARD,
        scope=NormalizationScope.PER_CLIENT_TRAIN,
        fitted_stat_policy=FittedStatisticPolicy.EXACT_TWO_PASS,
    )
    chunk_rows = ChunkRowCount(value=50_000)
    chunking = PreprocessingChunkSpec(
        source_scan_batch_rows=chunk_rows, preprocessing_chunk_rows=chunk_rows, parquet_write_batch_rows=chunk_rows
    )

    mapped = map_regime_a_preprocessing_config(configuration, chunking=chunking)

    assert mapped.strategy is NormalizationStrategy.STANDARD
    assert mapped.scope is NormalizationScope.PER_CLIENT_TRAIN
    assert mapped.fitted_stat_policy is FittedStatisticPolicy.EXACT_TWO_PASS
    assert mapped.chunking == chunking


def test_dirichlet_alpha_grid_mapping_includes_the_iid_sentinel() -> None:
    configuration = DirichletAlphaGridConfig(values=(0.1, 0.3, 0.5, 1.0, 10.0, DirichletAlphaSentinel.IID))

    mapped = map_dirichlet_alpha_grid_config(configuration)

    assert mapped[-1] == DirichletAlpha(value=DirichletAlphaSentinel.IID)
    assert mapped[0] == DirichletAlpha(value=0.1)


def test_calibration_size_grid_mapping_is_ordered() -> None:
    configuration = CalibrationSizeGridConfig(values=(50, 100, 250, 500, 1000, 5000))

    assert map_calibration_size_grid_config(configuration) == tuple(
        CalibrationSampleCount(value=value) for value in (50, 100, 250, 500, 1000, 5000)
    )


def test_shrinkage_weight_grid_mapping_spans_zero_to_one() -> None:
    configuration = ShrinkageWeightGridConfig(
        values=(Decimal("0.00"), Decimal("0.25"), Decimal("0.50"), Decimal("0.75"), Decimal("1.00"))
    )

    mapped = map_shrinkage_weight_grid_config(configuration)

    assert mapped[0].value == 0.0
    assert mapped[-1].value == 1.0


def test_conformal_alpha_mapping_produces_an_fpr_target() -> None:
    configuration = ConformalAlphaConfig(alpha=Decimal("0.05"))

    assert map_conformal_alpha_config(configuration) == FprTarget(value=0.05)


def test_loader_validates_yaml_at_the_boundary() -> None:
    schema = _load_schema(
        """
primary: cv_fpr
controls: []
""",
        EvaluationConfig,
    )

    assert schema.primary.value == "cv_fpr"


def test_scientific_modes_reject_unresolved_execution_fields() -> None:
    schema = experiment_config()
    scientific = replace(schema, execution=_execution_config(mode=ExecutionMode.SCIENTIFIC, unresolved_fields=("gpu",)))

    with pytest.raises(ConfigurationError):
        map_experiment_schema(scientific, catalogue=composed_profile_catalogue())
