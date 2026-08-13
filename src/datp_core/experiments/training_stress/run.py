from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

import numpy as np
import polars as pl
from pydantic import TypeAdapter, ValidationError

from datp_core.analysis.evidence import SeedEvidenceAssetName
from datp_core.analysis.mechanisms import (
    AbsorptionCohortResult,
    AbsorptionCornerEvidence,
    AbsorptionFourCornerEvidence,
    AbsorptionSeedObservation,
    decide_absorption_cohort,
)
from datp_core.analysis.mechanisms.model_alignment import (
    AlignmentReductionOutcome,
    ModelAlignmentClientScores,
    ModelAlignmentCondition,
    ModelAlignmentMetric,
    ModelAlignmentResult,
    alignment_reductions,
    fedavg_alignment_grid_for_scores,
    model_alignment,
)
from datp_core.analysis.metrics.cohort_construction import assert_cohort_invariant_to_threshold_methods
from datp_core.analysis.metrics.cohort_evidence import client_partition_counts_from_scores
from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.models import ClientMetricResult, MetricStatus, PopulationMetricResult, metric_by_id
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.app.planning import PlanDisposition, PlanningEvidence, PlanReason, expand_experiment_plan
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.artifacts.repositories.thresholds import (
    FederatedThresholdConstructionRequest,
    construct_and_publish_federated_thresholds,
)
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.artifacts.serializers.safetensors import save_state_dict_tensors
from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ClientIdentityToken,
    ContractSubject,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FeatureNameSequence,
    FederatedThresholdMethod,
    FileContentText,
    MetricId,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ScoreFrameColumn,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    CampaignOrdinal,
    ClientCount,
    DittoRegularization,
    ElapsedSeconds,
    MetricValue,
    ModelCoefficientValue,
    ProximalCoefficient,
    RowCount,
    ScoreValue,
    Seed,
    SeedObservationCount,
    ThresholdValue,
)
from datp_core.data.populations.contracts import ClientIdentity, FamilyAssignment
from datp_core.data.populations.declarations import split_protocol_for_population
from datp_core.data.populations.publication import ConstructDeclaredPopulationRequest, construct_declared_population
from datp_core.data.preprocessing.models import FederatedPreprocessingOutcome, FederatedPreprocessingRequest
from datp_core.data.preprocessing.service import preprocess_federated
from datp_core.data.registry import population_capabilities
from datp_core.detector.checkpoints.history import history_frames
from datp_core.detector.checkpoints.identities import FederatedHistoryColumn
from datp_core.detector.checkpoints.protocols import DIAGNOSTIC_SNAPSHOT_PROTOCOL
from datp_core.detector.scoring.federated import publish_federated_scores
from datp_core.detector.scoring.models import (
    FederatedScoreArtifactManifest,
    GenerateFederatedScoresRequest,
    TerminalFederatedScoringModel,
)
from datp_core.detector.training.contracts import (
    ModelAbsorptionDecisionProtocol as DetectorModelAbsorptionDecisionProtocol,
)
from datp_core.detector.training.ditto import DittoTrainingRequest
from datp_core.detector.training.ditto_publication import (
    TrainDittoDetectorRequest,
    TrainDittoDetectorResult,
    train_ditto_detector,
)
from datp_core.detector.training.engine import SerializedStateEvidence
from datp_core.detector.training.fine_tuning import (
    FineTunedTerminalModel,
    PersistedFedAvgFineTuningRequest,
    fine_tune_from_persisted_fedavg,
)
from datp_core.detector.training.models import (
    DittoTrainingCoordinates,
    FederatedTrainingCoordinate,
)
from datp_core.detector.training.protocols import (
    BATCH_SIZE,
    DITTO_ALTERNATIVE_ROUTE_DIFFERENCE,
    FEDAVG_LOCAL_FINE_TUNING_PROTOCOL,
    FEDPROX_COEFFICIENTS,
    LEARNING_RATE,
    MODEL_ABSORPTION_DECISION_PROTOCOL,
    NBAIOT_AUTOENCODER,
    resolve_ditto_protocol,
)
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.confirmatory.run import FedAvgCvFprEffectEvidence, absorption_corner_from_evaluation_document
from datp_core.experiments.execution import execute_declared_campaign
from datp_core.experiments.execution.context import (
    client_training_inputs,
    training_feature_names,
)
from datp_core.experiments.execution.evidence import load_evaluation_document
from datp_core.experiments.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    ExecutionRootDirectory,
    federated_training_directory,
)
from datp_core.experiments.execution.models import (
    CampaignEntry,
    CampaignPlan,
    ProgressEvent,
    ProgressEventKind,
    ProgressHook,
)
from datp_core.experiments.personalized_scoring import client_metric, client_scoring_input, score_record_for_client
from datp_core.experiments.registry import EXPERIMENTS
from datp_core.presentation.export import export_mechanism_publication
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically
from datp_core.thresholds.dispatch import ThresholdConstructionRequest
from datp_core.thresholds.policies.local import LocalThresholdResult
from datp_core.thresholds.policies.shared import SharedThresholdResult
from datp_core.thresholds.protocols import CANONICAL_QUANTILE, MINIMUM_BENIGN_SUPPORT, CalibrationSupportRule
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores

_MODEL_ABSORPTION_DECISION_PROTOCOL = DetectorModelAbsorptionDecisionProtocol.model_validate(
    MODEL_ABSORPTION_DECISION_PROTOCOL.model_dump()
)


class DittoArtifactBranch(StrEnum):
    GLOBAL_MODEL = "global_model"
    PERSONALIZED_MODELS = "personalized_models"
    THRESHOLDS = "thresholds"
    EVIDENCE = "evidence"
    ANALYSIS = "analysis"


class FedProxArtifactDirectory(StrEnum):
    ANALYSIS = "analysis"


class FineTuningArtifactBranch(StrEnum):
    TERMINAL_MODELS = "terminal_models"
    SCORES = "scores"
    THRESHOLDS = "thresholds"
    EVIDENCE = "evidence"
    ANALYSIS = "analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoStressTestResult:
    personalized_coordinate: FederatedTrainingCoordinate
    alignment: ModelAlignmentResult
    reference_alignment: ModelAlignmentResult
    alignment_reductions: tuple[AlignmentReductionOutcome, ...]
    shared_threshold: SharedThresholdResult
    local_threshold: LocalThresholdResult
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]
    evaluation_cohort: EvaluationCohortManifest


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoStressTestEvidence:
    personalized_coordinate: FederatedTrainingCoordinate
    alignment: ModelAlignmentResult
    reference_alignment: ModelAlignmentResult
    alignment_reductions: tuple[AlignmentReductionOutcome, ...]
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]
    evaluation_cohort: EvaluationCohortManifest


@dataclass(frozen=True, slots=True, kw_only=True)
class FineTuningStressTestResult:
    personalized_coordinate: FederatedTrainingCoordinate
    model_evidence: tuple[FineTuningClientModelEvidence, ...]
    alignment: ModelAlignmentResult
    reference_alignment: ModelAlignmentResult
    alignment_reductions: tuple[AlignmentReductionOutcome, ...]
    shared_threshold: SharedThresholdResult
    local_threshold: LocalThresholdResult
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]
    evaluation_cohort: EvaluationCohortManifest


