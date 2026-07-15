from dataclasses import dataclass

import pytest

from datp_core.application.ports.data import (
    BuildSplitManifestRequest,
    ClientPartitionRequest,
    DatasetSourceInspector,
    FitPreprocessorRequest,
    InspectDatasetSourceRequest,
    MaterializeProcessedSplitsRequest,
    PreprocessorFitter,
    ProcessedSplitMaterializer,
    SplitManifestBuilder,
)
from datp_core.application.ports.learning import (
    CentralizedModelTrainer,
    CentralizedTrainingRunResult,
    FederatedTrainer,
    TrainCentralizedModelRequest,
    TrainFederatedModelRequest,
    TrainingRunResult,
)
from datp_core.application.ports.scoring import (
    GenerateCalibrationScoresRequest,
    GenerateTemporalScoresRequest,
    GenerateTestScoresRequest,
    ScoreGenerator,
)
from datp_core.application.ports.statistics import RunStatisticalAnalysisRequest, StatisticalProcedureRunner
from datp_core.application.ports.thresholding import (
    ConstructThresholdsRequest,
    ThresholdAssignmentMetadata,
    ThresholdConstructor,
)
from datp_core.application.stages.analyze_statistics import analyze_statistics
from datp_core.application.stages.build_splits import build_splits
from datp_core.application.stages.construct_thresholds import construct_thresholds
from datp_core.application.stages.evaluate_policy import (
    ClientConfusionEvidence,
    EvaluatePolicyRequest,
    PolicyEvaluator,
)
from datp_core.application.stages.fit_preprocessor import fit_preprocessor
from datp_core.application.stages.generate_scores import (
    GenerateTemporalScoresStageRequest,
    generate_calibration_scores,
    generate_temporal_scores,
    generate_test_scores,
)
from datp_core.application.stages.inspect_dataset import inspect_dataset
from datp_core.application.stages.materialize_splits import materialize_splits
from datp_core.application.stages.partition_clients import partition_clients
from datp_core.application.stages.select_checkpoint import CheckpointSelectionRequest, CheckpointSelector
from datp_core.application.stages.train_model import (
    CentralizedTrainingStageRequest,
    FederatedTrainingStageRequest,
    train_model,
)
from datp_core.domain.artifacts import lineage as artifact_lineage
from datp_core.domain.artifacts import references as artifact_references
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import (
    CalibrationScoringIdentity,
    CentralizedCalibrationScoringIdentity,
    CentralizedCheckpointIdentity,
    CentralizedEvaluationIdentity,
    CentralizedModelIdentity,
    CentralizedTestScoringIdentity,
    CentralizedThresholdIdentity,
    CheckpointIdentity,
    DatasetSourceIdentity,
    FeatureSchemaIdentity,
    FittedPreprocessorIdentity,
    SplitIdentity,
    TemporalWindowIdentity,
    ThresholdIdentity,
    TrainingIdentity,
)
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
    ArtifactSchemaVersion,
    CalibrationScoreArtifactId,
    CheckpointId,
    StageFingerprint,
)
from datp_core.domain.data.datasets import Dataset, DatasetSourceInspectionResult, DatasetSpec, Regime
from datp_core.domain.data.partitioning import (
    ClientDefinitionStrategy,
    ClientPartitionResult,
    NaturalDevicePartitionSpec,
)
from datp_core.domain.data.preprocessing import (
    FittedPreprocessorResult,
    FittedStatisticPolicy,
    NormalizationScope,
    NormalizationStrategy,
    PreprocessingChunkSpec,
    PreprocessingSpec,
    ProcessedSplitResult,
)
from datp_core.domain.data.splitting import (
    BenignCalibrationSplitSpec,
    SplitCollectionSpec,
    SplitManifestResult,
    TestSplitSpec,
    TrainingSplitSpec,
)
from datp_core.domain.errors import CheckpointSelectionError, DomainValidationError, EvaluationError
from datp_core.domain.evaluation.alert_burden import (
    BootstrapResampleCount,
    CalibrationSampleCount,
    ConfusionCount,
)
from datp_core.domain.evaluation.operating_points import EligibleClientSet
from datp_core.domain.evaluation.statistical_results import (
    AuRocScore,
    ClaimOutcome,
    ConfidenceLevel,
    StatisticalAnalysisSpec,
    StatisticalMethod,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.experiments.specifications import CentralizedModelComparatorSpec
from datp_core.domain.learning import scores as learning_scores
from datp_core.domain.learning.checkpoints import (
    EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE,
    REGIME_A_SELECTION_RULE_VERSION,
    CheckpointCandidateResult,
    CheckpointDescriptor,
    CheckpointSchedule,
    CheckpointSelectionSpec,
    CheckpointSelectionStrategy,
    RegimeASelectionDiagnostics,
)
from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.scores import (
    CalibrationScoreArtifactSet,
    CalibrationScoringLineage,
    ClientCalibrationScoreArtifact,
    ClientCalibrationScoreMap,
    ClientEvaluationMap,
    ClientMap,
    ClientMapEntry,
    ClientRoster,
    ClientTestScoreArtifact,
    ClientTestScoreMap,
    QuantileEstimatorType,
    ScoreGenerationSpec,
    ScoreSampleCount,
    ScoringBatchSpec,
    ThresholdAssignmentSet,
)
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
from datp_core.domain.runtime.admissibility import BatchSize, ChunkRowCount, GradientAccumulationSteps, WorkerCount
from datp_core.domain.runtime.seeds import DataLoaderSeedPlan, RoundNumber, Seed
from datp_core.domain.thresholding.policies import (
    CoreThresholdPolicy,
    FprTarget,
    SharedThresholdConstruction,
    SharedThresholdSpec,
    ThresholdAssignment,
    ThresholdConstructionKind,
    ThresholdPercentile,
    ThresholdValue,
)
from datp_core.infrastructure.learning.centralized.trainer import CentralizedTorchTrainer
from tests.support.runtime_orchestration import runtime_profile
from tests.support.score_artifacts import (
    ScoreLineageContextRequest,
    calibration_scores_and_eligible_clients,
    score_lineage_context,
)


def _fingerprint(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _dataloader_seed_plan() -> DataLoaderSeedPlan:
    return DataLoaderSeedPlan(
        shuffle_seed=Seed(value=11),
        sampler_seed=Seed(value=12),
        worker_seed=Seed(value=13),
        client_seed=Seed(value=14),
        epoch_seed=Seed(value=15),
        round_seed=Seed(value=16),
        worker_count=WorkerCount(value=0),
    )


def _artifact_ref(*, character: str, artifact_type: ArtifactType) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _checkpoint_selection_spec() -> CheckpointSelectionSpec:
    return CheckpointSelectionSpec(
        strategy=CheckpointSelectionStrategy.REGIME_A_GLOBAL_PRIMARY,
        candidate_rounds=tuple(RoundNumber(value=value) for value in (25, 50, 75, 100, 125, 150, 200)),
        selection_rule_version=REGIME_A_SELECTION_RULE_VERSION,
        tie_break_rule=EARLIEST_SCHEDULED_ROUND_TIE_BREAK_RULE,
    )


def _candidate(*, round_value: int, loss: float, accepted: bool = True) -> CheckpointCandidateResult:
    return CheckpointCandidateResult(
        round=RoundNumber(value=round_value),
        regime_a_evidence_identity=_fingerprint("a"),
        allowed_diagnostics=RegimeASelectionDiagnostics(weighted_benign_validation_reconstruction_mse=loss),
        accepted=accepted,
        rejection_reason=None if accepted else "candidate rejected",
    )


def test_checkpoint_selector_uses_lowest_regime_a_loss_then_earliest_round() -> None:
    result = CheckpointSelector().select(
        CheckpointSelectionRequest(
            specification=_checkpoint_selection_spec(),
            candidates=(
                _candidate(round_value=25, loss=0.8),
                _candidate(round_value=50, loss=0.4),
                _candidate(round_value=75, loss=0.4),
                _candidate(round_value=100, loss=0.7),
                _candidate(round_value=125, loss=0.9),
                _candidate(round_value=150, loss=1.0),
                _candidate(round_value=200, loss=1.1, accepted=False),
            ),
        )
    )

    assert result.selected_round == RoundNumber(value=50)
    assert result.tie_break_evidence.tied_rounds == (RoundNumber(value=50), RoundNumber(value=75))
    assert result.prohibited_input_attestation is True


def test_checkpoint_selector_rejects_incomplete_schedule_before_deciding() -> None:
    with pytest.raises(CheckpointSelectionError):
        CheckpointSelector().select(
            CheckpointSelectionRequest(
                specification=_checkpoint_selection_spec(),
                candidates=(_candidate(round_value=25, loss=0.1),),
            )
        )


class _FederatedTrainerDouble(FederatedTrainer):
    def __init__(self) -> None:
        self.request: TrainFederatedModelRequest | None = None

    def train(self, request: TrainFederatedModelRequest) -> TrainingRunResult:
        self.request = request
        return TrainingRunResult(checkpoints=())


class _CentralizedTrainerDouble(CentralizedModelTrainer):
    def __init__(self) -> None:
        self.request: TrainCentralizedModelRequest | None = None

    def train(self, request: TrainCentralizedModelRequest) -> CentralizedTrainingRunResult:
        self.request = request
        return CentralizedTrainingRunResult(
            checkpoint_identity=request.comparator.checkpoint_identity,
            checkpoint_artifact=_artifact_ref(character="a", artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT),
        )


def _processed_splits() -> ProcessedSplitResult:
    return ProcessedSplitResult(
        artifacts=(_artifact_ref(character="a", artifact_type=ArtifactType.PROCESSED_SPLIT),),
        split_manifest_identity=SplitIdentity(value=_fingerprint("b")),
        preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("c")),
        source_row_lineage=(DatasetSourceIdentity(value=_fingerprint("d")),),
    )


def _training_specification() -> TrainingSpec:
    batch_size = BatchSize(value=8)
    return TrainingSpec(
        seed=Seed(value=1),
        autoencoder=AutoencoderSpec(
            input_dim=4,
            hidden_dims=(2,),
            bottleneck_dim=1,
            activation=ActivationFunction.RELU,
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
        training_batch=TrainingBatchSpec(
            micro_batch_size=batch_size,
            gradient_accumulation_steps=GradientAccumulationSteps(value=1),
            effective_batch_size=batch_size,
            dataloader_batch_size=batch_size,
            client_batch_partitioning=ClientBatchPartitioning.WHOLE_CLIENT,
            optimizer_step_semantics=OptimizerStepSemantics.AFTER_GRADIENT_ACCUMULATION,
        ),
        precision=PrecisionMode.FP32,
        determinism=DeterminismLevel.STRICT,
        personalization=ModelPersonalizationStrategy.NONE,
    )


def _centralized_comparator() -> CentralizedModelComparatorSpec:
    return CentralizedModelComparatorSpec(
        model_identity=CentralizedModelIdentity(value=_fingerprint("e")),
        checkpoint_identity=CentralizedCheckpointIdentity(value=_fingerprint("f")),
        calibration_score_identity=CentralizedCalibrationScoringIdentity(value=_fingerprint("0")),
        test_score_identity=CentralizedTestScoringIdentity(value=_fingerprint("1")),
        threshold_identity=CentralizedThresholdIdentity(value=_fingerprint("2")),
        evaluation_identity=CentralizedEvaluationIdentity(value=_fingerprint("3")),
    )


def test_train_model_dispatches_only_by_the_resolved_stage_request_variant() -> None:
    federated_trainer = _FederatedTrainerDouble()
    centralized_trainer = _CentralizedTrainerDouble()
    processed_splits = _processed_splits()

    federated_result = train_model(
        request=FederatedTrainingStageRequest(
            processed_splits=processed_splits,
            training=_training_specification(),
            checkpoint_schedule=_checkpoint_schedule(),
            resolved_batch_profile=runtime_profile(),
            dataloader_seed_plan=_dataloader_seed_plan(),
            compatible_recovery=None,
        ),
        federated_trainer=federated_trainer,
        centralized_trainer=centralized_trainer,
    )
    centralized_result = train_model(
        request=CentralizedTrainingStageRequest(
            processed_splits=processed_splits,
            comparator=_centralized_comparator(),
        ),
        federated_trainer=federated_trainer,
        centralized_trainer=centralized_trainer,
    )

    assert isinstance(federated_result, TrainingRunResult)
    assert isinstance(centralized_result, CentralizedTrainingRunResult)
    assert federated_result.checkpoints == ()
    assert centralized_result.checkpoint_identity == _centralized_comparator().checkpoint_identity
    assert federated_trainer.request is not None
    assert centralized_trainer.request is not None
    assert federated_trainer.request.processed_splits == processed_splits
    assert centralized_trainer.request.processed_splits == processed_splits


def test_centralized_trainer_emits_only_the_centralized_checkpoint_identity() -> None:
    request = TrainCentralizedModelRequest(
        processed_splits=_processed_splits(),
        comparator=_centralized_comparator(),
    )
    trainer = CentralizedTorchTrainer(checkpoint_stager=_CentralizedCheckpointStager())

    result = trainer.train(request)

    assert result.checkpoint_identity == request.comparator.checkpoint_identity
    assert result.checkpoint_artifact.artifact_type is ArtifactType.SCIENTIFIC_CHECKPOINT


def test_centralized_trainer_rejects_a_federated_checkpoint_identity() -> None:
    comparator = _centralized_comparator()
    object.__setattr__(comparator, "checkpoint_identity", CheckpointIdentity(value=_fingerprint("a")))
    trainer = CentralizedTorchTrainer(checkpoint_stager=_CentralizedCheckpointStager())

    with pytest.raises(DomainValidationError, match="centralized training result"):
        trainer.train(TrainCentralizedModelRequest(processed_splits=_processed_splits(), comparator=comparator))


def _checkpoint_schedule() -> CheckpointSchedule:
    return CheckpointSchedule(rounds=_checkpoint_selection_spec().candidate_rounds)


class _PortDoubleError(Exception):
    pass


class _CentralizedCheckpointStager:
    def stage(self, request: TrainCentralizedModelRequest) -> ArtifactRef:
        return _artifact_ref(character="b", artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT)


class _DatasetInspectorDouble(DatasetSourceInspector):
    def __init__(self) -> None:
        self.request: InspectDatasetSourceRequest | None = None

    def inspect(self, request: InspectDatasetSourceRequest) -> DatasetSourceInspectionResult:
        self.request = request
        raise _PortDoubleError


class _ClientPartitionerDouble:
    def __init__(self) -> None:
        self.request: ClientPartitionRequest | None = None

    def partition(self, request: ClientPartitionRequest) -> ClientPartitionResult:
        self.request = request
        raise _PortDoubleError


class _SplitManifestBuilderDouble(SplitManifestBuilder):
    def __init__(self) -> None:
        self.request: BuildSplitManifestRequest | None = None

    def build(self, request: BuildSplitManifestRequest) -> SplitManifestResult:
        self.request = request
        raise _PortDoubleError


class _PreprocessorFitterDouble(PreprocessorFitter):
    def __init__(self) -> None:
        self.request: FitPreprocessorRequest | None = None

    def fit(self, request: FitPreprocessorRequest) -> FittedPreprocessorResult:
        self.request = request
        raise _PortDoubleError


class _MaterializerDouble(ProcessedSplitMaterializer):
    def __init__(self) -> None:
        self.request: MaterializeProcessedSplitsRequest | None = None

    def materialize(self, request: MaterializeProcessedSplitsRequest) -> ProcessedSplitResult:
        self.request = request
        raise _PortDoubleError


def _stage_data_inputs() -> tuple[
    DatasetSpec,
    DatasetSourceInspectionResult,
    ClientPartitionResult,
    SplitCollectionSpec,
    SplitManifestResult,
    PreprocessingSpec,
    FittedPreprocessorResult,
]:
    client = ClientId(value="client-a")
    partition_identity = artifact_lineage.PartitionIdentity(value=_fingerprint("e"))
    split_collection = SplitCollectionSpec(
        training=TrainingSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint("f")), partition_identity=partition_identity
        ),
        calibration=BenignCalibrationSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint("0")), partition_identity=partition_identity
        ),
        test=TestSplitSpec(
            split_identity=SplitIdentity(value=_fingerprint("1")), partition_identity=partition_identity
        ),
    )
    inspection = DatasetSourceInspectionResult(
        source_manifest=_artifact_ref(character="2", artifact_type=ArtifactType.SOURCE_INSPECTION),
        feature_schema_manifest=_artifact_ref(character="3", artifact_type=ArtifactType.FEATURE_SCHEMA_MANIFEST),
        source_row_identity=DatasetSourceIdentity(value=_fingerprint("4")),
        timestamp_evidence=None,
    )
    partition = ClientPartitionResult(
        partition_manifest=_artifact_ref(character="5", artifact_type=ArtifactType.PARTITION_MANIFEST),
        client_roster=ClientRoster(client_ids=(client,)),
        partition_identity=partition_identity,
    )
    split_manifest = SplitManifestResult(
        split_manifest=_artifact_ref(character="6", artifact_type=ArtifactType.SPLIT_MANIFEST),
        split_identities=split_collection,
        partition_identity=partition_identity,
    )
    fitted_preprocessor = FittedPreprocessorResult(
        artifact=_artifact_ref(character="7", artifact_type=ArtifactType.FITTED_PREPROCESSOR),
        identity=FittedPreprocessorIdentity(value=_fingerprint("8")),
        training_row_order_checksum="training-order",
    )
    preprocessing = PreprocessingSpec(
        strategy=NormalizationStrategy.MIN_MAX,
        scope=NormalizationScope.GLOBAL_TRAIN,
        fitted_stat_policy=FittedStatisticPolicy.EXACT_TWO_PASS,
        chunking=PreprocessingChunkSpec(
            source_scan_batch_rows=ChunkRowCount(value=8),
            preprocessing_chunk_rows=ChunkRowCount(value=8),
            parquet_write_batch_rows=ChunkRowCount(value=8),
        ),
    )
    return (
        DatasetSpec(
            dataset=Dataset.N_BAIOT,
            input_dim=4,
            feature_schema_identity=FeatureSchemaIdentity(value=_fingerprint("9")),
            feature_count_verified=True,
        ),
        inspection,
        partition,
        split_collection,
        split_manifest,
        preprocessing,
        fitted_preprocessor,
    )


