"""Ditto and FedProx training-side threshold-scope stress experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl
from pydantic import TypeAdapter, ValidationError

from datp_core.analysis.mechanisms import (
    AbsorptionCohortResult,
    AbsorptionCornerEvidence,
    AbsorptionFourCornerEvidence,
    AbsorptionSeedObservation,
    decide_absorption_cohort,
)
from datp_core.artifacts.layout import evaluation_run_directory
from datp_core.artifacts.provenance import Checksum, checksum_file
from datp_core.artifacts.repositories.thresholds import (
    FederatedThresholdConstructionRequest,
    construct_and_publish_federated_thresholds,
)
from datp_core.artifacts.serializers.json import canonical_checksum, canonical_json_text
from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.core.identifiers import (
    ClientIdentityToken,
    ContractSubject,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FamilyIdentity,
    FeatureNameSequence,
    FederatedThresholdMethod,
    FedProxCoefficientSelectionRule,
    FedProxRoleDirectory,
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
    ClientCount,
    DittoRegularization,
    MetricValue,
    ModelCoefficientValue,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    ScoreValue,
    Seed,
)
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.data.registry import population_capabilities
from datp_core.detector.scoring.contracts import FixedScoreInvariant
from datp_core.evaluation.cohort.construction import assert_cohort_invariant_to_threshold_methods
from datp_core.evaluation.cohort.contracts import EvaluationCohortManifest
from datp_core.evaluation.cohort.evidence import client_partition_counts_from_scores
from datp_core.evaluation.federated.publication import FederatedEvaluationAssetName
from datp_core.evaluation.models import ClientMetricResult, MetricStatus, PopulationMetricResult, metric_by_id
from datp_core.evaluation.population_metrics import calculate_population_metrics
from datp_core.experiments.common.seeds import CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.experiments.confirmatory import FedAvgCvFprEffectEvidence, absorption_corner_from_evaluation_document
from datp_core.experiments.execution import execute_declared_campaign
from datp_core.experiments.personalized_scoring import client_metric, client_scoring_input, score_record_for_client
from datp_core.experiments.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.learning.federated.checkpoints.history import history_frames
from datp_core.learning.federated.checkpoints.identities import FederatedHistoryColumn
from datp_core.learning.federated.ditto import DittoTrainingRequest
from datp_core.learning.federated.models import (
    DittoTrainingCoordinates,
    FederatedTrainingCoordinate,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import preprocessing_state_set_checksum
from datp_core.pipeline.checkpoints.service import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
from datp_core.pipeline.decision.evidence import AnalysisAssetName, SeedEvidenceAssetName
from datp_core.pipeline.execution.context import (
    client_training_inputs,
    client_with_id,
    family_identities,
    training_feature_names,
)
from datp_core.pipeline.execution.evidence import load_evaluation_document
from datp_core.pipeline.execution.layout import (
    EvaluationRunAssetDirectory,
    ExecutionArtifactDirectory,
    ExecutionRootDirectory,
    federated_training_directory,
)
from datp_core.pipeline.execution.models import CampaignEntry, CampaignPlan, campaign_digest
from datp_core.pipeline.preparation.populations import ConstructDeclaredPopulationRequest, construct_declared_population
from datp_core.pipeline.scoring.federated import publish_federated_scores
from datp_core.pipeline.scoring.models import FederatedScoreArtifactManifest, GenerateFederatedScoresRequest
from datp_core.pipeline.training.personalized import (
    TrainDittoDetectorRequest,
    TrainDittoDetectorResult,
    train_ditto_detector,
)
from datp_core.preprocessing.models import FederatedPreprocessingOutcome, FederatedPreprocessingRequest
from datp_core.preprocessing.service import preprocess_federated
from datp_core.presentation.export import export_mechanism_publication
from datp_core.protocols.calibration import CANONICAL_QUANTILE, MINIMUM_BENIGN_SUPPORT, CalibrationSupportRule
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
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
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically
from datp_core.thresholds.contracts import FamilyAssignment
from datp_core.thresholds.dispatch import ThresholdConstructionRequest
from datp_core.thresholds.policies.local import LocalThresholdResult
from datp_core.thresholds.policies.shared import SharedThresholdResult
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores


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
    (directory / SeedEvidenceAssetName.DOCUMENT).write_text(canonical_json_text(evidence), encoding="utf-8")
    (directory / AnalysisAssetName.COMPLETE).write_text(canonical_checksum(evidence).value, encoding="utf-8")


def load_ditto_stress_test_evidence(
    *,
    training_seed: Seed,
    regularization: DittoRegularization,
    output_root: Path,
) -> DittoStressTestEvidence:
    directory = ditto_directory(training_seed, regularization, DittoArtifactBranch.EVIDENCE, output_root)
    document = directory / SeedEvidenceAssetName.DOCUMENT
    complete = directory / AnalysisAssetName.COMPLETE
    if not document.is_file() or not complete.is_file():
        raise ScientificContractError(
            f"missing completed Ditto stress-test evidence: {directory}",
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            reason=f"seed={training_seed.value} regularization={regularization.value}",
        )
    adapter: TypeAdapter[DittoStressTestEvidence] = TypeAdapter(DittoStressTestEvidence)
    try:
        evidence = adapter.validate_json(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as error:
        raise ScientificContractError(
            f"Ditto stress-test evidence is unreadable or invalid: {document}",
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        ) from error
    if complete.read_text(encoding="utf-8").strip() != canonical_checksum(evidence).value:
        raise ScientificContractError(
            f"Ditto stress-test evidence checksum does not match its completion marker: {document}",
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
    return evidence


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoPopulationContext:
    clients: tuple[ClientIdentity, ...]
    family_by_client: tuple[FamilyAssignment, ...]
    preprocessing: FederatedPreprocessingOutcome
    split_manifest_checksum: Checksum
    preprocessing_state_set_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonalizedScoreCollection:
    eligible_calibration: tuple[ClientBenignCalibrationScores, ...]
    manifests: ClientCollection[ClientIdentity, FederatedScoreArtifactManifest]


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxStressTestResult:
    training_seed: Seed
    coefficient: ProximalCoefficient
    campaign_digest: Checksum
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


def run_ditto_stress_test_seed(
    *,
    training_seed: Seed,
    regularization: DittoRegularization,
    output_root: Path,
    overwrite: bool,
) -> DittoStressTestResult:
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
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
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                training_seed=training_seed,
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                split_manifest_checksum=context.split_manifest_checksum,
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
            ),
            overwrite=overwrite,
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
            "Ditto shared-threshold construction must produce a shared result",
            subject=personalized_coordinate.model,
        )
    if not isinstance(local, LocalThresholdResult):
        raise ScientificContractError(
            "Ditto local-threshold construction must produce a local result",
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
            "absorption analysis requires one FedAvg corner-evidence record per Ditto seed result",
            subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        )
    observations: list[AbsorptionSeedObservation] = []
    alternative_route = 0
    for result, reference in zip(results, reference_evidence, strict=True):
        seed = result.personalized_coordinate.training_seed
        if reference.seed != seed:
            raise ScientificContractError(
                "Ditto absorption reference evidence must align seed-for-seed with stress results",
                subject=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            )
        shared_cv, local_cv, effect = _population_cv_fpr_effect(result)
        if abs(shared_cv.value - reference.local_cv.value) <= DITTO_ALTERNATIVE_ROUTE_DIFFERENCE.value:
            alternative_route += 1
        coefficient = result.personalized_coordinate.model_coefficient
        observations.append(
            AbsorptionSeedObservation(
                seed=seed,
                experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
                reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
                personalized_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
                reference_effect=reference.effect,
                personalized_effect=effect,
                reference_shared_cv=reference.shared_cv,
                reference_local_cv=reference.local_cv,
                personalized_shared_cv=shared_cv,
                personalized_local_cv=local_cv,
                model_coefficient=ModelCoefficientValue(coefficient.value) if coefficient is not None else None,
            )
        )
    cohort = decide_absorption_cohort(
        tuple(observations),
        MODEL_ABSORPTION_DECISION_PROTOCOL,
        alternative_route_seed_count=alternative_route,
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
) -> FedProxStressTestResult:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(training_seed,)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="the FedProx stress-test entry point supplies the locked natural-device execution prerequisites",
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
            f"FedProx planning produced no executable coordinates for coefficient={coefficient.value}",
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    campaign_entries = tuple(
        CampaignEntry(ordinal=index, coordinate=coordinate) for index, coordinate in enumerate(coordinates)
    )
    campaign = CampaignPlan(
        entries=campaign_entries,
        digest=campaign_digest(campaign_entries),
        plan_digest=plan.digest,
    )
    result = execute_declared_campaign(
        campaign=campaign,
        declaration=declaration,
        output_root=output_root,
        overwrite=overwrite,
    )
    return FedProxStressTestResult(
        training_seed=training_seed,
        coefficient=coefficient,
        campaign_digest=result.campaign_digest,
        completed_threshold_methods=result.completed_threshold_methods,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxCoefficientTerminalLoss:
    coefficient: ProximalCoefficient
    mean_terminal_training_loss: MetricValue
    per_seed_terminal_losses: tuple[tuple[Seed, MetricValue], ...]

    def __post_init__(self) -> None:
        if len(self.per_seed_terminal_losses) != CONFIRMATORY_SEED_COHORT.member_count.value:
            raise ScientificContractError(
                "FedProx terminal-loss candidates require the full confirmatory seed cohort",
                subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            )
        seeds = tuple(seed for seed, _loss in self.per_seed_terminal_losses)
        if seeds != CONFIRMATORY_SEED_COHORT.values:
            raise ScientificContractError(
                "FedProx terminal-loss candidates must use the locked confirmatory seed order",
                subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FedProxPrimaryCoefficientDecision:
    selection_rule: FedProxCoefficientSelectionRule
    primary_coefficient: ProximalCoefficient
    candidates: tuple[FedProxCoefficientTerminalLoss, ...]
    decision_checksum: Checksum


def fedprox_training_coordinate(training_seed: Seed, coefficient: ProximalCoefficient) -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=training_seed,
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
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
        round_frame, _client_frame, _personalized = history_frames(training_directory)
    except ArtifactIntegrityError as error:
        raise ScientificContractError(
            f"FedProx terminal training loss unavailable under {training_directory}: {error}",
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        ) from error
    matching = round_frame.filter(pl.col(FederatedHistoryColumn.ROUND_NUMBER.value) == maximum_round.value)
    if matching.height != 1:
        raise ScientificContractError(
            f"FedProx training history must contain exactly one row for terminal round {maximum_round.value}",
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
        seed_losses: list[tuple[Seed, MetricValue]] = []
        for seed in seed_cohort.values:
            directory = federated_training_directory(fedprox_training_coordinate(seed, coefficient), output_root)
            seed_losses.append(
                (
                    seed,
                    read_terminal_aggregate_training_loss(
                        directory,
                        maximum_round=CHECKPOINT_PROTOCOL.maximum_round,
                    ),
                )
            )
        candidates.append(
            FedProxCoefficientTerminalLoss(
                coefficient=coefficient,
                mean_terminal_training_loss=MetricValue(
                    sum(loss.value for _seed, loss in seed_losses) / len(seed_losses)
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
    decision_checksum = canonical_checksum((FEDPROX_COEFFICIENT_SELECTION_RULE, selected.coefficient, candidates))
    return FedProxPrimaryCoefficientDecision(
        selection_rule=FEDPROX_COEFFICIENT_SELECTION_RULE,
        primary_coefficient=selected.coefficient,
        candidates=candidates,
        decision_checksum=decision_checksum,
    )


def write_fedprox_primary_coefficient_decision(decision: FedProxPrimaryCoefficientDecision, destination: Path) -> Path:
    write_text_atomically(destination, canonical_json_text(decision))
    return destination


def load_fedprox_primary_coefficient_decision(destination: Path) -> FedProxPrimaryCoefficientDecision:
    try:
        adapter: TypeAdapter[FedProxPrimaryCoefficientDecision] = TypeAdapter(FedProxPrimaryCoefficientDecision)
        return adapter.validate_json(destination.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError) as error:
        raise ScientificContractError(
            f"FedProx primary-coefficient decision is unreadable or invalid: {destination}",
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
            "FedProx absorption reference evidence must match the observation seed",
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
        raise ScientificContractError("FedProx absorption requires FEDPROX_ABSORPTION_STRESS_TEST observations")
    if observations and any(
        item.personalized_model is not TrainingModelId.FEDPROX_AUTOENCODER for item in observations
    ):
        raise ScientificContractError("FedProx absorption requires FEDPROX personalized model identity")
    if observations and any(item.corners is None for item in observations):
        raise ScientificContractError(
            "FedProx absorption requires four-corner provenance on every seed observation",
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    cohort = decide_absorption_cohort(observations, MODEL_ABSORPTION_DECISION_PROTOCOL)
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
            "FedProx evaluation coordinate unresolved for "
            f"seed={training_seed.value} coefficient={coefficient.value} method={method.value}",
            subject=ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        )
    path = (
        evaluation_run_directory(OUTPUTS_ROOT, matches[0])
        / EvaluationRunAssetDirectory.EVALUATION
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(f"missing FedProx evaluation document: {path}")
    return path


def _population_cv_fpr_effect(result: DittoStressTestEvidence) -> tuple[MetricValue, MetricValue, MetricValue]:
    shared_population = calculate_population_metrics(result.shared_threshold_metrics, cohort=result.evaluation_cohort)
    local_population = calculate_population_metrics(result.local_threshold_metrics, cohort=result.evaluation_cohort)
    shared_cv = _required_population_cv(shared_population)
    local_cv = _required_population_cv(local_population)
    return shared_cv, local_cv, MetricValue(shared_cv.value - local_cv.value)


def _required_population_cv(population: PopulationMetricResult) -> MetricValue:
    outcome = metric_by_id(population.metrics, MetricId.FPR_COEFFICIENT_OF_VARIATION)
    if outcome.status is not MetricStatus.AVAILABLE or outcome.value is None:
        raise ScientificContractError("absorption requires available population CV(FPR) under both threshold methods")
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
    state_set_checksum = preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=client_with_id(clients, ClientIdentityToken(item.client_identity.value)),
                preprocessing_checksum=item.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return DittoPopulationContext(
        clients=clients,
        family_by_client=family_identities(
            clients,
            tuple(
                (ClientIdentityToken(client), FamilyIdentity(family))
                for client, family in population_result.construction.manifest.family_by_client
            ),
        ),
        preprocessing=preprocessing,
        split_manifest_checksum=population_result.split_manifest.assignment_checksum,
        preprocessing_state_set_checksum=state_set_checksum,
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
    for owned in sorted(training.personalized_candidates.items, key=lambda item: item.client):
        client = owned.client
        selection = select_federated_primary_checkpoint(
            SelectFederatedCheckpointRequest(
                coordinate=personalized_coordinate,
                client=client,
                candidates=owned.value,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                held_out_metrics=None,
                attack_labels_present=False,
            )
        )
        manifest = publish_federated_scores(
            GenerateFederatedScoresRequest(
                checkpoint=selection.selected,
                scored_split_protocol=selection.selected.coordinate.split_protocol,
                autoencoder=NBAIOT_AUTOENCODER,
                feature_names=feature_names,
                clients=(client_scoring_input(context.preprocessing.client_publications, client),),
                batch_size=BATCH_SIZE,
                output_directory=personalized_directory / client.client_id / ExecutionArtifactDirectory.SCORES,
                preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                overwrite=overwrite,
            )
        ).manifest
        manifests.append(ClientOwned(client=client, value=manifest))
        invariant = FixedScoreInvariant.from_manifest(manifest)
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
                checksum_file(record.path),
                invariant.calibration_score_set_checksum,
            )
        )
    if not eligible:
        raise ScientificContractError(
            "no client meets the minimum benign calibration support for threshold construction",
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
