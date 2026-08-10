"""Ditto and FedProx training-side threshold-scope stress experiments."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

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
from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    ContractSubject,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FeatureNameSequence,
    FederatedThresholdMethod,
    FedProxCoefficientSelectionRule,
    FedProxRoleDirectory,
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
    MetricValue,
    ModelCoefficientValue,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    ScoreValue,
    Seed,
    SeedObservationCount,
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
from datp_core.detector.scoring.models import FederatedScoreArtifactManifest, GenerateFederatedScoresRequest
from datp_core.detector.training.contracts import (
    ModelAbsorptionDecisionProtocol as DetectorModelAbsorptionDecisionProtocol,
)
from datp_core.detector.training.ditto import DittoTrainingRequest
from datp_core.detector.training.ditto_publication import (
    TrainDittoDetectorRequest,
    TrainDittoDetectorResult,
    train_ditto_detector,
)
from datp_core.detector.training.models import (
    DittoTrainingCoordinates,
    FederatedTrainingCoordinate,
)
from datp_core.detector.training.protocols import (
    BATCH_SIZE,
    DITTO_ALTERNATIVE_ROUTE_DIFFERENCE,
    FEDPROX_COEFFICIENT_SELECTION_RULE,
    FEDPROX_COEFFICIENTS,
    LEARNING_RATE,
    MODEL_ABSORPTION_DECISION_PROTOCOL,
    NBAIOT_AUTOENCODER,
    require_non_test_fedprox_coefficient_selection_inputs,
    resolve_ditto_protocol,
    select_primary_fedprox_coefficient,
)
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
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


class TrainingStressArtifactName(StrEnum):
    PRIMARY_COEFFICIENT_DECISION = "primary_coefficient_decision.json"


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoStressTestResult:
    personalized_coordinate: FederatedTrainingCoordinate
    shared_threshold: SharedThresholdResult
    local_threshold: LocalThresholdResult
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]
    evaluation_cohort: EvaluationCohortManifest


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoStressTestEvidence:
    personalized_coordinate: FederatedTrainingCoordinate
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]
    evaluation_cohort: EvaluationCohortManifest


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
    """Population CV(FPR) evidence for the paired Ditto threshold-scope comparison."""

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
    result = DittoStressTestResult(
        personalized_coordinate=personalized_coordinate,
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
            shared_threshold_metrics=result.shared_threshold_metrics,
            local_threshold_metrics=result.local_threshold_metrics,
            evaluation_cohort=result.evaluation_cohort,
        ),
        training_seed=training_seed,
        regularization=regularization,
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


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxTerminalLossObservation:
    """Terminal aggregate training loss observed for one FedProx training seed."""

    seed: Seed
    terminal_training_loss: MetricValue


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxCoefficientTerminalLoss:
    coefficient: ProximalCoefficient
    mean_terminal_training_loss: MetricValue
    per_seed_terminal_losses: tuple[FedProxTerminalLossObservation, ...]

    def __post_init__(self) -> None:
        if len(self.per_seed_terminal_losses) != CONFIRMATORY_SEED_COHORT.member_count.value:
            raise ScientificContractError(
                ErrorMessage("FedProx terminal-loss candidates require the full confirmatory seed cohort"),
                subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            )
        seeds = tuple(observation.seed for observation in self.per_seed_terminal_losses)
        if seeds != CONFIRMATORY_SEED_COHORT.values:
            raise ScientificContractError(
                ErrorMessage("FedProx terminal-loss candidates must use the locked confirmatory seed order"),
                subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            )
        observed_mean = sum(
            observation.terminal_training_loss.value for observation in self.per_seed_terminal_losses
        ) / len(self.per_seed_terminal_losses)
        if abs(self.mean_terminal_training_loss.value - observed_mean) > NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE.value:
            raise ScientificContractError(
                ErrorMessage("FedProx candidate mean terminal loss must equal its seed observations"),
                subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxPrimaryCoefficientDecision:
    selection_rule: FedProxCoefficientSelectionRule
    primary_coefficient: ProximalCoefficient
    candidates: tuple[FedProxCoefficientTerminalLoss, ...]


def fedprox_training_coordinate(training_seed: Seed, coefficient: ProximalCoefficient) -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=training_seed,
        split_protocol=split_protocol_for_population(PopulationId.NBAIOT_NATURAL_DEVICES),
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.FEDPROX_AUTOENCODER,
        model_coefficient=coefficient,
    )


def read_terminal_aggregate_training_loss(
    training_directory: Path,
    *,
    maximum_round: RoundNumber,
) -> MetricValue:
    try:
        round_frame = history_frames(training_directory).round_summary
    except ArtifactIntegrityError as error:
        raise ScientificContractError(
            ErrorMessage(f"FedProx terminal training loss unavailable under {training_directory}: {error}"),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        ) from error
    matching = round_frame.filter(pl.col(FederatedHistoryColumn.ROUND_NUMBER.value) == maximum_round.value)
    if matching.height != 1:
        raise ScientificContractError(
            ErrorMessage(
                f"FedProx training history must contain exactly one row for terminal round {maximum_round.value}"
            ),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    return MetricValue(float(matching.get_column(FederatedHistoryColumn.AGGREGATE_LOSS.value).item()))


def collect_fedprox_coefficient_terminal_losses(
    *,
    output_root: Path,
    seed_cohort: SeedCohort,
) -> tuple[FedProxCoefficientTerminalLoss, ...]:
    candidates: list[FedProxCoefficientTerminalLoss] = []
    for coefficient in FEDPROX_COEFFICIENTS:
        seed_losses: list[FedProxTerminalLossObservation] = []
        for seed in seed_cohort.values:
            directory = federated_training_directory(fedprox_training_coordinate(seed, coefficient), output_root)
            seed_losses.append(
                FedProxTerminalLossObservation(
                    seed=seed,
                    terminal_training_loss=read_terminal_aggregate_training_loss(
                        directory,
                        maximum_round=DIAGNOSTIC_SNAPSHOT_PROTOCOL.maximum_round,
                    ),
                )
            )
        candidates.append(
            FedProxCoefficientTerminalLoss(
                coefficient=coefficient,
                mean_terminal_training_loss=MetricValue(
                    sum(observation.terminal_training_loss.value for observation in seed_losses) / len(seed_losses)
                ),
                per_seed_terminal_losses=tuple(seed_losses),
            )
        )
    return tuple(candidates)


def select_primary_fedprox_coefficient_from_artifacts(
    *,
    output_root: Path,
    seed_cohort: SeedCohort,
) -> FedProxPrimaryCoefficientDecision:
    require_non_test_fedprox_coefficient_selection_inputs(
        selection_rule=FEDPROX_COEFFICIENT_SELECTION_RULE,
        held_out_metrics=None,
        attack_labels_present=False,
    )
    candidates = collect_fedprox_coefficient_terminal_losses(output_root=output_root, seed_cohort=seed_cohort)
    selected = select_primary_fedprox_coefficient(candidates)
    return FedProxPrimaryCoefficientDecision(
        selection_rule=FEDPROX_COEFFICIENT_SELECTION_RULE,
        primary_coefficient=selected.coefficient,
        candidates=candidates,
    )


def write_fedprox_primary_coefficient_decision(decision: FedProxPrimaryCoefficientDecision, destination: Path) -> Path:
    write_text_atomically(destination, FileContentText(canonical_json_text(decision)))
    return destination


def load_fedprox_primary_coefficient_decision(destination: Path) -> FedProxPrimaryCoefficientDecision:
    try:
        adapter: TypeAdapter[FedProxPrimaryCoefficientDecision] = TypeAdapter(FedProxPrimaryCoefficientDecision)
        return adapter.validate_json(destination.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as error:
        raise ScientificContractError(
            ErrorMessage(f"FedProx primary-coefficient decision is unreadable or invalid: {destination}"),
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        ) from error


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
    role: FedProxRoleDirectory,
    *,
    output_root: Path,
) -> Path:
    return (
        fedprox_stress_test_root(output_root=output_root)
        / FedProxArtifactDirectory.ANALYSIS
        / role.value
        / str(coefficient.value)
    )