def test_data_stage_functions_build_a_named_request_for_each_port_double() -> None:
    dataset, inspection, partition, splits, split_manifest, preprocessing, fitted_preprocessor = _stage_data_inputs()
    inspector = _DatasetInspectorDouble()
    partitioner = _ClientPartitionerDouble()
    builder = _SplitManifestBuilderDouble()
    fitter = _PreprocessorFitterDouble()
    materializer = _MaterializerDouble()

    with pytest.raises(_PortDoubleError):
        inspect_dataset(inspector=inspector, dataset=dataset)
    with pytest.raises(_PortDoubleError):
        partition_clients(
            partitioner=partitioner,
            inspection=inspection,
            partitioning=NaturalDevicePartitionSpec(
                strategy=ClientDefinitionStrategy.NATURAL_DEVICE,
                regime=Regime.A,
            ),
        )
    with pytest.raises(_PortDoubleError):
        build_splits(builder=builder, partition=partition, splits=splits)
    with pytest.raises(_PortDoubleError):
        fit_preprocessor(fitter=fitter, split_manifest=split_manifest, preprocessing=preprocessing)
    with pytest.raises(_PortDoubleError):
        materialize_splits(
            materializer=materializer,
            split_manifest=split_manifest,
            fitted_preprocessor=fitted_preprocessor,
        )

    assert inspector.request == InspectDatasetSourceRequest(dataset=dataset)
    assert partitioner.request is not None and partitioner.request.inspection == inspection
    assert builder.request is not None and builder.request.partition == partition
    assert fitter.request is not None and fitter.request.split_manifest == split_manifest
    assert materializer.request is not None and materializer.request.fitted_preprocessor == fitted_preprocessor