@dataclass(frozen=True, slots=True, kw_only=True)
class FineTuningStressTestEvidence:
    personalized_coordinate: FederatedTrainingCoordinate
    model_evidence: tuple[FineTuningClientModelEvidence, ...]
    alignment: ModelAlignmentResult
    reference_alignment: ModelAlignmentResult
    alignment_reductions: tuple[AlignmentReductionOutcome, ...]
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]
    evaluation_cohort: EvaluationCohortManifest


@dataclass(frozen=True, slots=True, kw_only=True)
class FineTuningClientModelEvidence:
    client: ClientIdentity
    serialized_state_evidence: SerializedStateEvidence
    wall_time: ElapsedSeconds


def _persist_ditto_evidence(
    evidence: DittoStressTestEvidence,
    *,
    training_seed: Seed,
    regularization: DittoRegularization,
    output_root: Path,
) -> None:
    directory = ditto_directory(training_seed, regularization, DittoArtifactBranch.EVIDENCE, output_root)
    directory.mkdir(parents=True, exist_ok=True)
    write_text_atomically(
        directory / SeedEvidenceAssetName.DOCUMENT,
        FileContentText(canonical_json_text(evidence)),
    )


def load_ditto_stress_test_evidence(
    *,
    training_seed: Seed,
    regularization: DittoRegularization,
    output_root: Path,
) -> DittoStressTestEvidence:
    directory = ditto_directory(training_seed, regularization, DittoArtifactBranch.EVIDENCE, output_root)
    document = directory / SeedEvidenceAssetName.DOCUMENT
    if not document.is_file():
        raise ScientificContractError(
            ErrorMessage(
                f"missing Ditto stress-test evidence: {directory} "
                f"(seed={training_seed.value} regularization={regularization.value})"
            ),
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
    adapter: TypeAdapter[DittoStressTestEvidence] = TypeAdapter(DittoStressTestEvidence)
    try:
        evidence = adapter.validate_json(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as error:
        raise ScientificContractError(
            ErrorMessage(f"Ditto stress-test evidence is unreadable or invalid: {document}"),
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        ) from error
    return evidence


def _persist_fine_tuning_evidence(
    evidence: FineTuningStressTestEvidence,
    *,
    training_seed: Seed,
    output_root: Path,
) -> None:
    directory = fine_tuning_root(training_seed, output_root=output_root) / FineTuningArtifactBranch.EVIDENCE
    directory.mkdir(parents=True, exist_ok=True)
    write_text_atomically(directory / SeedEvidenceAssetName.DOCUMENT, FileContentText(canonical_json_text(evidence)))


def load_fine_tuning_stress_test_evidence(*, training_seed: Seed, output_root: Path) -> FineTuningStressTestEvidence:
    document = (
        fine_tuning_root(training_seed, output_root=output_root)
        / FineTuningArtifactBranch.EVIDENCE
        / SeedEvidenceAssetName.DOCUMENT
    )
    if not document.is_file():
        raise ScientificContractError(
            ErrorMessage(f"missing fine-tuning stress-test evidence: {document}"),
            subject=ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
        )
    adapter: TypeAdapter[FineTuningStressTestEvidence] = TypeAdapter(FineTuningStressTestEvidence)
    try:
        return adapter.validate_json(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as error:
        raise ScientificContractError(
            ErrorMessage(f"fine-tuning stress-test evidence is unreadable or invalid: {document}"),
            subject=ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
        ) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoPopulationContext:
    clients: tuple[ClientIdentity, ...]
    family_by_client: tuple[FamilyAssignment, ...]
    preprocessing: FederatedPreprocessingOutcome


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonalizedScoreCollection:
    eligible_calibration: tuple[ClientBenignCalibrationScores, ...]
    manifests: ClientCollection[ClientIdentity, FederatedScoreArtifactManifest]


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxStressTestResult:
    training_seed: Seed
    coefficient: ProximalCoefficient
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxAlignmentEvidence:
    training_seed: Seed
    coefficient: ProximalCoefficient
    reference_alignment: ModelAlignmentResult
    alignment: ModelAlignmentResult
    native_alignment: ModelAlignmentResult
    alignment_reductions: tuple[AlignmentReductionOutcome, ...]


@dataclass(frozen=True, slots=True)
class Terminal50ClientDrift:
    client_id: ClientIdentityToken
    rms_drift: MetricValue


@dataclass(frozen=True, slots=True)
class Terminal50DriftSummary:
    seed: Seed
    coefficient: ProximalCoefficient | None
    federation_rms_drift: MetricValue
    client_rms_drifts: tuple[Terminal50ClientDrift, ...]

    def __post_init__(self) -> None:
        if not self.client_rms_drifts:
            raise ValueError("terminal-50 drift requires one or more clients")
        if tuple(item.client_id for item in self.client_rms_drifts) != tuple(
            sorted((item.client_id for item in self.client_rms_drifts), key=lambda identity: identity.value)
        ):
            raise ValueError("terminal-50 client drifts must be ordered by client identity")


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxCvFprCornerEvidence:
    seed: Seed
    coefficient: ProximalCoefficient
    shared: AbsorptionCornerEvidence
    local: AbsorptionCornerEvidence

    def __post_init__(self) -> None:
        if self.shared.seed != self.seed or self.local.seed != self.seed:
            raise ValueError("FedProx CV(FPR) corners must match the observation seed")
        if self.shared.threshold_method is not FederatedThresholdMethod.SHARED_THRESHOLD:
            raise ValueError("FedProx shared corner must use SHARED_THRESHOLD")
        if self.local.threshold_method is not FederatedThresholdMethod.LOCAL_THRESHOLD:
            raise ValueError("FedProx local corner must use LOCAL_THRESHOLD")
        if self.shared.model is not TrainingModelId.FEDPROX_AUTOENCODER:
            raise ValueError("FedProx shared corner must use FEDPROX_AUTOENCODER")
        if self.local.model is not TrainingModelId.FEDPROX_AUTOENCODER:
            raise ValueError("FedProx local corner must use FEDPROX_AUTOENCODER")
        tolerance = NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value
        for corner in (self.shared, self.local):
            if corner.coefficient is None or abs(corner.coefficient.value - self.coefficient.value) > tolerance:
                raise ValueError("FedProx corner coefficient must match the declared proximal coefficient")

    @property
    def shared_cv(self) -> MetricValue:
        return self.shared.population_cv_fpr

    @property
    def local_cv(self) -> MetricValue:
        return self.local.population_cv_fpr

    @property
    def effect(self) -> MetricValue:
        return MetricValue(self.shared_cv.value - self.local_cv.value)


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoCvFprEffectEvidence:
    shared_cv: MetricValue
    local_cv: MetricValue
    effect: MetricValue

    def __post_init__(self) -> None:
        expected_effect = self.shared_cv.value - self.local_cv.value
        if abs(self.effect.value - expected_effect) > NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value:
            raise ScientificContractError(
                ErrorMessage("Ditto CV(FPR) effect must equal the shared-minus-local population difference"),
                subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            )


def _ditto_personalized_coordinate(training_seed: Seed, regularization: DittoRegularization) -> ExperimentCoordinate:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.DITTO_ABSORPTION_STRESS_TEST)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(training_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason(
                    "the Ditto stress-test entry point supplies the locked natural-device execution prerequisites"
                ),
            ),
        ),
    )
    tolerance = NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.disposition is PlanDisposition.EXECUTABLE
        and entry.coordinate.training_model is TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER
        and entry.coordinate.model_coefficient is not None
        and abs(entry.coordinate.model_coefficient.value - regularization.value) <= tolerance
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(
                f"Ditto planning produced no unique personalized coordinate for regularization={regularization.value}"
            ),
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
    return matches[0]


