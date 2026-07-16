from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from datp_core.config.compose import OVERRIDE_PRECEDENCE, compose_configuration
from datp_core.config.loader import load_yaml
from datp_core.config.mapping.execution import map_streaming_chunk_config
from datp_core.config.mapping.scientific import (
    ExperimentConfigSchema,
    ResolveExperimentProfileRequest,
    map_canonical_temporal_config,
    map_centralized_comparator_config,
    map_experiment_schema,
    map_federation_config,
    map_regime_a_preprocessing_config,
    map_regime_a_static_split_config,
    resolve_experiment_profile,
)
from datp_core.config.schemas.artifacts import ArtifactConfig, ArtifactSerializationConfig
from datp_core.config.schemas.execution import (
    ExecutionConfig,
    ParallelismConfig,
    RecoveryConfig,
    ResourceBudgetConfig,
    ResourcePressureConfig,
    StageExecutionConfig,
    StreamingChunkConfig,
)
from datp_core.config.schemas.reporting import ReportingConfig
from datp_core.config.schemas.scientific import (
    BcaBootstrapStatisticalConfig,
    CanonicalTemporalConfig,
    CentralizedComparatorConfig,
    EvaluationConfig,
    FedAvgFederationConfig,
    FedProxFederationConfig,
    LocalThresholdConfig,
    RegimeAPreprocessingConfig,
    RegimeAStaticSplitConfig,
    ScientificConfig,
    SharedThresholdConfig,
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
from datp_core.domain.data.datasets import TimestampEvidenceKind
from datp_core.domain.data.preprocessing import (
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
)
from datp_core.domain.data.splitting import LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY
from datp_core.domain.errors import ConfigurationError
from datp_core.domain.evaluation.metrics import OperatingPointMetric
from datp_core.domain.experiments.claims import ClaimTier, ExperimentRole
from datp_core.domain.experiments.identities import ArchitectureCatalogueId, ExperimentId
from datp_core.domain.experiments.protocols import ProtocolTrack, ReportingPolicy
from datp_core.domain.experiments.specifications import (
    CentralizedModelComparatorProfileSpec,
    CentralizedModelComparatorSpec,
)
from datp_core.domain.learning.checkpoints import RecoveryCadence
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
from datp_core.domain.thresholding.policies import SharedThresholdConstruction
from tests.unit.domain.test_protocol_aggregates import confirmatory_profile


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
        reporting=ReportingConfig(tables=(), figures=(), report_artifacts=(), formats=(), wording_outcomes=()),
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
    mapped = map_experiment_schema(schema)
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
    with pytest.raises(ValidationError):
        RegimeAStaticSplitConfig(
            train_fraction=Decimal("0.50"),
            gap_fraction=Decimal("0.01"),
            calibration_fraction=Decimal("0.20"),
        )


def test_regime_a_static_split_mapping_produces_the_locked_boundary() -> None:
    configuration = RegimeAStaticSplitConfig(
        train_fraction=Decimal("0.60"),
        gap_fraction=Decimal("0.01"),
        calibration_fraction=Decimal("0.20"),
    )

    assert map_regime_a_static_split_config(configuration) == LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY


def test_regime_a_static_split_yaml_file_loads_and_maps_to_the_locked_boundary() -> None:
    yaml_path = Path(__file__).resolve().parents[3] / "configs" / "protocols" / "regime_a_static_split.yaml"

    schema = load_yaml(yaml_path.read_text(), RegimeAStaticSplitConfig)

    assert map_regime_a_static_split_config(schema) == LOCKED_REGIME_A_STATIC_SPLIT_BOUNDARY


def test_streaming_chunk_schema_rejects_a_non_positive_value() -> None:
    with pytest.raises(ValidationError):
        StreamingChunkConfig(csv_block_bytes=0, parquet_batch_rows=50_000)


def test_streaming_chunk_mapping_produces_typed_domain_values() -> None:
    configuration = StreamingChunkConfig(csv_block_bytes=8 * 1024 * 1024, parquet_batch_rows=50_000)

    mapped = map_streaming_chunk_config(configuration)

    assert mapped.csv_block_bytes.value == 8 * 1024 * 1024
    assert mapped.parquet_batch_rows.value == 50_000


def test_streaming_chunk_yaml_file_loads_and_maps() -> None:
    yaml_path = Path(__file__).resolve().parents[3] / "configs" / "execution" / "streaming_chunks.yaml"

    schema = load_yaml(yaml_path.read_text(), StreamingChunkConfig)
    mapped = map_streaming_chunk_config(schema)

    assert mapped.csv_block_bytes.value == 8 * 1024 * 1024
    assert mapped.parquet_batch_rows.value == 50_000


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


def test_regime_a_preprocessing_yaml_file_loads_and_maps() -> None:
    yaml_path = Path(__file__).resolve().parents[3] / "configs" / "protocols" / "regime_a_preprocessing.yaml"
    chunk_rows = ChunkRowCount(value=50_000)
    chunking = PreprocessingChunkSpec(
        source_scan_batch_rows=chunk_rows, preprocessing_chunk_rows=chunk_rows, parquet_write_batch_rows=chunk_rows
    )

    schema = load_yaml(yaml_path.read_text(), RegimeAPreprocessingConfig)
    mapped = map_regime_a_preprocessing_config(schema, chunking=chunking)

    assert mapped.strategy is NormalizationStrategy.STANDARD
    assert mapped.scope is NormalizationScope.PER_CLIENT_TRAIN
    assert mapped.fitted_stat_policy is FittedStatisticPolicy.EXACT_TWO_PASS


def test_ordered_override_precedence_is_deterministic() -> None:
    base = _scientific_config()
    override = _scientific_config(protocol_track=ProtocolTrack.JOURNAL_EXTENSION)

    assert OVERRIDE_PRECEDENCE == "ordered_override_wins"
    assert compose_configuration(base, (override,)) == override
    first_composition = compose_configuration(base, (override,))
    second_composition = compose_configuration(base, (override,))

    assert first_composition == second_composition


def test_loader_validates_yaml_at_the_boundary() -> None:
    schema = load_yaml(
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
        map_experiment_schema(scientific)