class _ScoreGeneratorDouble(ScoreGenerator):
    def __init__(self) -> None:
        self.calibration_request: GenerateCalibrationScoresRequest | None = None
        self.test_request: GenerateTestScoresRequest | None = None
        self.temporal_request: GenerateTemporalScoresRequest | None = None

    def generate_calibration_scores(self, request: GenerateCalibrationScoresRequest):
        self.calibration_request = request
        raise _PortDoubleError

    def generate_test_scores(self, request: GenerateTestScoresRequest):
        self.test_request = request
        raise _PortDoubleError

    def generate_temporal_scores(self, request: GenerateTemporalScoresRequest):
        self.temporal_request = request
        raise _PortDoubleError


def _checkpoint_descriptor() -> CheckpointDescriptor:
    checkpoint_reference = _artifact_ref(character="a", artifact_type=ArtifactType.SCIENTIFIC_CHECKPOINT)
    return CheckpointDescriptor(
        checkpoint_id=CheckpointId(value="checkpoint-" + "a" * 64),
        round=RoundNumber(value=25),
        seed=Seed(value=1),
        training_identity=TrainingIdentity(value=_fingerprint("b")),
        artifact_ref=checkpoint_reference,
        content_hash="a" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
    )


def _scoring_specification() -> ScoreGenerationSpec:
    batch_size = BatchSize(value=8)
    return ScoreGenerationSpec(
        scoring_batch=ScoringBatchSpec(
            calibration_batch_size=batch_size,
            test_batch_size=batch_size,
            temporal_batch_size=batch_size,
        ),
        precision=PrecisionMode.FP32,
        numeric_equivalence_policy="exact-fp32",
    )