def run_ditto_stress_test_seed(
    *,
    training_seed: Seed,
    regularization: DittoRegularization,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> DittoStressTestResult:
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = split_protocol_for_population(population)
    preprocessing_identity = PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    context = _population_context(
        training_seed=training_seed,
        population=population,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
    )
    coordinates = DittoTrainingCoordinates.create(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
        regularization=regularization,
    )
    personalized_coordinate = coordinates.personalized_coordinate
    progress_coordinate = _ditto_personalized_coordinate(training_seed, regularization)
    feature_names = training_feature_names(DatasetId.NBAIOT)
    training = train_ditto_detector(
        TrainDittoDetectorRequest(
            request=DittoTrainingRequest(
                coordinates=coordinates,
                clients=client_training_inputs(
                    context.preprocessing.client_publications,
                    context.clients,
                    feature_names,
                ),
                population_client_count=ClientCount(len(context.clients)),
                autoencoder=NBAIOT_AUTOENCODER,
                training_protocol=resolve_ditto_protocol(regularization),
                diagnostic_snapshot_protocol=DIAGNOSTIC_SNAPSHOT_PROTOCOL,
                training_seed=training_seed,
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                global_output_directory=ditto_directory(
                    training_seed,
                    regularization,
                    DittoArtifactBranch.GLOBAL_MODEL,
                    output_root,
                ),
                personalized_output_directory=ditto_directory(
                    training_seed,
                    regularization,
                    DittoArtifactBranch.PERSONALIZED_MODELS,
                    output_root,
                ),
                progress_callback=(
                    (
                        lambda round_value, maximum_round: progress.emit(
                            ProgressEvent(
                                kind=ProgressEventKind.TRAINING_ROUND,
                                coordinate=progress_coordinate,
                                round_number=round_value,
                                maximum_round=maximum_round,
                            )
                        )
                    )
                    if progress is not None
                    else None
                ),
            ),
        )
    )
    scores = _personalized_scores(
        training=training,
        personalized_coordinate=personalized_coordinate,
        context=context,
        feature_names=feature_names,
        training_seed=training_seed,
        regularization=regularization,
        output_root=output_root,
        overwrite=overwrite,
    )
    capabilities = population_capabilities(population)
    threshold_directory = ditto_directory(training_seed, regularization, DittoArtifactBranch.THRESHOLDS, output_root)
    shared = construct_and_publish_federated_thresholds(
        FederatedThresholdConstructionRequest(
            request=ThresholdConstructionRequest(
                method=FederatedThresholdMethod.SHARED_THRESHOLD,
                coordinate=personalized_coordinate,
                quantile=CANONICAL_QUANTILE,
                capabilities=capabilities,
                eligible=scores.eligible_calibration,
                family_by_client=context.family_by_client,
                support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
                cluster_threshold_aggregation=None,
            ),
            output_directory=threshold_directory / FederatedThresholdMethod.SHARED_THRESHOLD.value,
            overwrite=overwrite,
        )
    ).result
    local = construct_and_publish_federated_thresholds(
        FederatedThresholdConstructionRequest(
            request=ThresholdConstructionRequest(
                method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                coordinate=personalized_coordinate,
                quantile=CANONICAL_QUANTILE,
                capabilities=capabilities,
                eligible=scores.eligible_calibration,
                family_by_client=context.family_by_client,
                support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
                cluster_threshold_aggregation=None,
            ),
            output_directory=threshold_directory / FederatedThresholdMethod.LOCAL_THRESHOLD.value,
            overwrite=overwrite,
        )
    ).result
    if not isinstance(shared, SharedThresholdResult):
        raise ScientificContractError(
            ErrorMessage("Ditto shared-threshold construction must produce a shared result"),
            subject=personalized_coordinate.model,
        )
    if not isinstance(local, LocalThresholdResult):
        raise ScientificContractError(
            ErrorMessage("Ditto local-threshold construction must produce a local result"),
            subject=personalized_coordinate.model,
        )
    reference_manifest = scores.manifests.require(shared.assignments[0].client)
    evaluation_cohort = assert_cohort_invariant_to_threshold_methods(
        population=population,
        partition_seed=personalized_coordinate.training_seed,
        client_counts=client_partition_counts_from_scores(reference_manifest),
        methods=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    )
    source_coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    source_score_directory = (
        federated_training_directory(source_coordinate, output_root) / ExecutionArtifactDirectory.SCORES
    )
    source_alignment_clients = _alignment_clients_from_scores(
        score_directory=source_score_directory,
        clients=context.clients,
    )
    grid = fedavg_alignment_grid_for_scores(source_alignment_clients)
    reference_alignment = model_alignment(
        ModelAlignmentCondition(
            client_scores=source_alignment_clients,
            shared_threshold=_shared_type7_threshold(source_alignment_clients),
        ),
        grid=grid,
    )
    alignment = model_alignment(
        _alignment_condition_from_eligible(scores.eligible_calibration, shared.assignments[0].threshold),
        grid=grid,
    )
    result = DittoStressTestResult(
        personalized_coordinate=personalized_coordinate,
        alignment=alignment,
        reference_alignment=reference_alignment,
        alignment_reductions=alignment_reductions(reference_alignment, alignment),
        shared_threshold=shared,
        local_threshold=local,
        shared_threshold_metrics=tuple(
            client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.SHARED_THRESHOLD,
                scores.manifests.require(assignment.client),
                assignment,
                evaluation_cohort,
            )
            for assignment in shared.assignments
        ),
        local_threshold_metrics=tuple(
            client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                scores.manifests.require(assignment.client),
                assignment,
                evaluation_cohort,
            )
            for assignment in local.assignments
        ),
        evaluation_cohort=evaluation_cohort,
    )
    _persist_ditto_evidence(
        DittoStressTestEvidence(
            personalized_coordinate=result.personalized_coordinate,
            alignment=result.alignment,
            reference_alignment=result.reference_alignment,
            alignment_reductions=result.alignment_reductions,
            shared_threshold_metrics=result.shared_threshold_metrics,
            local_threshold_metrics=result.local_threshold_metrics,
            evaluation_cohort=result.evaluation_cohort,
        ),
        training_seed=training_seed,
        regularization=regularization,
        output_root=output_root,
    )
    return result


