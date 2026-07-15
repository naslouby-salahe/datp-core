from dataclasses import replace
from decimal import Decimal

import pytest
from pydantic import ValidationError

from datp_core.config.compose import OVERRIDE_PRECEDENCE, compose_configuration
from datp_core.config.loader import load_yaml
from datp_core.config.mapping.scientific import (
    ExperimentConfigSchema,
    ResolveExperimentProfileRequest,
    map_canonical_temporal_config,
    map_centralized_comparator_config,
    map_experiment_schema,
    map_federation_config,
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

    assert mapped.scientific_protocol in mapped.profile.authorized_protocols
    with pytest.raises(ConfigurationError):
        resolve_experiment_profile(
            ResolveExperimentProfileRequest(
                experiment_id=ExperimentId(value="E-S1"),
                profiles=schema.profile_request.profiles,
            )
        )


def test_fedprox_mapping_rejects_zero_and_requires_the_frozen_grid() -> None:
    with pytest.raises(ConfigurationError):
        map_federation_config(
            FedProxFederationConfig(
                aggregation=AggregationStrategy.FEDPROX,
                local_epochs=1,
                participation=ParticipationStrategy.FULL,
                rounds_max=200,
                fedprox_mu=Decimal(0),
                selection_source="pre_registered_grid",
            )
        )


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
    with pytest.raises(ConfigurationError):
        map_canonical_temporal_config(
            CanonicalTemporalConfig(
                historical_fraction=Decimal("0.70"),
                timestamp_evidence_kind=TimestampEvidenceKind.GENUINE_CAPTURE_TIME,
                capture_timestamp_field="file_order",
                boundary_identity="b" * 64,
            )
        )


def test_canonical_temporal_schema_rejects_a_non_70_30_boundary() -> None:
    with pytest.raises(ValidationError):
        CanonicalTemporalConfig(
            historical_fraction=Decimal("0.60"),
            timestamp_evidence_kind=TimestampEvidenceKind.GENUINE_CAPTURE_TIME,
            capture_timestamp_field="capture_time",
            boundary_identity="b" * 64,
        )


def test_ordered_override_precedence_is_deterministic() -> None:
    base = _scientific_config()
    override = _scientific_config(protocol_track=ProtocolTrack.JOURNAL_EXTENSION)

    assert OVERRIDE_PRECEDENCE == "ordered_override_wins"
    assert compose_configuration(base, (override,)) == override
    assert compose_configuration(base, (override,)) == compose_configuration(base, (override,))


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