def test_score_stage_functions_build_role_specific_requests_for_the_score_port_double() -> None:
    generator = _ScoreGeneratorDouble()
    processed_splits = _processed_splits()
    checkpoint = _checkpoint_descriptor()
    scoring = _scoring_specification()
    window_identity = TemporalWindowIdentity(value=_fingerprint("c"))

    with pytest.raises(_PortDoubleError):
        generate_calibration_scores(
            generator=generator,
            processed_splits=processed_splits,
            checkpoint=checkpoint,
            scoring=scoring,
        )
    with pytest.raises(_PortDoubleError):
        generate_test_scores(
            generator=generator,
            processed_splits=processed_splits,
            checkpoint=checkpoint,
            scoring=scoring,
        )
    with pytest.raises(_PortDoubleError):
        generate_temporal_scores(
            GenerateTemporalScoresStageRequest(
                generator=generator,
                processed_splits=processed_splits,
                checkpoint=checkpoint,
                scoring=scoring,
                window_identity=window_identity,
            )
        )

    assert generator.calibration_request is not None
    assert generator.test_request is not None
    assert generator.temporal_request is not None
    assert generator.temporal_request.window_identity == window_identity


class _ThresholdConstructorDouble(ThresholdConstructor):
    def __init__(self) -> None:
        self.request: ConstructThresholdsRequest | None = None

    def construct(self, request: ConstructThresholdsRequest):
        self.request = request
        raise _PortDoubleError