def run_fedavg_local_fine_tuning_stress_test_seed(
    *,
    training_seed: Seed,
    output_root: Path,
    overwrite: bool,
) -> FineTuningStressTestResult:
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = split_protocol_for_population(population)
    preprocessing_identity = PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    context = _population_context(
        training_seed=training_seed,
        population=population,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
    )
    source_coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    personalized_coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
        model=TrainingModelId.FEDAVG_LOCAL_FINE_TUNING,
        model_coefficient=None,
    )
    feature_names = training_feature_names(DatasetId.NBAIOT)
    clients = client_training_inputs(context.preprocessing.client_publications, context.clients, feature_names)
    root = fine_tuning_root(training_seed, output_root=output_root)
    model_directory = root / FineTuningArtifactBranch.TERMINAL_MODELS
    if model_directory.exists():
        if not overwrite:
            raise FileExistsError(f"fine-tuning output already exists: {model_directory}")
        rmtree(model_directory)
    models = fine_tune_from_persisted_fedavg(
        PersistedFedAvgFineTuningRequest(
            dataset=DatasetId.NBAIOT,
            source_coordinate=source_coordinate,
            source_directory=federated_training_directory(source_coordinate, output_root),
            clients=clients,
            autoencoder=NBAIOT_AUTOENCODER,
            diagnostic_snapshot_protocol=DIAGNOSTIC_SNAPSHOT_PROTOCOL,
            protocol=FEDAVG_LOCAL_FINE_TUNING_PROTOCOL,
            batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            training_seed=training_seed,
        )
    )
    model_directory.mkdir(parents=True, exist_ok=True)
    for owned in models.items:
        save_state_dict_tensors(
            owned.value.terminal_model_state.to_torch_state_dict(),
            model_directory / f"terminal_model_{owned.client.client_id.value}.safetensors",
        )
    scores = _fine_tuned_scores(
        models=models,
        personalized_coordinate=personalized_coordinate,
        context=context,
        feature_names=feature_names,
        output_directory=root / FineTuningArtifactBranch.SCORES,
        overwrite=overwrite,
    )
    capabilities = population_capabilities(population)
    threshold_directory = root / FineTuningArtifactBranch.THRESHOLDS
    shared = construct_and_publish_federated_thresholds(
        FederatedThresholdConstructionRequest(
            request=ThresholdConstructionRequest(
                method=FederatedThresholdMethod.SHARED_THRESHOLD,
                coordinate=personalized_coordinate,
                quantile=CANONICAL_QUANTILE,
                capabilities=capabilities,
                eligible=scores.eligible_calibration,
                family_by_client=context.family_by_client,
                support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
                cluster_threshold_aggregation=None,
            ),
            output_directory=threshold_directory / FederatedThresholdMethod.SHARED_THRESHOLD.value,
            overwrite=overwrite,
        )
    ).result
    local = construct_and_publish_federated_thresholds(
        FederatedThresholdConstructionRequest(
            request=ThresholdConstructionRequest(
                method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                coordinate=personalized_coordinate,
                quantile=CANONICAL_QUANTILE,
                capabilities=capabilities,
                eligible=scores.eligible_calibration,
                family_by_client=context.family_by_client,
                support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
                cluster_threshold_aggregation=None,
            ),
            output_directory=threshold_directory / FederatedThresholdMethod.LOCAL_THRESHOLD.value,
            overwrite=overwrite,
        )
    ).result
    if not isinstance(shared, SharedThresholdResult) or not isinstance(local, LocalThresholdResult):
        raise ScientificContractError(
            ErrorMessage("fine-tuning stress test must produce shared and local threshold results"),
            subject=personalized_coordinate.model,
        )
    reference_manifest = scores.manifests.require(shared.assignments[0].client)
    evaluation_cohort = assert_cohort_invariant_to_threshold_methods(
        population=population,
        partition_seed=training_seed,
        client_counts=client_partition_counts_from_scores(reference_manifest),
        methods=(FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD),
    )
    fine_alignment_condition = _alignment_condition_from_scores(
        score_directory=root / FineTuningArtifactBranch.SCORES,
        clients=context.clients,
        shared_threshold=shared.assignments[0].threshold,
    )
    source_score_directory = (
        federated_training_directory(source_coordinate, output_root) / ExecutionArtifactDirectory.SCORES
    )
    source_alignment_clients = _alignment_clients_from_scores(
        score_directory=source_score_directory,
        clients=context.clients,
    )
    grid = fedavg_alignment_grid_for_scores(source_alignment_clients)
    reference_alignment = model_alignment(
        ModelAlignmentCondition(
            client_scores=source_alignment_clients,
            shared_threshold=_shared_type7_threshold(source_alignment_clients),
        ),
        grid=grid,
    )
    alignment = model_alignment(
        fine_alignment_condition,
        grid=grid,
    )
    result = FineTuningStressTestResult(
        personalized_coordinate=personalized_coordinate,
        model_evidence=tuple(
            FineTuningClientModelEvidence(
                client=owned.client,
                serialized_state_evidence=owned.value.serialized_state_evidence,
                wall_time=owned.value.wall_time,
            )
            for owned in models.items
        ),
        alignment=alignment,
        reference_alignment=reference_alignment,
        alignment_reductions=alignment_reductions(reference_alignment, alignment),
        shared_threshold=shared,
        local_threshold=local,
        shared_threshold_metrics=tuple(
            client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.SHARED_THRESHOLD,
                scores.manifests.require(assignment.client),
                assignment,
                evaluation_cohort,
            )
            for assignment in shared.assignments
        ),
        local_threshold_metrics=tuple(
            client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                scores.manifests.require(assignment.client),
                assignment,
                evaluation_cohort,
            )
            for assignment in local.assignments
        ),
        evaluation_cohort=evaluation_cohort,
    )
    _persist_fine_tuning_evidence(
        FineTuningStressTestEvidence(
            personalized_coordinate=result.personalized_coordinate,
            model_evidence=result.model_evidence,
            alignment=result.alignment,
            reference_alignment=result.reference_alignment,
            alignment_reductions=result.alignment_reductions,
            shared_threshold_metrics=result.shared_threshold_metrics,
            local_threshold_metrics=result.local_threshold_metrics,
            evaluation_cohort=result.evaluation_cohort,
        ),
        training_seed=training_seed,
        output_root=output_root,
    )
    return result