class _StatisticsRunnerDouble(StatisticalProcedureRunner):
    def __init__(self) -> None:
        self.request: RunStatisticalAnalysisRequest | None = None

    def run(self, request: RunStatisticalAnalysisRequest):
        self.request = request
        raise _PortDoubleError


def test_threshold_and_statistics_stages_build_named_requests_for_port_doubles() -> None:
    constructor = _ThresholdConstructorDouble()
    runner = _StatisticsRunnerDouble()
    calibration_scores, eligible_clients = calibration_scores_and_eligible_clients()
    construction = SharedThresholdSpec(
        kind=ThresholdConstructionKind.SHARED,
        percentile=ThresholdPercentile(value=0.95),
        construction=SharedThresholdConstruction.MEAN,
        estimator=QuantileEstimatorType.LOCAL_EXACT,
    )
    assignment_metadata = ThresholdAssignmentMetadata(
        policy=CoreThresholdPolicy.B1,
        threshold_identity=ThresholdIdentity(value=_fingerprint("a")),
        fallback_fingerprint=_fingerprint("b"),
        fpr_target=FprTarget.from_percentile(percentile=construction.percentile),
    )
    analysis = StatisticalAnalysisSpec(
        method=StatisticalMethod.BCA_BOOTSTRAP,
        confidence=ConfidenceLevel(value=0.95),
        resamples=BootstrapResampleCount(value=10),
        paired_seed_count=10,
    )

    with pytest.raises(_PortDoubleError):
        construct_thresholds(
            constructor=constructor,
            request=ConstructThresholdsRequest(
                calibration_scores=calibration_scores,
                construction=construction,
                eligible_clients=eligible_clients,
                assignment_metadata=assignment_metadata,
            ),
        )
    with pytest.raises(_PortDoubleError):
        analyze_statistics(
            runner=runner,
            analysis=analysis,
            input_artifacts=ArtifactReferenceCollection(references=()),
        )

    assert constructor.request is not None and constructor.request.calibration_scores == calibration_scores
    assert constructor.request.assignment_metadata == assignment_metadata
    assert runner.request is not None and runner.request.analysis == analysis


@dataclass(frozen=True, slots=True, kw_only=True)
class _EvaluationFixture:
    client: ClientId
    roster: ClientRoster
    split_identity: SplitIdentity
    checkpoint_identity: CheckpointIdentity
    preprocessor_identity: FittedPreprocessorIdentity
    schema_identity: FeatureSchemaIdentity
    test_scoring_identity: artifact_lineage.TestScoringIdentity


def evaluation_request() -> EvaluatePolicyRequest:
    fixture = _evaluation_fixture()
    eligible_client_set = _eligible_client_set(fixture)
    return EvaluatePolicyRequest(
        policy=CoreThresholdPolicy.B1,
        evaluation_identity=_fingerprint("c"),
        score_set=_test_score_set(fixture),
        assignment=_threshold_assignment(fixture, eligible_client_set),
        eligible_client_set=eligible_client_set,
        confusion_evidence=_confusion_evidence(fixture),
        auroc_control=AuRocScore(value=0.9),
        zero_mean_cv_wording_outcome=ClaimOutcome.NULL,
        cluster_dispersion=None,
    )


def _evaluation_fixture() -> _EvaluationFixture:
    client = ClientId(value="client-a")
    return _EvaluationFixture(
        client=client,
        roster=ClientRoster(client_ids=(client,)),
        split_identity=SplitIdentity(value=_fingerprint("b")),
        checkpoint_identity=CheckpointIdentity(value=_fingerprint("c")),
        preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("d")),
        schema_identity=FeatureSchemaIdentity(value=_fingerprint("e")),
        test_scoring_identity=artifact_lineage.TestScoringIdentity(value=_fingerprint("f")),
    )