def analyze_ditto_absorption(
    results: tuple[DittoStressTestEvidence, ...],
    *,
    reference_evidence: tuple[FedAvgCvFprEffectEvidence, ...],
    output_directory: Path,
) -> AbsorptionCohortResult:
    if len(results) != len(reference_evidence):
        raise ScientificContractError(
            ErrorMessage("absorption analysis requires one FedAvg corner-evidence record per Ditto seed result"),
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
    observations: list[AbsorptionSeedObservation] = []
    alternative_route = 0
    for result, reference in zip(results, reference_evidence, strict=True):
        seed = result.personalized_coordinate.training_seed
        if reference.seed != seed:
            raise ScientificContractError(
                ErrorMessage("Ditto absorption reference evidence must align seed-for-seed with stress results"),
                subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            )
        effect_evidence = _population_cv_fpr_effect(result)
        if abs(effect_evidence.shared_cv.value - reference.local_cv.value) <= DITTO_ALTERNATIVE_ROUTE_DIFFERENCE.value:
            alternative_route += 1
        coefficient = result.personalized_coordinate.model_coefficient
        observations.append(
            AbsorptionSeedObservation(
                seed=seed,
                experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
                reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
                personalized_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
                reference_effect=reference.effect,
                personalized_effect=effect_evidence.effect,
                reference_shared_cv=reference.shared_cv,
                reference_local_cv=reference.local_cv,
                personalized_shared_cv=effect_evidence.shared_cv,
                personalized_local_cv=effect_evidence.local_cv,
                model_coefficient=ModelCoefficientValue(coefficient.value) if coefficient is not None else None,
            )
        )
    cohort = decide_absorption_cohort(
        tuple(observations),
        _MODEL_ABSORPTION_DECISION_PROTOCOL,
        alternative_route_seed_count=SeedObservationCount(alternative_route),
    )
    export_mechanism_publication(
        (cohort,),
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output_directory,
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
    )
    return cohort


def analyze_fine_tuning_absorption(
    results: tuple[FineTuningStressTestEvidence, ...],
    *,
    reference_evidence: tuple[FedAvgCvFprEffectEvidence, ...],
    output_directory: Path,
) -> AbsorptionCohortResult:
    if len(results) != len(reference_evidence):
        raise ScientificContractError(
            ErrorMessage("absorption analysis requires one FedAvg corner-evidence record per fine-tuning seed result"),
            subject=ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
        )
    observations: list[AbsorptionSeedObservation] = []
    for result, reference in zip(results, reference_evidence, strict=True):
        seed = result.personalized_coordinate.training_seed
        if reference.seed != seed:
            raise ScientificContractError(
                ErrorMessage("fine-tuning absorption reference evidence must align seed-for-seed with stress results"),
                subject=ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
            )
        shared_population = calculate_population_metrics(
            result.shared_threshold_metrics,
            cohort=result.evaluation_cohort,
        )
        local_population = calculate_population_metrics(
            result.local_threshold_metrics,
            cohort=result.evaluation_cohort,
        )
        shared_cv = _required_population_cv(shared_population)
        local_cv = _required_population_cv(local_population)
        observations.append(
            AbsorptionSeedObservation(
                seed=seed,
                experiment=ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
                reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
                personalized_model=TrainingModelId.FEDAVG_LOCAL_FINE_TUNING,
                reference_effect=reference.effect,
                personalized_effect=MetricValue(shared_cv.value - local_cv.value),
                reference_shared_cv=reference.shared_cv,
                reference_local_cv=reference.local_cv,
                personalized_shared_cv=shared_cv,
                personalized_local_cv=local_cv,
                model_coefficient=None,
            )
        )
    cohort = decide_absorption_cohort(tuple(observations), _MODEL_ABSORPTION_DECISION_PROTOCOL)
    export_mechanism_publication(
        (cohort,),
        experiment=ExperimentId.FEDAVG_LOCAL_FINE_TUNING,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output_directory,
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
    )
    return cohort


def run_fedprox_stress_test_seed(
    *,
    training_seed: Seed,
    coefficient: ProximalCoefficient,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> FedProxStressTestResult:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(training_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason(
                    "the FedProx stress-test entry point supplies the locked natural-device execution prerequisites"
                ),
            ),
        ),
    )
    tolerance = NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value
    coordinates = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.disposition is PlanDisposition.EXECUTABLE
        and entry.coordinate.model_coefficient is not None
        and abs(entry.coordinate.model_coefficient.value - coefficient.value) <= tolerance
    )
    if not coordinates:
        raise ScientificContractError(
            ErrorMessage(f"FedProx planning produced no executable coordinates for coefficient={coefficient.value}"),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    campaign_entries = tuple(
        CampaignEntry(ordinal=CampaignOrdinal(index), coordinate=coordinate)
        for index, coordinate in enumerate(coordinates)
    )
    campaign = CampaignPlan(entries=campaign_entries)
    result = execute_declared_campaign(
        campaign=campaign,
        declaration=declaration,
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    return FedProxStressTestResult(
        training_seed=training_seed,
        coefficient=coefficient,
        completed_threshold_methods=result.completed_threshold_methods,
    )


def load_fedprox_cv_fpr_corners(
    training_seed: Seed,
    coefficient: ProximalCoefficient,
) -> FedProxCvFprCornerEvidence:
    experiment = ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST
    shared = absorption_corner_from_evaluation_document(
        load_evaluation_document(
            _fedprox_evaluation_path(training_seed, coefficient, FederatedThresholdMethod.SHARED_THRESHOLD)
        ),
        experiment=experiment,
    )
    local = absorption_corner_from_evaluation_document(
        load_evaluation_document(
            _fedprox_evaluation_path(training_seed, coefficient, FederatedThresholdMethod.LOCAL_THRESHOLD)
        ),
        experiment=experiment,
    )
    return FedProxCvFprCornerEvidence(seed=training_seed, coefficient=coefficient, shared=shared, local=local)


def load_fedprox_alignment_evidence(
    training_seed: Seed,
    coefficient: ProximalCoefficient,
) -> FedProxAlignmentEvidence:
    shared_document = load_evaluation_document(
        _fedprox_evaluation_path(training_seed, coefficient, FederatedThresholdMethod.SHARED_THRESHOLD)
    )
    if not shared_document.clients:
        raise ScientificContractError(ErrorMessage("FedProx alignment requires at least one evaluated client"))
    shared_threshold = shared_document.clients[0].threshold
    if any(item.threshold != shared_threshold for item in shared_document.clients[1:]):
        raise ScientificContractError(ErrorMessage("FedProx shared evaluation must use one threshold across clients"))
    clients = tuple(item.client for item in shared_document.clients)
    condition_coordinate = shared_document.score_coordinate
    condition_clients = _alignment_clients_from_scores(
        score_directory=federated_training_directory(condition_coordinate, OUTPUTS_ROOT)
        / ExecutionArtifactDirectory.SCORES,
        clients=clients,
    )
    source_coordinate = FederatedTrainingCoordinate(
        population=condition_coordinate.population,
        training_seed=training_seed,
        split_protocol=condition_coordinate.split_protocol,
        preprocessing_identity=condition_coordinate.preprocessing_identity,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
        controlled_partition_kind=condition_coordinate.controlled_partition_kind,
        dirichlet_concentration=condition_coordinate.dirichlet_concentration,
    )
    source_clients = _alignment_clients_from_scores(
        score_directory=federated_training_directory(source_coordinate, OUTPUTS_ROOT)
        / ExecutionArtifactDirectory.SCORES,
        clients=clients,
    )
    grid = fedavg_alignment_grid_for_scores(source_clients)
    reference_alignment = model_alignment(
        ModelAlignmentCondition(client_scores=source_clients, shared_threshold=_shared_type7_threshold(source_clients)),
        grid=grid,
    )
    alignment = model_alignment(
        ModelAlignmentCondition(client_scores=condition_clients, shared_threshold=shared_threshold),
        grid=grid,
    )
    native_alignment = model_alignment(
        ModelAlignmentCondition(client_scores=condition_clients, shared_threshold=shared_threshold),
        grid=fedavg_alignment_grid_for_scores(condition_clients),
    )
    return FedProxAlignmentEvidence(
        training_seed=training_seed,
        coefficient=coefficient,
        reference_alignment=reference_alignment,
        alignment=alignment,
        native_alignment=native_alignment,
        alignment_reductions=alignment_reductions(reference_alignment, alignment),
    )


def fedprox_terminal50_rms_drift(
    training_seed: Seed,
    coefficient: ProximalCoefficient | None,
) -> MetricValue:
    """Return the prospectively fixed median RMS drift over rounds 151..200."""

    return terminal50_drift_summary(training_seed, coefficient).federation_rms_drift


def terminal50_drift_summary(
    training_seed: Seed,
    coefficient: ProximalCoefficient | None,
) -> Terminal50DriftSummary:
    """Load the fixed final-50-round client and federation RMS drift diagnostics."""

    coordinate = _fedprox_training_coordinate(training_seed, coefficient)
    frame = history_frames(federated_training_directory(coordinate, OUTPUTS_ROOT)).client_rounds
    columns = FederatedHistoryColumn
    terminal_rounds = tuple(
        sorted(
            int(value)
            for value in frame.get_column(columns.ROUND_NUMBER.value).unique().to_list()
            if int(value) >= 151
        )
    )
    if terminal_rounds != tuple(range(151, 201)):
        raise ScientificContractError(
            ErrorMessage("FedProx activation evidence requires the locked complete rounds 151 through 200"),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    terminal = frame.filter(pl.col(columns.ROUND_NUMBER.value) >= 151)
    values = tuple(
        float(value)
        for value in terminal.get_column(columns.RMS_DRIFT.value).to_list()
        if value is not None
    )
    if len(values) != terminal.height:
        raise ScientificContractError(
            ErrorMessage("FedProx activation evidence requires persisted terminal-50 RMS drift values"),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    clients = tuple(
        Terminal50ClientDrift(
            client_id=ClientIdentityToken(str(client_id)),
            rms_drift=MetricValue(float(np.median(np.asarray(client_values, dtype=np.float64)))),
        )
        for client_id, client_values in sorted(
            (
                (str(client_id), tuple(float(value) for value in values if value is not None))
                for client_id, values in terminal.group_by(columns.CLIENT_ID.value, maintain_order=True).agg(
                    pl.col(columns.RMS_DRIFT.value)
                ).iter_rows()
            ),
            key=lambda item: item[0],
        )
    )
    return Terminal50DriftSummary(
        seed=training_seed,
        coefficient=coefficient,
        federation_rms_drift=MetricValue(float(np.median(np.asarray(values, dtype=np.float64)))),
        client_rms_drifts=clients,
    )


def _fedprox_training_coordinate(
    training_seed: Seed,
    coefficient: ProximalCoefficient | None,
) -> FederatedTrainingCoordinate:
    requested_coefficient = FEDPROX_COEFFICIENTS[0] if coefficient is None else coefficient
    shared_document = load_evaluation_document(
        _fedprox_evaluation_path(training_seed, requested_coefficient, FederatedThresholdMethod.SHARED_THRESHOLD)
    )
    if coefficient is not None:
        return shared_document.score_coordinate
    return replace(
        shared_document.score_coordinate,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )


def build_fedprox_absorption_observation(
    *,
    training_seed: Seed,
    coefficient: ProximalCoefficient,
    reference: FedAvgCvFprEffectEvidence,
) -> AbsorptionSeedObservation:
    experiment = ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST
    if reference.seed != training_seed:
        raise ScientificContractError(
            ErrorMessage("FedProx absorption reference evidence must match the observation seed"),
            subject=experiment,
        )
    personalized = load_fedprox_cv_fpr_corners(training_seed, coefficient)
    return AbsorptionSeedObservation.from_corners(
        AbsorptionFourCornerEvidence(
            seed=training_seed,
            experiment=experiment,
            reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
            personalized_model=TrainingModelId.FEDPROX_AUTOENCODER,
            reference_shared=reference.shared,
            reference_local=reference.local,
            personalized_shared=personalized.shared,
            personalized_local=personalized.local,
        )
    )


def analyze_fedprox_absorption(
    observations: tuple[AbsorptionSeedObservation, ...],
    *,
    output_directory: Path,
) -> AbsorptionCohortResult:
    if observations and any(
        item.experiment is not ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST for item in observations
    ):
        raise ScientificContractError(
            ErrorMessage("FedProx absorption requires FEDPROX_ABSORPTION_STRESS_TEST observations")
        )
    if observations and any(
        item.personalized_model is not TrainingModelId.FEDPROX_AUTOENCODER for item in observations
    ):
        raise ScientificContractError(ErrorMessage("FedProx absorption requires FEDPROX personalized model identity"))
    if observations and any(item.corners is None for item in observations):
        raise ScientificContractError(
            ErrorMessage("FedProx absorption requires four-corner provenance on every seed observation"),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    cohort = decide_absorption_cohort(observations, _MODEL_ABSORPTION_DECISION_PROTOCOL)
    export_mechanism_publication(
        (cohort,),
        experiment=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output_directory,
        evidence_role=EvidenceRole.TRAINING_STRESS_TEST,
    )
    return cohort


def fedprox_activation_report(
    evidence_by_coefficient: tuple[
        tuple[ProximalCoefficient, tuple[FedProxAlignmentEvidence, ...], tuple[AbsorptionSeedObservation, ...]], ...
    ],
) -> str:
    """Render the mandatory FedAvg/FedProx activation view from seed-level evidence."""

    lines = [
        "# FedProx mechanism-activation view",
        "",
        "Terminal-50 RMS drift is the median over all client-round cells in rounds 151–200. "
        "All quantities are descriptive training-stress diagnostics; threshold outcomes alone are not evidence "
        "that the proximal mechanism was active.",
        "",
        "| condition | seed | D_terminal50 | DriftSuppression | DeltaH | H | ModelAlignmentH | "
        "LocalThresholdDispersion | NormalizedSharedLocalThresholdDistance | DeltaScope | ScopeAbsorption |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    client_drift_lines = [
        "",
        "## Per-client terminal-50 RMS drift",
        "",
        "| condition | seed | client | terminal-50 RMS drift |",
        "| --- | ---: | --- | ---: |",
    ]
    fedavg_written: set[Seed] = set()
    for coefficient, alignments, observations in evidence_by_coefficient:
        alignment_by_seed = {item.training_seed: item for item in alignments}
        observation_by_seed = {item.seed: item for item in observations}
        if set(alignment_by_seed) != set(observation_by_seed):
            raise ScientificContractError(ErrorMessage("FedProx activation rows require aligned seed evidence"))
        for seed in sorted(alignment_by_seed):
            alignment_evidence = alignment_by_seed[seed]
            observation = observation_by_seed[seed]
            fedavg_summary = terminal50_drift_summary(seed, None)
            condition_summary = terminal50_drift_summary(seed, coefficient)
            fedavg_drift = fedavg_summary.federation_rms_drift
            condition_drift = condition_summary.federation_rms_drift
            reference_h = _alignment_metric_value(
                alignment_evidence.reference_alignment, ModelAlignmentMetric.MODEL_ALIGNMENT_HETEROGENEITY
            )
            condition_h = _alignment_metric_value(
                alignment_evidence.native_alignment, ModelAlignmentMetric.MODEL_ALIGNMENT_HETEROGENEITY
            )
            model_alignment_h = _alignment_metric_value(
                alignment_evidence.alignment, ModelAlignmentMetric.MODEL_ALIGNMENT_HETEROGENEITY
            )
            local_dispersion = _alignment_metric_value(
                alignment_evidence.alignment, ModelAlignmentMetric.LOCAL_THRESHOLD_DISPERSION
            )
            normalized_distance = _alignment_metric_value(
                alignment_evidence.alignment,
                ModelAlignmentMetric.NORMALIZED_SHARED_LOCAL_THRESHOLD_DISTANCE,
            )
            if seed not in fedavg_written:
                lines.append(
                    _activation_row(
                        "FedAvg", seed, fedavg_drift, None, None, reference_h, reference_h,
                        _alignment_metric_value(
                            alignment_evidence.reference_alignment, ModelAlignmentMetric.LOCAL_THRESHOLD_DISPERSION
                        ),
                        _alignment_metric_value(
                            alignment_evidence.reference_alignment,
                            ModelAlignmentMetric.NORMALIZED_SHARED_LOCAL_THRESHOLD_DISTANCE,
                        ),
                        observation.reference_effect, None,
                    )
                )
                fedavg_written.add(seed)
                client_drift_lines.extend(
                    f"| FedAvg | {seed.value} | `{item.client_id.value}` | {item.rms_drift.value:.12g} |"
                    for item in fedavg_summary.client_rms_drifts
                )
            suppression = (
                MetricValue(1.0 - condition_drift.value / fedavg_drift.value)
                if fedavg_drift.value > 1e-12
                else None
            )
            delta_h = (
                MetricValue(condition_h.value - reference_h.value)
                if condition_h is not None and reference_h is not None
                else None
            )
            scope_absorption = (
                MetricValue(1.0 - observation.personalized_effect.value / observation.reference_effect.value)
                if observation.reference_effect.value > 1e-12
                else None
            )
            lines.append(
                _activation_row(
                    f"FedProx(mu={coefficient.value:.12g})", seed, condition_drift, suppression, delta_h,
                    condition_h, model_alignment_h, local_dispersion, normalized_distance,
                    observation.personalized_effect, scope_absorption,
                )
            )
            client_drift_lines.extend(
                f"| FedProx(mu={coefficient.value:.12g}) | {seed.value} | `{item.client_id.value}` | "
                f"{item.rms_drift.value:.12g} |"
                for item in condition_summary.client_rms_drifts
            )
    return "\n".join([*lines, *client_drift_lines]) + "\n"


def _alignment_metric_value(result: ModelAlignmentResult, metric: ModelAlignmentMetric) -> MetricValue | None:
    return next(item.value for item in result.metrics if item.metric is metric)


def _activation_row(
    condition: str,
    seed: Seed,
    drift: MetricValue,
    suppression: MetricValue | None,
    delta_h: MetricValue | None,
    heterogeneity: MetricValue | None,
    model_alignment_h: MetricValue | None,
    local_dispersion: MetricValue | None,
    normalized_distance: MetricValue | None,
    delta_scope: MetricValue,
    scope_absorption: MetricValue | None,
) -> str:
    values = (
        drift,
        suppression,
        delta_h,
        heterogeneity,
        model_alignment_h,
        local_dispersion,
        normalized_distance,
        delta_scope,
        scope_absorption,
    )
    rendered = (f"{item.value:.12g}" if item is not None else "UNAVAILABLE" for item in values)
    return f"| {condition} | {seed.value} | " + " | ".join(rendered) + " |"


def _fedprox_evaluation_path(
    training_seed: Seed,
    coefficient: ProximalCoefficient,
    method: FederatedThresholdMethod,
) -> Path:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST)
    plan = expand_experiment_plan(declarations=(declaration,), seed_cohort=SeedCohort(values=(training_seed,)))
    tolerance = NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value
    matches = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.coordinate.threshold_method is method
        and entry.coordinate.metric is MetricId.FPR_COEFFICIENT_OF_VARIATION
        and entry.coordinate.model_coefficient is not None
        and abs(entry.coordinate.model_coefficient.value - coefficient.value) <= tolerance
    )
    if len(matches) != 1:
        raise ScientificContractError(
            ErrorMessage(
                "FedProx evaluation coordinate unresolved for "
                f"seed={training_seed.value} coefficient={coefficient.value} method={method.value}"
            ),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    path = (
        evaluation_run_directory(OUTPUTS_ROOT, matches[0])
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(ErrorMessage(f"missing FedProx evaluation document: {path}"))
    return path


def _population_cv_fpr_effect(result: DittoStressTestEvidence) -> DittoCvFprEffectEvidence:
    shared_population = calculate_population_metrics(result.shared_threshold_metrics, cohort=result.evaluation_cohort)
    local_population = calculate_population_metrics(result.local_threshold_metrics, cohort=result.evaluation_cohort)
    shared_cv = _required_population_cv(shared_population)
    local_cv = _required_population_cv(local_population)
    return DittoCvFprEffectEvidence(
        shared_cv=shared_cv,
        local_cv=local_cv,
        effect=MetricValue(shared_cv.value - local_cv.value),
    )


def _required_population_cv(population: PopulationMetricResult) -> MetricValue:
    outcome = metric_by_id(population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)
    if outcome.status is not MetricStatus.AVAILABLE or outcome.value is None:
        raise ScientificContractError(
            ErrorMessage("absorption requires available population CV(FPR) under both threshold methods")
        )
    return outcome.value


def _population_context(
    *,
    training_seed: Seed,
    population: PopulationId,
    split_protocol: SplitProtocolId,
    preprocessing_identity: PreprocessingProtocolId,
) -> DittoPopulationContext:
    population_result = construct_declared_population(
        ConstructDeclaredPopulationRequest(
            population=population,
            dataset=DatasetId.NBAIOT,
            canonical_root=DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / DatasetId.NBAIOT.value,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            controlled_condition=None,
        )
    )
    preprocessing = preprocess_federated(
        FederatedPreprocessingRequest(
            population=population,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            preprocessing_identity=preprocessing_identity,
            data_root=DATA_ROOT,
            dirichlet_condition=None,
            capture_timestamp_column=None,
        )
    )
    clients = population_result.construction.manifest.clients
    return DittoPopulationContext(
        clients=clients,
        family_by_client=population_result.construction.manifest.family_by_client,
        preprocessing=preprocessing,
    )


def _personalized_scores(
    *,
    training: TrainDittoDetectorResult,
    personalized_coordinate: FederatedTrainingCoordinate,
    context: DittoPopulationContext,
    feature_names: FeatureNameSequence,
    training_seed: Seed,
    regularization: DittoRegularization,
    output_root: Path,
    overwrite: bool,
) -> PersonalizedScoreCollection:
    eligible: list[ClientBenignCalibrationScores] = []
    manifests: list[ClientOwned[ClientIdentity, FederatedScoreArtifactManifest]] = []
    personalized_directory = ditto_directory(
        training_seed,
        regularization,
        DittoArtifactBranch.PERSONALIZED_MODELS,
        output_root,
    )
    for owned in sorted(training.personalized_terminal_models.items, key=lambda item: item.client):
        client = owned.client
        terminal_training = replace(
            training.global_training,
            coordinate=owned.value.coordinate,
            terminal_model_state=owned.value.model_state,
        )
        manifest = publish_federated_scores(
            GenerateFederatedScoresRequest(
                training=terminal_training,
                scored_split_protocol=terminal_training.coordinate.split_protocol,
                autoencoder=NBAIOT_AUTOENCODER,
                feature_names=feature_names,
                clients=(client_scoring_input(context.preprocessing.client_publications, client),),
                batch_size=BATCH_SIZE,
                output_directory=personalized_directory / client.client_id.value / ExecutionArtifactDirectory.SCORES,
                overwrite=overwrite,
            )
        ).manifest
        manifests.append(ClientOwned(client=client, value=manifest))
        record = score_record_for_client(manifest.calibration_records, client, PartitionRole.CALIBRATION)
        scores = tuple(
            ScoreValue(float(value))
            for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
        )
        if not MINIMUM_BENIGN_SUPPORT.fits_within(RowCount(len(scores))):
            continue
        eligible.append(
            ClientBenignCalibrationScores(
                client,
                personalized_coordinate,
                scores,
            )
        )
    if not eligible:
        raise ScientificContractError(
            ErrorMessage("no client meets the minimum benign calibration support for threshold construction"),
            subject=ContractSubject.CALIBRATION,
        )
    return PersonalizedScoreCollection(
        eligible_calibration=tuple(eligible),
        manifests=ClientCollection(items=tuple(manifests)),
    )


def _fine_tuned_scores(
    *,
    models: ClientCollection[ClientIdentity, FineTunedTerminalModel],
    personalized_coordinate: FederatedTrainingCoordinate,
    context: DittoPopulationContext,
    feature_names: FeatureNameSequence,
    output_directory: Path,
    overwrite: bool,
) -> PersonalizedScoreCollection:
    eligible: list[ClientBenignCalibrationScores] = []
    manifests: list[ClientOwned[ClientIdentity, FederatedScoreArtifactManifest]] = []
    for owned in models.items:
        manifest = publish_federated_scores(
            GenerateFederatedScoresRequest(
                training=TerminalFederatedScoringModel(
                    coordinate=personalized_coordinate,
                    terminal_model_state=owned.value.terminal_model_state,
                    batch_size_used=BATCH_SIZE,
                ),
                scored_split_protocol=personalized_coordinate.split_protocol,
                autoencoder=NBAIOT_AUTOENCODER,
                feature_names=feature_names,
                clients=(client_scoring_input(context.preprocessing.client_publications, owned.client),),
                batch_size=BATCH_SIZE,
                output_directory=output_directory / owned.client.client_id.value,
                overwrite=overwrite,
            )
        ).manifest
        manifests.append(ClientOwned(client=owned.client, value=manifest))
        record = score_record_for_client(manifest.calibration_records, owned.client, PartitionRole.CALIBRATION)
        scores = tuple(
            ScoreValue(float(value))
            for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
        )
        if MINIMUM_BENIGN_SUPPORT.fits_within(RowCount(len(scores))):
            eligible.append(ClientBenignCalibrationScores(owned.client, personalized_coordinate, scores))
    if not eligible:
        raise ScientificContractError(
            ErrorMessage("no client meets the minimum benign calibration support for threshold construction"),
            subject=ContractSubject.CALIBRATION,
        )
    return PersonalizedScoreCollection(
        eligible_calibration=tuple(eligible),
        manifests=ClientCollection(items=tuple(manifests)),
    )


def _alignment_condition_from_scores(
    *,
    score_directory: Path,
    clients: tuple[ClientIdentity, ...],
    shared_threshold: ThresholdValue,
) -> ModelAlignmentCondition:
    return ModelAlignmentCondition(
        client_scores=_alignment_clients_from_scores(score_directory=score_directory, clients=clients),
        shared_threshold=shared_threshold,
    )


def _alignment_condition_from_eligible(
    eligible: tuple[ClientBenignCalibrationScores, ...],
    shared_threshold: ThresholdValue,
) -> ModelAlignmentCondition:
    return ModelAlignmentCondition(
        client_scores=tuple(
            ModelAlignmentClientScores(client=item.client, calibration_scores=item.scores)
            for item in sorted(eligible, key=lambda item: item.client)
        ),
        shared_threshold=shared_threshold,
    )


def _alignment_clients_from_scores(
    *,
    score_directory: Path,
    clients: tuple[ClientIdentity, ...],
) -> tuple[ModelAlignmentClientScores, ...]:
    observations: list[ModelAlignmentClientScores] = []
    for client in sorted(clients):
        path = score_directory / client.client_id.value / "calibration.parquet"
        if not path.is_file():
            raise ScientificContractError(
                ErrorMessage(f"missing immutable calibration score artifact for alignment: {path}"),
                subject=ContractSubject.ARTIFACT_PATH,
            )
        frame = pl.read_parquet(path)
        observations.append(
            ModelAlignmentClientScores(
                client=client,
                calibration_scores=tuple(
                    ScoreValue(float(value))
                    for value in frame[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
                ),
            )
        )
    return tuple(observations)


def _shared_type7_threshold(client_scores: tuple[ModelAlignmentClientScores, ...]) -> ThresholdValue:
    pooled = np.concatenate(
        tuple(
            np.asarray([value.value for value in client.calibration_scores], dtype=np.float64)
            for client in client_scores
        )
    )
    return ThresholdValue(float(np.quantile(pooled, CANONICAL_QUANTILE.value, method="linear")))


def ditto_directory(
    training_seed: Seed,
    regularization: DittoRegularization,
    branch: DittoArtifactBranch,
    output_root: Path,
) -> Path:
    return (
        output_root
        / ExecutionRootDirectory.DITTO_STRESS_TEST
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / str(training_seed.value)
        / str(regularization.value)
        / branch.value
    )


def fine_tuning_root(training_seed: Seed, *, output_root: Path) -> Path:
    return (
        output_root
        / ExecutionRootDirectory.FEDAVG_LOCAL_FINE_TUNING
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / str(training_seed.value)
    )


def ditto_analysis_directory(regularization: DittoRegularization, *, output_root: Path) -> Path:
    return (
        output_root
        / ExecutionRootDirectory.DITTO_STRESS_TEST
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / DittoArtifactBranch.ANALYSIS
        / str(regularization.value)
    )


def fedprox_stress_test_root(*, output_root: Path) -> Path:
    return output_root / ExecutionRootDirectory.FEDPROX_STRESS_TEST / PopulationId.NBAIOT_NATURAL_DEVICES.value


def fedprox_analysis_directory(
    coefficient: ProximalCoefficient,
    *,
    output_root: Path,
) -> Path:
    return (
        fedprox_stress_test_root(output_root=output_root) / FedProxArtifactDirectory.ANALYSIS / str(coefficient.value)
    )