def _test_score_set(fixture: _EvaluationFixture) -> learning_scores.TestScoreArtifactSet:
    benign_reference = _artifact_ref(character="1", artifact_type=ArtifactType.TEST_SCORE_SET)
    attack_reference = _artifact_ref(character="2", artifact_type=ArtifactType.TEST_SCORE_SET)
    test_artifact = ClientTestScoreArtifact(
        client_id=fixture.client,
        test_split_identity=fixture.split_identity,
        split_manifest_hash="3" * 64,
        test_scoring_identity=fixture.test_scoring_identity,
        scientific_checkpoint_identity=fixture.checkpoint_identity,
        scientific_checkpoint_content_hash="4" * 64,
        fitted_preprocessor_identity=fixture.preprocessor_identity,
        feature_schema_identity=fixture.schema_identity,
        benign_scores_ref=benign_reference,
        benign_sample_count=ScoreSampleCount(value=10),
        benign_content_hash="1" * 64,
        benign_row_order_checksum="benign-order",
        attack_scores_ref=attack_reference,
        attack_sample_count=ScoreSampleCount(value=5),
        attack_content_hash="2" * 64,
        attack_row_order_checksum="attack-order",
        aggregate_manifest_hash="5" * 64,
        score_schema_version=ArtifactSchemaVersion(value="v1"),
    )
    return learning_scores.TestScoreArtifactSet(
        artifact_id=artifact_references.TestScoreArtifactId(value="artifact-" + "6" * 64),
        lineage=learning_scores.TestScoringLineage(
            scoring_identity=fixture.test_scoring_identity,
            context=score_lineage_context(
                ScoreLineageContextRequest(
                    roster=fixture.roster,
                    split_identity=fixture.split_identity,
                    checkpoint_identity=fixture.checkpoint_identity,
                    checkpoint_content_hash="4" * 64,
                    preprocessor_identity=fixture.preprocessor_identity,
                    schema_identity=fixture.schema_identity,
                    row_order_checksum="test-order",
                )
            ),
        ),
        per_client=ClientTestScoreMap(
            values=ClientMap(
                roster=fixture.roster,
                entries=(ClientMapEntry(client_id=fixture.client, value=test_artifact),),
            )
        ),
    )


def _eligible_client_set(fixture: _EvaluationFixture) -> EligibleClientSet:
    return EligibleClientSet(
        roster=fixture.roster,
        protocol_eligibility_rule_identity=_fingerprint("7"),
        eligible_clients=(fixture.client,),
        ineligible_reasons=(),
        identity=_fingerprint("8"),
    )


def _threshold_assignment(fixture: _EvaluationFixture, eligible_client_set: EligibleClientSet) -> ThresholdAssignment:
    return ThresholdAssignment(
        policy=CoreThresholdPolicy.B1,
        per_client_tau=ThresholdAssignmentSet(
            values=ClientMap(
                roster=fixture.roster,
                entries=(ClientMapEntry(client_id=fixture.client, value=ThresholdValue(value=0.5)),),
            )
        ),
        calibration_score_artifact_id=CalibrationScoreArtifactId(value="artifact-" + "9" * 64),
        threshold_identity=ThresholdIdentity(value=_fingerprint("a")),
        eligible_client_set_identity=eligible_client_set.identity,
        fallback_fingerprint=_fingerprint("b"),
    )


def _confusion_evidence(fixture: _EvaluationFixture) -> ClientEvaluationMap[ClientConfusionEvidence]:
    return ClientEvaluationMap(
        values=ClientMap(
            roster=fixture.roster,
            entries=(
                ClientMapEntry(
                    client_id=fixture.client,
                    value=ClientConfusionEvidence(
                        true_positive=ConfusionCount(value=4),
                        false_positive=ConfusionCount(value=2),
                        true_negative=ConfusionCount(value=8),
                        false_negative=ConfusionCount(value=1),
                        calibration_sample_count=CalibrationSampleCount(value=100),
                    ),
                ),
            ),
        )
    )


def test_policy_evaluator_uses_the_committed_test_aggregate_and_counts() -> None:
    result = PolicyEvaluator().evaluate(evaluation_request())

    assert result.client_results[0].false_positive_rate.value == 0.2
    assert result.client_results[0].true_positive_rate.value == 0.8
    assert result.fleet_detection.auroc_control == AuRocScore(value=0.9)


def test_policy_evaluator_rejects_a_calibration_score_set_in_the_test_position() -> None:
    request = evaluation_request()
    client = request.eligible_client_set.roster.client_ids[0]
    calibration_score_set = CalibrationScoreArtifactSet(
        artifact_id=CalibrationScoreArtifactId(value="artifact-" + "d" * 64),
        lineage=CalibrationScoringLineage(
            scoring_identity=CalibrationScoringIdentity(value=_fingerprint("e")),
            context=score_lineage_context(
                ScoreLineageContextRequest(
                    roster=request.eligible_client_set.roster,
                    split_identity=SplitIdentity(value=_fingerprint("3")),
                    checkpoint_identity=CheckpointIdentity(value=_fingerprint("f")),
                    checkpoint_content_hash="0" * 64,
                    preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("1")),
                    schema_identity=FeatureSchemaIdentity(value=_fingerprint("2")),
                    row_order_checksum="calibration-order",
                )
            ),
        ),
        per_client=ClientCalibrationScoreMap(
            values=ClientMap(
                roster=request.eligible_client_set.roster,
                entries=(
                    ClientMapEntry(
                        client_id=client,
                        value=ClientCalibrationScoreArtifact(
                            client_id=client,
                            calibration_split_identity=SplitIdentity(value=_fingerprint("3")),
                            split_manifest_hash="4" * 64,
                            scoring_identity=CalibrationScoringIdentity(value=_fingerprint("e")),
                            scientific_checkpoint_identity=CheckpointIdentity(value=_fingerprint("f")),
                            scientific_checkpoint_content_hash="0" * 64,
                            fitted_preprocessor_identity=FittedPreprocessorIdentity(value=_fingerprint("1")),
                            feature_schema_identity=FeatureSchemaIdentity(value=_fingerprint("2")),
                            sample_count=ScoreSampleCount(value=100),
                            schema_version=ArtifactSchemaVersion(value="v1"),
                            content_hash="5" * 64,
                            row_order_checksum="calibration-order",
                            artifact_ref=_artifact_ref(character="5", artifact_type=ArtifactType.CALIBRATION_SCORE_SET),
                        ),
                    ),
                ),
            )
        ),
    )
    object.__setattr__(request, "score_set", calibration_score_set)

    with pytest.raises(EvaluationError, match="test-role score aggregate"):
        PolicyEvaluator().evaluate(request)
