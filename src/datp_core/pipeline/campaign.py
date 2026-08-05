"""Deterministic campaigns and the canonical confirmatory execution workflow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from shutil import rmtree
from typing import ClassVar

import polars as pl
from pydantic import ValidationError

from datp_core.analysis.contrasts import PairedContrast
from datp_core.analysis.temporal import TemporalDeploymentProvenance
from datp_core.anchor.models import VerifyAnchorStageRequest
from datp_core.datasets.catalogue import dataset_binding
from datp_core.datasets.edge_iiotset.schema import EDGE_NUMERIC_FEATURE_COLUMNS
from datp_core.domain.enums import (
    CentralizedModelId,
    DatasetId,
    EvaluationCohort,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ScoreFrameColumn,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import (
    ByteCount,
    Checksum,
    ClientCount,
    DittoRegularization,
    FamilyIdentity,
    FeatureName,
    FeatureNameSequence,
    MetricValue,
    ProximalCoefficient,
    ScoreValue,
    Seed,
    checksum_file,
)
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.cohorts import build_evaluation_cohort_manifest, client_partition_counts_from_scores
from datp_core.evaluation.confusion import calculate_confusion_counts
from datp_core.evaluation.controls import (
    FixedScoreEvidence,
    build_federated_evaluation_inputs,
    evaluation_label_checksum,
    source_row_checksum,
)
from datp_core.evaluation.models import ClientMetricResult, MetricStatus, metric_by_id
from datp_core.evaluation.population import FederatedEvaluationAssetName, FederatedEvaluationDocument
from datp_core.learning.centralized.training import CentralizedTrainingCoordinate
from datp_core.learning.federated.ditto import DittoTrainingRequest
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    FederatedTrainingCoordinate,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import FederatedTrainingRequest, preprocessing_state_set_checksum
from datp_core.pipeline.analyze_evidence import AnalyzeConfirmatoryEvidenceRequest, analyze_confirmatory_evidence
from datp_core.pipeline.construct_population import (
    ConstructDeclaredPopulationRequest,
    ConstructDeclaredPopulationResult,
    ConstructPublishedPopulationRequest,
    ConstructPublishedSplitRequest,
    construct_declared_population,
    construct_published_population,
    construct_published_split,
)
from datp_core.pipeline.construct_thresholds import (
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    ConstructCentralizedThresholdRequest,
    ConstructFederatedThresholdsRequest,
    construct_centralized_threshold,
    construct_federated_thresholds,
)
from datp_core.pipeline.evaluate_detector import (
    EvaluateCentralizedDetectorRequest,
    EvaluateCentralizedDetectorResult,
    EvaluateFederatedDetectorRequest,
    evaluate_centralized_detector,
    evaluate_federated_detector,
)
from datp_core.pipeline.execution import (
    ExecutionProvenance,
    ExistingExperimentState,
    ExperimentExecution,
    ExperimentOutputStore,
    PipelineStage,
    StageExecution,
    StageOutcome,
    StageRunner,
    execute_experiment,
)
from datp_core.pipeline.fit_preprocessing import (
    FitCentralizedPopulationPreprocessingRequest,
    FitFederatedPreprocessingRequest,
    FitFederatedPreprocessingResult,
    FitPublishedFederatedPreprocessingRequest,
    fit_centralized_population_preprocessing,
    fit_federated_preprocessing,
    fit_published_federated_preprocessing,
)
from datp_core.pipeline.generate_scores import (
    GenerateCentralizedScoresRequest,
    GenerateFederatedScoresRequest,
    generate_centralized_scores,
    generate_federated_scores,
)
from datp_core.pipeline.materialize_dataset import MaterializeDatasetRequest, materialize_dataset
from datp_core.pipeline.planning import (
    ExecutionRoute,
    ExperimentCoordinate,
    ExperimentPlan,
    PlanDisposition,
    execution_route_for,
)
from datp_core.pipeline.publication.completion import (
    build_completion_record,
    read_completion_record,
    write_completion_record,
)
from datp_core.pipeline.publication.layout import experiment_output_directory
from datp_core.pipeline.publication.records import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactState,
    CompletionState,
)
from datp_core.pipeline.publication.reload_validation import validate_reload
from datp_core.pipeline.scoring.service import ClientScoringInput, FederatedScoreArtifactManifest
from datp_core.pipeline.select_checkpoint import (
    SelectCentralizedCheckpointRequest,
    SelectFederatedCheckpointRequest,
    select_centralized_primary_checkpoint,
    select_federated_primary_checkpoint,
)
from datp_core.pipeline.train_detector import (
    TrainCentralizedDetectorRequest,
    TrainDittoDetectorRequest,
    TrainDittoDetectorResult,
    TrainFederatedDetectorRequest,
    train_centralized_detector,
    train_ditto_detector,
    train_federated_detector,
)
from datp_core.pipeline.verify_anchor import verify_anchor
from datp_core.populations.capabilities import population_capabilities
from datp_core.populations.catalogue import resolve_population
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.preprocessing.models import ClientPreprocessingResult
from datp_core.protocols.anchor import ANCHOR_DECISION_PROTOCOL
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.experiments import (
    BOUNDED_EVIDENCE_POPULATIONS,
    EXPERIMENTS,
    ExternalTemporalExecutionIdentity,
)
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.protocols.models import AutoencoderProtocol, DittoProtocol, FedAvgProtocol, FedProxProtocol
from datp_core.protocols.populations import split_protocol_for_population
from datp_core.protocols.runtime import DATA_ROOT, OUTPUTS_ROOT
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    DITTO_TRAINING_PROTOCOLS,
    EDGE_IIOTSET_NUMERIC_AUTOENCODER,
    FEDAVG_TRAINING_PROTOCOL,
    FEDPROX_TRAINING_PROTOCOLS,
    LEARNING_RATE,
    NBAIOT_AUTOENCODER,
)
from datp_core.thresholding.assignments import ThresholdAssignment
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult
from datp_core.thresholding.methods.local import LocalThresholdResult
from datp_core.thresholding.methods.shared import SharedThresholdResult
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignEntry:
    ordinal: int
    coordinate: ExperimentCoordinate

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("campaign ordinals must be non-negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignPlan:
    entries: tuple[CampaignEntry, ...]
    digest: str
    plan_digest: Checksum

    def __post_init__(self) -> None:
        if tuple(item.ordinal for item in self.entries) != tuple(range(len(self.entries))):
            raise ValueError("campaign entries must use contiguous deterministic ordinals")
        if self.digest != _campaign_digest(self.entries):
            raise ValueError("campaign digest does not match campaign entries")


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignExecution:
    campaign_digest: str
    experiments: tuple[ExperimentExecution, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatorySeedContext:
    coordinate: FederatedTrainingCoordinate
    population: ConstructDeclaredPopulationResult
    preprocessing: FitFederatedPreprocessingResult
    state_set_checksum: Checksum
    training_directory: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatoryThresholdInputs:
    scores: FederatedScoreArtifactManifest
    eligible: tuple[ClientBenignCalibrationScores, ...]
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...]
    previous_evidence: FixedScoreEvidence | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishedSeedContext:
    coordinate: FederatedTrainingCoordinate
    execution_identity: ExternalTemporalExecutionIdentity | None
    clients: tuple[ClientIdentity, ...]
    family_by_client: tuple[tuple[str, str], ...]
    preprocessing: FitFederatedPreprocessingResult
    state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    training_directory: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoStressTestResult:
    """Ditto's declared personalized-model threshold-scope comparison (roadmap 7.2/11.2).

    SHARED_THRESHOLD and LOCAL_THRESHOLD are both constructed from the PERSONALIZED
    per-client scores only (never the global model, which would confound model identity,
    score geometry, and threshold-calibration scope in one comparison). Personalized
    clients are expected to carry distinct model/score checksums from each other; the
    controlled comparison instead holds each client's own model, preprocessing state,
    calibration rows, and evaluation rows fixed across the two threshold policies."""

    personalized_coordinate: FederatedTrainingCoordinate
    shared_threshold: SharedThresholdResult
    local_threshold: LocalThresholdResult
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]


def build_campaign(plan: ExperimentPlan) -> CampaignPlan:
    """Build the generic single-coordinate campaign from executable plan entries.

    Only ExecutionRoute.SINGLE_COORDINATE coordinates are included: Ditto and
    temporal-paired coordinates require their dedicated joint workflow (see
    pipeline.planning.execution_route_for) and are never executed through
    execute_experiment/GeneralStageRunner, so they are not campaign cells here.
    """
    coordinates = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.disposition is PlanDisposition.EXECUTABLE
        and execution_route_for(entry.coordinate) is ExecutionRoute.SINGLE_COORDINATE
    )
    entries = tuple(CampaignEntry(ordinal=index, coordinate=coordinate) for index, coordinate in enumerate(coordinates))
    return CampaignPlan(entries=entries, digest=_campaign_digest(entries), plan_digest=Checksum(plan.digest))


def protocol_digest() -> Checksum:
    """Checksum the validated protocol declaration graph a plan was expanded against."""
    return canonical_checksum(EXPERIMENTS)


def execute_campaign(
    *,
    campaign: CampaignPlan,
    stage_runner: StageRunner,
    output_store: ExperimentOutputStore,
    output_root: Path,
) -> CampaignExecution:
    provenance = ExecutionProvenance(
        plan_digest=campaign.plan_digest,
        campaign_digest=Checksum(campaign.digest),
        protocol_digest=protocol_digest(),
    )
    experiments = tuple(
        execute_experiment(
            coordinate=entry.coordinate,
            provenance=provenance,
            stage_runner=stage_runner,
            output_store=output_store,
            output_root=output_root,
        )
        for entry in campaign.entries
    )
    return CampaignExecution(campaign_digest=campaign.digest, experiments=experiments)


def run_confirmatory_seed(training_seed: Seed) -> tuple[FederatedThresholdMethod, ...]:
    context = _prepare_confirmatory_seed(training_seed)
    inputs = ConfirmatoryThresholdInputs(
        scores=_score_confirmatory_seed(context),
        eligible=(),
        family_by_client=(),
        previous_evidence=None,
    )
    inputs = ConfirmatoryThresholdInputs(
        scores=inputs.scores,
        eligible=_eligible_calibration_scores(inputs.scores),
        family_by_client=_family_identities(
            context.population.construction.manifest.clients,
            context.population.construction.manifest.family_by_client,
        ),
        previous_evidence=None,
    )
    completed: list[FederatedThresholdMethod] = []
    for method in population_capabilities(context.coordinate.population).valid_threshold_methods:
        inputs, available = _evaluate_confirmatory_threshold_method(context, inputs, method)
        if available:
            completed.append(method)
    return tuple(completed)


def run_confirmatory_campaign() -> tuple[tuple[Seed, tuple[FederatedThresholdMethod, ...]], ...]:
    return tuple((seed, run_confirmatory_seed(seed)) for seed in CONFIRMATORY_SEED_COHORT.values)


def analyze_confirmatory_campaign() -> Path:
    output = OUTPUTS_ROOT / "confirmatory" / PopulationId.NBAIOT_NATURAL_DEVICES.value / "analysis"
    analyze_confirmatory_evidence(
        AnalyzeConfirmatoryEvidenceRequest(
            contrasts=tuple(_confirmatory_contrast(seed) for seed in CONFIRMATORY_SEED_COHORT.values),
            inference_protocol=CONFIRMATORY_INFERENCE_PROTOCOL,
            analysis_seed=Seed(31),
            output_directory=output,
            overwrite=False,
        )
    )
    return output


def run_centralized_reference_seed(training_seed: Seed) -> EvaluateCentralizedDetectorResult:
    """Train, checkpoint-select, score, threshold, and evaluate the centralized reference
    for one seed on the confirmatory N-BaIoT population.

    The centralized reference is the roadmap's privacy-incompatible upper-bound comparator
    (roadmap section 4.1) and is structurally outside the federated threshold-scope ladder:
    its own pooled model, its own pooled preprocessing, and its own POOLED_BENIGN_QUANTILE
    threshold policy, never a federated checkpoint or a federated threshold method."""
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    population_result = construct_declared_population(
        ConstructDeclaredPopulationRequest(
            population=population,
            dataset=DatasetId.NBAIOT,
            canonical_root=DATA_ROOT / "canonical" / DatasetId.NBAIOT.value,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            controlled_condition=None,
        )
    )
    preprocessing = fit_centralized_population_preprocessing(
        FitCentralizedPopulationPreprocessingRequest(
            population=population,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            data_root=DATA_ROOT,
            dirichlet_condition=None,
            capture_timestamp_column=None,
        )
    )
    coordinate = CentralizedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    )
    directory = _centralized_reference_directory(training_seed)
    feature_names = _training_feature_names(DatasetId.NBAIOT)
    split_checksum = population_result.split_manifest.assignment_checksum
    preprocessing_checksum = preprocessing.result.fitted_state.estimator_checksum
    training = train_centralized_detector(
        TrainCentralizedDetectorRequest(
            coordinate=coordinate,
            training_features=pl.read_parquet(preprocessing.result.paths.train),
            feature_names=feature_names,
            preprocessing_state=preprocessing.result.fitted_state,
            split_manifest_checksum=split_checksum,
            output_directory=directory / "training",
            training_seed=training_seed,
            autoencoder=NBAIOT_AUTOENCODER,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            overwrite=False,
        )
    )
    selection = select_centralized_primary_checkpoint(
        SelectCentralizedCheckpointRequest(
            coordinate=coordinate,
            candidates=training.candidates,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            preprocessing_checksum=preprocessing_checksum,
            split_checksum=split_checksum,
            training_seed=training_seed,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    )
    scores = generate_centralized_scores(
        GenerateCentralizedScoresRequest(
            coordinate=coordinate,
            checkpoint=selection.decision.selected,
            autoencoder=NBAIOT_AUTOENCODER,
            feature_names=feature_names,
            calibration_features=pl.read_parquet(preprocessing.result.paths.calibration),
            evaluation_features=pl.read_parquet(preprocessing.result.paths.evaluation),
            batch_size=BATCH_SIZE,
            output_directory=directory / "scores",
            preprocessing_state_checksum=preprocessing_checksum,
            overwrite=False,
        )
    )
    threshold = construct_centralized_threshold(
        ConstructCentralizedThresholdRequest(
            coordinate=coordinate,
            calibration_scores=scores.scoring.calibration_scores,
            output_directory=directory / "threshold",
            protocol=CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
            overwrite=False,
        )
    )
    return evaluate_centralized_detector(
        EvaluateCentralizedDetectorRequest(
            coordinate=coordinate,
            evaluation_scores=scores.scoring.evaluation_scores,
            threshold=threshold.threshold,
            output_directory=directory / "evaluation",
            overwrite=False,
        )
    )


def _centralized_reference_directory(training_seed: Seed) -> Path:
    return OUTPUTS_ROOT / "centralized_reference" / PopulationId.NBAIOT_NATURAL_DEVICES.value / str(training_seed.value)


def _ditto_training_protocol_for(regularization: DittoRegularization) -> DittoProtocol:
    matches = tuple(
        protocol for protocol in DITTO_TRAINING_PROTOCOLS if protocol.regularization.value == regularization.value
    )
    if len(matches) != 1:
        raise ScientificContractError(
            "a Ditto regularization value must resolve to exactly one declared training protocol",
            subject=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        )
    return matches[0]


def _ditto_directory(training_seed: Seed, regularization: DittoRegularization, branch: str) -> Path:
    return (
        OUTPUTS_ROOT
        / "ditto_stress_test"
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / str(training_seed.value)
        / str(regularization.value)
        / branch
    )


def _client_scoring_input(
    publications: tuple[ClientPreprocessingResult, ...], client: ClientIdentity
) -> ClientScoringInput:
    publication = next(item for item in publications if item.client_identity.value == client.client_id)
    return ClientScoringInput(
        client,
        pl.read_parquet(publication.paths.calibration),
        pl.read_parquet(publication.paths.evaluation),
    )


def _ditto_client_metric(
    coordinate: FederatedTrainingCoordinate,
    threshold_method: FederatedThresholdMethod,
    population: PopulationId,
    manifest: FederatedScoreArtifactManifest,
    assignment: ThresholdAssignment,
) -> ClientMetricResult:
    record = next(item for item in manifest.evaluation_records if item.scored_client == assignment.client)
    frame = pl.read_parquet(record.path)
    scores = tuple(ScoreValue(float(value)) for value in frame[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list())
    labels = tuple(
        PopulationOutcomeLabel(str(value)) for value in frame[ScoreFrameColumn.OUTCOME_LABEL.value].to_list()
    )
    rows = tuple(str(value) for value in frame[ScoreFrameColumn.STABLE_ROW_ID.value].to_list())
    cohort_manifest = build_evaluation_cohort_manifest(
        population=population,
        partition_seed=coordinate.training_seed,
        client_counts=client_partition_counts_from_scores(manifest),
    )
    eligibility = next(item for item in cohort_manifest.records if item.client == assignment.client)
    confusion = calculate_confusion_counts(
        scores=scores,
        labels=labels,
        source_row_ids=rows,
        threshold=assignment.threshold,
        partition_role=PartitionRole.EVALUATION,
        attack_assignment_valid=eligibility.attack_evaluable,
    )
    if eligibility.fpr_evaluable:
        cohort = EvaluationCohort.FPR_EVALUABLE
    elif eligibility.deployment_fallback:
        cohort = EvaluationCohort.DEPLOYMENT_FALLBACK
    else:
        cohort = EvaluationCohort.UNAVAILABLE
    return ClientMetricResult(
        coordinate=coordinate,
        threshold_method=threshold_method,
        cohort=cohort,
        client=assignment.client,
        threshold=assignment.threshold,
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=population_capabilities(population).evidentiary_role,
        evaluation_score_checksum=record.checksum,
        evaluation_label_checksum=evaluation_label_checksum(labels),
        source_row_checksum=source_row_checksum(rows),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class _DittoPopulationContext:
    clients: tuple[ClientIdentity, ...]
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...]
    preprocessing: FitFederatedPreprocessingResult
    split_manifest_checksum: Checksum
    state_set_checksum: Checksum


def _ditto_population_context(
    *,
    training_seed: Seed,
    population: PopulationId,
    split_protocol: SplitProtocolId,
    preprocessing_identity: PreprocessingProtocolId,
) -> _DittoPopulationContext:
    population_result = construct_declared_population(
        ConstructDeclaredPopulationRequest(
            population=population,
            dataset=DatasetId.NBAIOT,
            canonical_root=DATA_ROOT / "canonical" / DatasetId.NBAIOT.value,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            controlled_condition=None,
        )
    )
    preprocessing = fit_federated_preprocessing(
        FitFederatedPreprocessingRequest(
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
                client=_client_with_id(clients, item.client_identity.value),
                preprocessing_checksum=item.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return _DittoPopulationContext(
        clients=clients,
        family_by_client=_family_identities(clients, population_result.construction.manifest.family_by_client),
        preprocessing=preprocessing,
        split_manifest_checksum=population_result.split_manifest.assignment_checksum,
        state_set_checksum=state_set_checksum,
    )


def _ditto_personalized_client_scores(
    *,
    training: TrainDittoDetectorResult,
    personalized_coordinate: FederatedTrainingCoordinate,
    context: _DittoPopulationContext,
    feature_names: FeatureNameSequence,
    training_seed: Seed,
    regularization: DittoRegularization,
    overwrite: bool,
) -> tuple[tuple[ClientBenignCalibrationScores, ...], dict[ClientIdentity, FederatedScoreArtifactManifest]]:
    eligible: list[ClientBenignCalibrationScores] = []
    manifests_by_client: dict[ClientIdentity, FederatedScoreArtifactManifest] = {}
    for owned in sorted(training.personalized_candidates.items, key=lambda item: item.client):
        client = owned.client
        selection = select_federated_primary_checkpoint(
            SelectFederatedCheckpointRequest(
                coordinate=personalized_coordinate,
                client=client,
                candidates=owned.value,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                preprocessing_state_set_checksum=context.state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                held_out_metrics=None,
                attack_labels_present=False,
            )
        )
        scores = generate_federated_scores(
            GenerateFederatedScoresRequest(
                checkpoint=selection.decision.selected,
                autoencoder=NBAIOT_AUTOENCODER,
                feature_names=feature_names,
                clients=(_client_scoring_input(context.preprocessing.client_publications, client),),
                batch_size=BATCH_SIZE,
                output_directory=(
                    _ditto_directory(training_seed, regularization, "personalized") / client.client_id / "scores"
                ),
                preprocessing_state_set_checksum=context.state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                overwrite=overwrite,
            )
        ).result.manifest
        manifests_by_client[client] = scores
        invariant = FixedScoreInvariant.from_manifest(scores)
        record = next(item for item in scores.calibration_records if item.scored_client == client)
        eligible.append(
            ClientBenignCalibrationScores(
                client,
                personalized_coordinate,
                tuple(
                    float(value)
                    for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
                ),
                checksum_file(record.path),
                invariant.calibration_score_set_checksum,
            )
        )
    return tuple(eligible), manifests_by_client


def run_ditto_stress_test_seed(
    *,
    training_seed: Seed,
    regularization: DittoRegularization,
    overwrite: bool = False,
) -> DittoStressTestResult:
    """Train Ditto's joint global/personalized publication (roadmap 7.2), then construct and
    evaluate SHARED_THRESHOLD and LOCAL_THRESHOLD from the PERSONALIZED per-client scores only.

    SHARED_THRESHOLD means every eligible client deploys the identical value
    unweighted_mean(local_quantile_i for all i); LOCAL_THRESHOLD means each client deploys its
    own local_quantile_i. Both constructions already tolerate distinct per-client score-set
    checksums (thresholding.methods.shared.construct_shared_threshold and
    methods.local.construct_local_threshold require no cross-client checksum equality, unlike
    the pooled-scores POOLED_SHARED_QUANTILE method) so no relaxation of any existing scientific
    invariant was needed. Both policies reuse the SAME per-client personalized checkpoint,
    preprocessing state, calibration rows, and evaluation rows -- only the threshold-calibration
    scope differs, which is the controlled comparison the roadmap requires."""
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    context = _ditto_population_context(
        training_seed=training_seed,
        population=population,
        split_protocol=split_protocol,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    )
    global_coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.DITTO_GLOBAL_AUTOENCODER,
        model_coefficient=None,
    )
    personalized_coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        model_coefficient=regularization,
    )
    feature_names = _training_feature_names(DatasetId.NBAIOT)
    training = train_ditto_detector(
        TrainDittoDetectorRequest(
            request=DittoTrainingRequest(
                global_coordinate=global_coordinate,
                personalized_coordinate=personalized_coordinate,
                clients=_client_training_inputs(
                    context.preprocessing.client_publications, context.clients, feature_names
                ),
                population_client_count=ClientCount(len(context.clients)),
                autoencoder=NBAIOT_AUTOENCODER,
                training_protocol=_ditto_training_protocol_for(regularization),
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                training_seed=training_seed,
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                split_manifest_checksum=context.split_manifest_checksum,
                global_output_directory=_ditto_directory(training_seed, regularization, "global"),
                personalized_output_directory=_ditto_directory(training_seed, regularization, "personalized"),
            ),
            overwrite=overwrite,
        )
    )
    eligible, manifests_by_client = _ditto_personalized_client_scores(
        training=training,
        personalized_coordinate=personalized_coordinate,
        context=context,
        feature_names=feature_names,
        training_seed=training_seed,
        regularization=regularization,
        overwrite=overwrite,
    )
    capabilities = population_capabilities(population)
    threshold_directory = _ditto_directory(training_seed, regularization, "threshold")
    shared = construct_federated_thresholds(
        ConstructFederatedThresholdsRequest(
            request=ThresholdConstructionRequest(
                FederatedThresholdMethod.SHARED_THRESHOLD,
                personalized_coordinate,
                CANONICAL_QUANTILE,
                capabilities,
                eligible,
                context.family_by_client,
            ),
            output_directory=threshold_directory / "shared",
            overwrite=overwrite,
        )
    ).result
    local = construct_federated_thresholds(
        ConstructFederatedThresholdsRequest(
            request=ThresholdConstructionRequest(
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                personalized_coordinate,
                CANONICAL_QUANTILE,
                capabilities,
                eligible,
                context.family_by_client,
            ),
            output_directory=threshold_directory / "local",
            overwrite=overwrite,
        )
    ).result
    if not isinstance(shared, SharedThresholdResult):
        raise ScientificContractError(
            "Ditto SHARED_THRESHOLD construction must produce a shared threshold result",
            subject=personalized_coordinate.model,
        )
    if not isinstance(local, LocalThresholdResult):
        raise ScientificContractError(
            "Ditto LOCAL_THRESHOLD construction must produce a local threshold result",
            subject=personalized_coordinate.model,
        )
    return DittoStressTestResult(
        personalized_coordinate=personalized_coordinate,
        shared_threshold=shared,
        local_threshold=local,
        shared_threshold_metrics=tuple(
            _ditto_client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.SHARED_THRESHOLD,
                population,
                manifests_by_client[assignment.client],
                assignment,
            )
            for assignment in shared.assignments
        ),
        local_threshold_metrics=tuple(
            _ditto_client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                population,
                manifests_by_client[assignment.client],
                assignment,
            )
            for assignment in local.assignments
        ),
    )


def run_published_seed(
    *,
    execution_identity: ExternalTemporalExecutionIdentity,
    dataset: DatasetId,
    partition_seed: Seed,
    training_seed: Seed,
    preprocessing_identity: PreprocessingProtocolId,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
    overwrite: bool = False,
) -> tuple[FederatedThresholdMethod, ...]:
    """Run federated preprocessing, training, scoring, thresholds, and evaluation for one
    bounded-evidence (external/applicability-boundary/temporal-boundary) population seed."""
    context = _prepare_published_seed(
        execution_identity=execution_identity,
        dataset=dataset,
        partition_seed=partition_seed,
        training_seed=training_seed,
        preprocessing_identity=preprocessing_identity,
        overwrite=overwrite,
    )
    scores = _score_published_seed(context, autoencoder, feature_names, overwrite=overwrite)
    inputs = ConfirmatoryThresholdInputs(
        scores=scores,
        eligible=_eligible_calibration_scores(scores),
        family_by_client=_family_identities(context.clients, context.family_by_client),
        previous_evidence=None,
    )
    completed: list[FederatedThresholdMethod] = []
    for method in population_capabilities(context.coordinate.population).valid_threshold_methods:
        inputs, available = _evaluate_published_threshold_method(context, inputs, method)
        if available:
            completed.append(method)
    return tuple(completed)


def _published_seed_directory(execution_identity: ExternalTemporalExecutionIdentity, partition_seed: Seed) -> Path:
    temporal = execution_identity.temporal_state.value if execution_identity.temporal_state is not None else "static"
    return OUTPUTS_ROOT / "phase11" / execution_identity.population.value / str(partition_seed.value) / temporal


def _prepare_published_seed(
    *,
    execution_identity: ExternalTemporalExecutionIdentity,
    dataset: DatasetId,
    partition_seed: Seed,
    training_seed: Seed,
    preprocessing_identity: PreprocessingProtocolId,
    overwrite: bool,
) -> PublishedSeedContext:
    population = execution_identity.population
    split_protocol = split_protocol_for_population(population)
    root = _published_seed_directory(execution_identity, partition_seed)
    population_result = construct_published_population(
        ConstructPublishedPopulationRequest(
            canonical_root=DATA_ROOT / "canonical" / dataset.value,
            population=population,
            execution_identity=execution_identity,
            partition_seed=partition_seed,
            split_protocol=split_protocol,
            output_directory=root / "population",
            overwrite=overwrite,
        )
    )
    split_result = construct_published_split(
        ConstructPublishedSplitRequest(
            population=population,
            execution_identity=execution_identity,
            population_manifest=population_result.population_manifest,
            membership=population_result.membership,
            partition_seed=partition_seed,
            output_directory=root / "split",
            overwrite=overwrite,
            matched_static_reference_manifest=population_result.matched_static_reference_manifest,
            matched_static_reference_membership=population_result.matched_static_reference_membership,
        )
    )
    coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    preprocessing = fit_published_federated_preprocessing(
        FitPublishedFederatedPreprocessingRequest(
            execution_identity=execution_identity,
            population_directory=root / "population",
            split_directory=root / "split",
            preprocessing_identity=preprocessing_identity,
            data_root=DATA_ROOT,
        )
    )
    identity_kind = resolve_population(population).declaration.identity_kind
    state_set_checksum = preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=ClientIdentity(population, item.client_identity.value, identity_kind),
                preprocessing_checksum=item.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return PublishedSeedContext(
        coordinate=coordinate,
        execution_identity=execution_identity,
        clients=population_result.population_manifest.clients,
        family_by_client=population_result.population_manifest.family_by_client,
        preprocessing=preprocessing,
        state_set_checksum=state_set_checksum,
        split_manifest_checksum=split_result.manifest.assignment_checksum,
        training_directory=_federated_training_directory(coordinate),
    )


def _score_published_seed(
    context: PublishedSeedContext,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
    *,
    overwrite: bool,
) -> FederatedScoreArtifactManifest:
    training = train_federated_detector(
        TrainFederatedDetectorRequest(
            request=FederatedTrainingRequest(
                coordinate=context.coordinate,
                clients=_client_training_inputs(
                    context.preprocessing.client_publications,
                    context.clients,
                    feature_names,
                ),
                population_client_count=ClientCount(len(context.clients)),
                autoencoder=autoencoder,
                training_protocol=FEDAVG_TRAINING_PROTOCOL,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                training_seed=context.coordinate.training_seed,
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                split_manifest_checksum=context.split_manifest_checksum,
                output_directory=context.training_directory,
            ),
            overwrite=overwrite,
        )
    )
    selected = select_federated_primary_checkpoint(
        SelectFederatedCheckpointRequest(
            coordinate=context.coordinate,
            client=None,
            candidates=training.candidates,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            preprocessing_state_set_checksum=context.state_set_checksum,
            split_manifest_checksum=context.split_manifest_checksum,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    ).decision.selected
    return generate_federated_scores(
        GenerateFederatedScoresRequest(
            checkpoint=selected,
            autoencoder=autoencoder,
            feature_names=feature_names,
            clients=_client_scoring_inputs(context.preprocessing.client_publications, context.clients),
            batch_size=BATCH_SIZE,
            output_directory=context.training_directory / "scores",
            preprocessing_state_set_checksum=context.state_set_checksum,
            split_manifest_checksum=context.split_manifest_checksum,
            overwrite=overwrite,
        )
    ).result.manifest


def _evaluate_published_threshold_method(
    context: PublishedSeedContext,
    inputs: ConfirmatoryThresholdInputs,
    method: FederatedThresholdMethod,
) -> tuple[ConfirmatoryThresholdInputs, bool]:
    if context.execution_identity is None:
        raise ScientificContractError(
            "published threshold evaluation requires a bounded-evidence execution identity",
            subject=context.coordinate.population,
        )
    seed_directory = _published_seed_directory(context.execution_identity, context.coordinate.training_seed)
    threshold = construct_federated_thresholds(
        ConstructFederatedThresholdsRequest(
            request=ThresholdConstructionRequest(
                method,
                context.coordinate,
                CANONICAL_QUANTILE,
                population_capabilities(context.coordinate.population),
                inputs.eligible,
                inputs.family_by_client,
            ),
            output_directory=seed_directory / "thresholds" / method.value,
            overwrite=False,
        )
    ).result
    if isinstance(threshold, ThresholdUnavailableResult):
        return inputs, False
    evaluation_inputs = build_federated_evaluation_inputs(inputs.scores, method)
    evaluation = evaluate_federated_detector(
        EvaluateFederatedDetectorRequest(
            score_manifest=inputs.scores,
            threshold_result=threshold,
            cohort=evaluation_inputs.cohort,
            fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
            comparison_fixed_score_evidence=inputs.previous_evidence,
            evidence_role=context.execution_identity.evidence_role,
            conformal_coverage_inputs=(),
            threshold_estimation_inputs=(),
            communication_messages=(),
            traffic_rate_evidence=None,
            execution_identity=context.execution_identity,
            output_directory=seed_directory / "evaluations" / method.value,
            overwrite=False,
        )
    )
    return (
        ConfirmatoryThresholdInputs(
            scores=inputs.scores,
            eligible=inputs.eligible,
            family_by_client=inputs.family_by_client,
            previous_evidence=evaluation_inputs.fixed_score_evidence,
        ),
        bool(evaluation.complete_digest.value),
    )


def run_temporal_future_pair(
    *,
    partition_seed: Seed,
    training_seed: Seed,
    preprocessing_identity: PreprocessingProtocolId,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
    overwrite: bool = False,
) -> dict[TemporalState, tuple[FederatedThresholdMethod, ...]]:
    """Train and score one shared historical Edge-temporal detector once, then construct
    and evaluate frozen-future and recalibrated-future thresholds from its calibration
    and future-recalibration partitions respectively. Only the calibration window
    differs between the two states; detector, preprocessing, split, and evaluation
    scores are identical by construction (see analysis.temporal.validate_frozen_recalibrated_pair)."""
    frozen_identity = ExternalTemporalExecutionIdentity(
        experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
        population=PopulationId.EDGE_TEMPORAL_GROUPS,
        evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
        temporal_state=TemporalState.FROZEN_FUTURE,
    )
    context = _prepare_published_seed(
        execution_identity=frozen_identity,
        dataset=DatasetId.EDGE_IIOTSET,
        partition_seed=partition_seed,
        training_seed=training_seed,
        preprocessing_identity=preprocessing_identity,
        overwrite=overwrite,
    )
    scores = _score_published_seed(context, autoencoder, feature_names, overwrite=overwrite)
    results: dict[TemporalState, tuple[FederatedThresholdMethod, ...]] = {}
    for state, calibration_role in (
        (TemporalState.FROZEN_FUTURE, PartitionRole.CALIBRATION),
        (TemporalState.RECALIBRATED_FUTURE, PartitionRole.FUTURE_RECALIBRATION),
    ):
        identity = ExternalTemporalExecutionIdentity(
            experiment=ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            population=PopulationId.EDGE_TEMPORAL_GROUPS,
            evidence_role=EvidenceRole.TEMPORAL_BOUNDARY,
            temporal_state=state,
        )
        provenance = TemporalDeploymentProvenance.from_score_manifest(state, scores)
        inputs = ConfirmatoryThresholdInputs(
            scores=scores,
            eligible=_eligible_calibration_scores_for_role(scores, calibration_role),
            family_by_client=_family_identities(context.clients, context.family_by_client),
            previous_evidence=None,
        )
        completed: list[FederatedThresholdMethod] = []
        for method in population_capabilities(context.coordinate.population).valid_threshold_methods:
            inputs, available = _evaluate_temporal_threshold_method(
                context,
                identity,
                provenance,
                inputs,
                method,
            )
            if available:
                completed.append(method)
        results[state] = tuple(completed)
    return results


def _evaluate_temporal_threshold_method(
    context: PublishedSeedContext,
    identity: ExternalTemporalExecutionIdentity,
    provenance: TemporalDeploymentProvenance,
    inputs: ConfirmatoryThresholdInputs,
    method: FederatedThresholdMethod,
) -> tuple[ConfirmatoryThresholdInputs, bool]:
    seed_directory = _published_seed_directory(identity, context.coordinate.training_seed)
    threshold = construct_federated_thresholds(
        ConstructFederatedThresholdsRequest(
            request=ThresholdConstructionRequest(
                method,
                context.coordinate,
                CANONICAL_QUANTILE,
                population_capabilities(context.coordinate.population),
                inputs.eligible,
                inputs.family_by_client,
            ),
            output_directory=seed_directory / "thresholds" / method.value,
            overwrite=False,
            temporal_provenance=provenance,
            temporal_score_manifest=inputs.scores,
        )
    ).result
    if isinstance(threshold, ThresholdUnavailableResult):
        return inputs, False
    evaluation_inputs = build_federated_evaluation_inputs(inputs.scores, method)
    evaluation = evaluate_federated_detector(
        EvaluateFederatedDetectorRequest(
            score_manifest=inputs.scores,
            threshold_result=threshold,
            cohort=evaluation_inputs.cohort,
            fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
            comparison_fixed_score_evidence=inputs.previous_evidence,
            evidence_role=identity.evidence_role,
            conformal_coverage_inputs=(),
            threshold_estimation_inputs=(),
            communication_messages=(),
            traffic_rate_evidence=None,
            execution_identity=identity,
            temporal_provenance=provenance,
            temporal_threshold_provenance=provenance,
            output_directory=seed_directory / "evaluations" / method.value,
            overwrite=False,
        )
    )
    return (
        ConfirmatoryThresholdInputs(
            scores=inputs.scores,
            eligible=inputs.eligible,
            family_by_client=inputs.family_by_client,
            previous_evidence=evaluation_inputs.fixed_score_evidence,
        ),
        bool(evaluation.complete_digest.value),
    )


def _eligible_calibration_scores_for_role(
    score_manifest: FederatedScoreArtifactManifest,
    role: PartitionRole,
) -> tuple[ClientBenignCalibrationScores, ...]:
    invariant = FixedScoreInvariant.from_manifest(score_manifest)
    set_checksum = (
        invariant.calibration_score_set_checksum
        if role is PartitionRole.CALIBRATION
        else invariant.future_recalibration_score_set_checksum
    )
    if set_checksum is None:
        raise ScientificContractError(
            "temporal recalibration eligibility requires a future-recalibration score set",
            subject=role,
        )
    return tuple(
        ClientBenignCalibrationScores(
            record.scored_client,
            score_manifest.coordinate,
            tuple(
                float(value)
                for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
            ),
            checksum_file(record.path),
            set_checksum,
        )
        for record in sorted(score_manifest.records_for(role), key=lambda item: item.scored_client)
    )


def _prepare_confirmatory_seed(training_seed: Seed) -> ConfirmatorySeedContext:
    population = PopulationId.NBAIOT_NATURAL_DEVICES
    split_protocol = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    preprocessing_identity = PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
    coordinate = FederatedTrainingCoordinate(
        population=population,
        training_seed=training_seed,
        split_protocol=split_protocol,
        preprocessing_identity=preprocessing_identity,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )
    population_result = construct_declared_population(
        ConstructDeclaredPopulationRequest(
            population=population,
            dataset=DatasetId.NBAIOT,
            canonical_root=DATA_ROOT / "canonical" / DatasetId.NBAIOT.value,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            controlled_condition=None,
        )
    )
    preprocessing = fit_federated_preprocessing(
        FitFederatedPreprocessingRequest(
            population=population,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            preprocessing_identity=preprocessing_identity,
            data_root=DATA_ROOT,
            dirichlet_condition=None,
            capture_timestamp_column=None,
        )
    )
    identity_kind = resolve_population(population).declaration.identity_kind
    state_set_checksum = preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=ClientIdentity(population, item.client_identity.value, identity_kind),
                preprocessing_checksum=item.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return ConfirmatorySeedContext(
        coordinate=coordinate,
        population=population_result,
        preprocessing=preprocessing,
        state_set_checksum=state_set_checksum,
        training_directory=_federated_training_directory(coordinate),
    )


def _score_confirmatory_seed(context: ConfirmatorySeedContext) -> FederatedScoreArtifactManifest:
    feature_names = FeatureNameSequence(
        tuple(FeatureName(name) for name in dataset_binding(DatasetId.NBAIOT).schema.feature_columns)
    )
    training = train_federated_detector(
        TrainFederatedDetectorRequest(
            request=FederatedTrainingRequest(
                coordinate=context.coordinate,
                clients=_client_training_inputs(
                    context.preprocessing.client_publications,
                    context.population.construction.manifest.clients,
                    feature_names,
                ),
                population_client_count=ClientCount(
                    len(context.population.construction.manifest.document.accepted_clients)
                ),
                autoencoder=NBAIOT_AUTOENCODER,
                training_protocol=FEDAVG_TRAINING_PROTOCOL,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                training_seed=context.coordinate.training_seed,
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                split_manifest_checksum=context.population.split_manifest.assignment_checksum,
                output_directory=context.training_directory,
            ),
            overwrite=False,
        )
    )
    selected = select_federated_primary_checkpoint(
        SelectFederatedCheckpointRequest(
            coordinate=context.coordinate,
            client=None,
            candidates=training.candidates,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            preprocessing_state_set_checksum=context.state_set_checksum,
            split_manifest_checksum=context.population.split_manifest.assignment_checksum,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    ).decision.selected
    return generate_federated_scores(
        GenerateFederatedScoresRequest(
            checkpoint=selected,
            autoencoder=NBAIOT_AUTOENCODER,
            feature_names=feature_names,
            clients=_client_scoring_inputs(
                context.preprocessing.client_publications,
                context.population.construction.manifest.clients,
            ),
            batch_size=BATCH_SIZE,
            output_directory=context.training_directory / "scores",
            preprocessing_state_set_checksum=context.state_set_checksum,
            split_manifest_checksum=context.population.split_manifest.assignment_checksum,
            overwrite=False,
        )
    ).result.manifest


def _evaluate_confirmatory_threshold_method(
    context: ConfirmatorySeedContext,
    inputs: ConfirmatoryThresholdInputs,
    method: FederatedThresholdMethod,
) -> tuple[ConfirmatoryThresholdInputs, bool]:
    threshold = construct_federated_thresholds(
        ConstructFederatedThresholdsRequest(
            request=ThresholdConstructionRequest(
                method,
                context.coordinate,
                CANONICAL_QUANTILE,
                population_capabilities(context.coordinate.population),
                inputs.eligible,
                inputs.family_by_client,
            ),
            output_directory=_confirmatory_seed_directory(context.coordinate.training_seed)
            / "thresholds"
            / method.value,
            overwrite=False,
        )
    ).result
    if isinstance(threshold, ThresholdUnavailableResult):
        return inputs, False
    evaluation_inputs = build_federated_evaluation_inputs(inputs.scores, method)
    evaluation = evaluate_federated_detector(
        EvaluateFederatedDetectorRequest(
            score_manifest=inputs.scores,
            threshold_result=threshold,
            cohort=evaluation_inputs.cohort,
            fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
            comparison_fixed_score_evidence=inputs.previous_evidence,
            evidence_role=EvidenceRole.CONFIRMATORY,
            conformal_coverage_inputs=(),
            threshold_estimation_inputs=(),
            communication_messages=(),
            traffic_rate_evidence=None,
            output_directory=_confirmatory_seed_directory(context.coordinate.training_seed)
            / "evaluations"
            / method.value,
            overwrite=False,
        )
    )
    return (
        ConfirmatoryThresholdInputs(
            scores=inputs.scores,
            eligible=inputs.eligible,
            family_by_client=inputs.family_by_client,
            previous_evidence=evaluation_inputs.fixed_score_evidence,
        ),
        bool(evaluation.complete_digest.value),
    )


def _eligible_calibration_scores(
    score_manifest: FederatedScoreArtifactManifest,
) -> tuple[ClientBenignCalibrationScores, ...]:
    invariant = FixedScoreInvariant.from_manifest(score_manifest)
    return tuple(
        ClientBenignCalibrationScores(
            record.scored_client,
            score_manifest.coordinate,
            tuple(
                float(value)
                for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
            ),
            checksum_file(record.path),
            invariant.calibration_score_set_checksum,
        )
        for record in sorted(score_manifest.calibration_records, key=lambda item: item.scored_client)
    )


def _client_training_inputs(
    publications: tuple[ClientPreprocessingResult, ...],
    clients: tuple[ClientIdentity, ...],
    feature_names: FeatureNameSequence,
) -> tuple[ClientTrainingInput, ...]:
    return tuple(
        ClientTrainingInput(
            client=_client_with_id(clients, publication.client_identity.value),
            training_features=pl.read_parquet(publication.paths.train),
            feature_names=feature_names,
            preprocessing_state=publication.fitted_state,
        )
        for publication in publications
    )


def _client_scoring_inputs(
    publications: tuple[ClientPreprocessingResult, ...],
    clients: tuple[ClientIdentity, ...],
) -> tuple[ClientScoringInput, ...]:
    return tuple(
        ClientScoringInput(
            _client_with_id(clients, publication.client_identity.value),
            pl.read_parquet(publication.paths.calibration),
            pl.read_parquet(publication.paths.evaluation),
        )
        for publication in publications
    )


def _family_identities(
    clients: tuple[ClientIdentity, ...],
    family_by_client: tuple[tuple[str, str], ...],
) -> tuple[tuple[ClientIdentity, FamilyIdentity], ...]:
    return tuple(
        (_client_with_id(clients, client_id), FamilyIdentity(family)) for client_id, family in family_by_client
    )


def _client_with_id(clients: tuple[ClientIdentity, ...], client_id: str) -> ClientIdentity:
    client = next((candidate for candidate in clients if candidate.client_id == client_id), None)
    if client is None:
        raise ScientificContractError(f"population manifest is missing client {client_id}")
    return client


def _confirmatory_contrast(training_seed: Seed) -> PairedContrast:
    shared = _load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.SHARED_THRESHOLD))
    local = _load_evaluation_document(_evaluation_path(training_seed, FederatedThresholdMethod.LOCAL_THRESHOLD))
    if shared.score_coordinate != local.score_coordinate:
        raise ScientificContractError("paired evaluation documents use different training coordinates")
    return PairedContrast(
        coordinate=shared.score_coordinate,
        evidence_role=EvidenceRole.CONFIRMATORY,
        metric=MetricId.FPR_COEFFICIENT_OF_VARIATION,
        left_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        right_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        left_value=_population_metric(shared, MetricId.FPR_COEFFICIENT_OF_VARIATION),
        right_value=_population_metric(local, MetricId.FPR_COEFFICIENT_OF_VARIATION),
    )


def _evaluation_path(training_seed: Seed, method: FederatedThresholdMethod) -> Path:
    path = (
        _confirmatory_seed_directory(training_seed)
        / "evaluations"
        / method.value
        / FederatedEvaluationAssetName.DOCUMENT
    )
    if not path.is_file():
        raise ScientificContractError(f"missing completed evaluation document: {path}")
    return path


def _load_evaluation_document(path: Path) -> FederatedEvaluationDocument:
    try:
        return FederatedEvaluationDocument.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError, ValueError) as error:
        raise ScientificContractError(f"completed evaluation document is unreadable or invalid: {path}") from error


def _population_metric(document: FederatedEvaluationDocument, metric: MetricId) -> MetricValue:
    result = metric_by_id(document.population.metrics, metric)
    if result.status is not MetricStatus.AVAILABLE or result.value is None:
        raise ScientificContractError(f"required confirmatory metric is unavailable: {metric.value}")
    return result.value


def _federated_training_directory(coordinate: FederatedTrainingCoordinate) -> Path:
    coefficient = f"{coordinate.model_coefficient.value}" if coordinate.model_coefficient is not None else "unweighted"
    return (
        OUTPUTS_ROOT
        / "federated"
        / coordinate.population.value
        / str(coordinate.training_seed.value)
        / coordinate.split_protocol.value
        / coordinate.preprocessing_identity.value
        / coordinate.model.value
        / coefficient
    )


def _confirmatory_seed_directory(training_seed: Seed) -> Path:
    return OUTPUTS_ROOT / "confirmatory" / PopulationId.NBAIOT_NATURAL_DEVICES.value / str(training_seed.value)


def _campaign_digest(entries: tuple[CampaignEntry, ...]) -> str:
    payload = "\n".join(f"{entry.ordinal}|{entry.coordinate.stable_key}" for entry in entries).encode("utf-8")
    return blake2b(payload, digest_size=32).hexdigest()


# --- Generic ExperimentCoordinate-driven stage runner -----------------------------------
#
# Every stage below is re-derived purely from (ExperimentCoordinate, ExecutionProvenance):
# no state is carried between stage() calls in memory. Each capability call underneath is
# itself idempotent (overwrite=False reuses an already-published, valid artifact instead of
# recomputing it), so re-resolving the same coordinate context at every stage is correct and
# cheap once the expensive work (training) is done, matching the "coordinate-derived paths,
# no hidden execution token" architecture.
#
# Scope: FedAvg and FedProx on any declared (N-BaIoT) or published non-temporal
# (Edge external validation) population. Ditto (separate global+personalized related
# publication) and Edge one-shot temporal states (frozen/recalibrated futures must share one
# detector; see run_temporal_future_pair) are not single-coordinate stage-decomposable and are
# reported BLOCKED with the dedicated entry point to use instead, rather than approximated.

EDGE_FEATURE_NAMES = FeatureNameSequence(tuple(FeatureName(name) for name in EDGE_NUMERIC_FEATURE_COLUMNS))


def _training_autoencoder(dataset: DatasetId) -> AutoencoderProtocol:
    match dataset:
        case DatasetId.NBAIOT:
            return NBAIOT_AUTOENCODER
        case DatasetId.EDGE_IIOTSET:
            return EDGE_IIOTSET_NUMERIC_AUTOENCODER
        case DatasetId.CICIOT2023:
            raise ScientificContractError(
                "no autoencoder architecture is declared for CICIOT2023; training cannot "
                "proceed without a source-backed width sequence",
                subject=dataset,
            )


def _training_feature_names(dataset: DatasetId) -> FeatureNameSequence:
    if dataset is DatasetId.EDGE_IIOTSET:
        return EDGE_FEATURE_NAMES
    return FeatureNameSequence(tuple(FeatureName(name) for name in dataset_binding(dataset).schema.feature_columns))


def _training_protocol_for(coordinate: ExperimentCoordinate) -> FedAvgProtocol | FedProxProtocol:
    match coordinate.training_model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            return FEDAVG_TRAINING_PROTOCOL
        case TrainingModelId.FEDPROX_AUTOENCODER:
            if coordinate.model_coefficient is None:
                raise ScientificContractError(
                    "a FedProx coordinate requires a declared model coefficient",
                    subject=coordinate.training_model,
                )
            matches = tuple(
                protocol
                for protocol in FEDPROX_TRAINING_PROTOCOLS
                if protocol.coefficient.value == coordinate.model_coefficient.value
            )
            if len(matches) != 1:
                raise ScientificContractError(
                    "coordinate model coefficient must resolve to exactly one declared FedProx protocol",
                    subject=coordinate.training_model,
                )
            return matches[0]
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "Ditto's related global/personalized publication is not single-coordinate "
                "stage-decomposable; train it directly via learning.federated.ditto",
                subject=coordinate.training_model,
            )


def _federated_model_coefficient(coordinate: ExperimentCoordinate) -> ProximalCoefficient | DittoRegularization | None:
    match coordinate.training_model:
        case TrainingModelId.FEDAVG_AUTOENCODER:
            return None
        case TrainingModelId.FEDPROX_AUTOENCODER:
            protocol = _training_protocol_for(coordinate)
            if not isinstance(protocol, FedProxProtocol):
                raise ScientificContractError(
                    "a FedProx coordinate must resolve to a FedProxProtocol declaration",
                    subject=coordinate.training_model,
                )
            return protocol.coefficient
        case TrainingModelId.DITTO_GLOBAL_AUTOENCODER | TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            raise ScientificContractError(
                "Ditto's related global/personalized publication is not single-coordinate "
                "stage-decomposable; train it directly via learning.federated.ditto",
                subject=coordinate.training_model,
            )


def _execution_identity_for(coordinate: ExperimentCoordinate) -> ExternalTemporalExecutionIdentity | None:
    if coordinate.population not in BOUNDED_EVIDENCE_POPULATIONS:
        return None
    return ExternalTemporalExecutionIdentity(
        experiment=coordinate.experiment,
        population=coordinate.population,
        evidence_role=coordinate.evidence_role,
        temporal_state=coordinate.temporal_state,
    )


def _resolve_seed_context(coordinate: ExperimentCoordinate) -> PublishedSeedContext:
    """Resolve population, split, and preprocessing for one coordinate, dispatching to the
    declared (N-BaIoT) or published (bounded-evidence) construction path. Re-derivable and
    idempotent: already-published artifacts are reused, not recomputed."""
    training_coordinate = FederatedTrainingCoordinate(
        population=coordinate.population,
        training_seed=coordinate.training_seed,
        split_protocol=coordinate.split_protocol,
        preprocessing_identity=coordinate.preprocessing_protocol,
        model=coordinate.training_model,
        model_coefficient=_federated_model_coefficient(coordinate),
    )
    execution_identity = _execution_identity_for(coordinate)
    identity_kind = resolve_population(coordinate.population).declaration.identity_kind
    if execution_identity is None:
        population_result = construct_declared_population(
            ConstructDeclaredPopulationRequest(
                population=coordinate.population,
                dataset=coordinate.dataset,
                canonical_root=DATA_ROOT / "canonical" / coordinate.dataset.value,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                controlled_condition=None,
            )
        )
        preprocessing = fit_federated_preprocessing(
            FitFederatedPreprocessingRequest(
                population=coordinate.population,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                preprocessing_identity=coordinate.preprocessing_protocol,
                data_root=DATA_ROOT,
                dirichlet_condition=None,
                capture_timestamp_column=None,
            )
        )
        clients = population_result.construction.manifest.clients
        family_by_client = population_result.construction.manifest.family_by_client
        split_manifest_checksum = population_result.split_manifest.assignment_checksum
    else:
        root = _published_seed_directory(execution_identity, coordinate.training_seed)
        population_result = construct_published_population(
            ConstructPublishedPopulationRequest(
                canonical_root=DATA_ROOT / "canonical" / coordinate.dataset.value,
                population=coordinate.population,
                execution_identity=execution_identity,
                partition_seed=coordinate.training_seed,
                split_protocol=coordinate.split_protocol,
                output_directory=root / "population",
                overwrite=False,
            )
        )
        split_result = construct_published_split(
            ConstructPublishedSplitRequest(
                population=coordinate.population,
                execution_identity=execution_identity,
                population_manifest=population_result.population_manifest,
                membership=population_result.membership,
                partition_seed=coordinate.training_seed,
                output_directory=root / "split",
                overwrite=False,
                matched_static_reference_manifest=population_result.matched_static_reference_manifest,
                matched_static_reference_membership=population_result.matched_static_reference_membership,
            )
        )
        preprocessing = fit_published_federated_preprocessing(
            FitPublishedFederatedPreprocessingRequest(
                execution_identity=execution_identity,
                population_directory=root / "population",
                split_directory=root / "split",
                preprocessing_identity=coordinate.preprocessing_protocol,
                data_root=DATA_ROOT,
            )
        )
        clients = population_result.population_manifest.clients
        family_by_client = population_result.population_manifest.family_by_client
        split_manifest_checksum = split_result.manifest.assignment_checksum
    state_set_checksum = preprocessing_state_set_checksum(
        tuple(
            PreparedClientProvenance(
                client=ClientIdentity(coordinate.population, item.client_identity.value, identity_kind),
                preprocessing_checksum=item.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return PublishedSeedContext(
        coordinate=training_coordinate,
        execution_identity=execution_identity,
        clients=clients,
        family_by_client=family_by_client,
        preprocessing=preprocessing,
        state_set_checksum=state_set_checksum,
        split_manifest_checksum=split_manifest_checksum,
        training_directory=_federated_training_directory(training_coordinate),
    )


@dataclass(frozen=True, slots=True)
class GeneralExperimentOutputStore:
    """Reads and deletes the coordinate-derived experiment output directory. Artifacts are
    referenced by path relative to output_root (not copied into the directory), matching the
    reusable-asset rule; only the completion record itself lives in the coordinate directory."""

    def state(self, coordinate: ExperimentCoordinate, output_root: Path) -> ExistingExperimentState:
        directory = experiment_output_directory(output_root, coordinate)
        if not directory.is_dir():
            return ExistingExperimentState.ABSENT
        record = read_completion_record(directory)
        if record is None or record.state is not CompletionState.COMPLETE:
            return ExistingExperimentState.INCOMPLETE
        observed = _observed_artifacts(output_root, record.artifacts)
        validation = validate_reload(root=output_root, completion=record, observed=observed)
        return ExistingExperimentState.COMPLETE_VALID if validation.valid else ExistingExperimentState.COMPLETE_INVALID

    def delete(self, coordinate: ExperimentCoordinate, output_root: Path) -> None:
        directory = experiment_output_directory(output_root, coordinate)
        if directory.exists():
            rmtree(directory)


def _observed_artifacts(output_root: Path, declared: tuple[ArtifactRecord, ...]) -> tuple[ArtifactRecord, ...]:
    observed: list[ArtifactRecord] = []
    for item in declared:
        path = output_root / item.relative_path
        if not path.is_file():
            continue
        observed.append(
            ArtifactRecord(
                kind=item.kind,
                relative_path=item.relative_path,
                checksum=checksum_file(path),
                byte_count=ByteCount(path.stat().st_size),
                state=ArtifactState.PUBLISHED,
            )
        )
    return tuple(observed)


@dataclass(frozen=True, slots=True)
class GeneralStageRunner:
    """Concrete StageRunner resolving every canonical pipeline stage from
    (ExperimentCoordinate, ExecutionProvenance) alone. See module note above for scope."""

    def run(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
    ) -> StageExecution:
        try:
            return self._dispatch(stage, coordinate, provenance)
        except ScientificContractError as error:
            return StageExecution(stage=stage, outcome=StageOutcome.BLOCKED, evidence=str(error))

    def _dispatch(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
    ) -> StageExecution:
        if coordinate.temporal_state is not None:
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.BLOCKED,
                evidence=(
                    "temporal coordinates require the shared frozen/recalibrated-future detector "
                    "run via pipeline.campaign.run_temporal_future_pair, not single-coordinate stages"
                ),
            )
        if stage is PipelineStage.PREFLIGHT:
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.COMPLETED,
                evidence=f"coordinate validated: {coordinate.stable_key}",
            )
        if stage is PipelineStage.PUBLISH_REPORT:
            raise ScientificContractError(
                "PUBLISH_REPORT is a campaign-level report aggregation, not a per-coordinate stage; "
                "no execution recipe includes it",
                subject=coordinate.experiment,
            )
        if stage is PipelineStage.FINALIZE_PUBLICATION:
            return self._finalize_publication(stage, coordinate, provenance)
        handler = self._COORDINATE_STAGE_HANDLERS.get(stage)
        if handler is None:
            raise ScientificContractError(
                f"no coordinate-stage handler is declared for {stage.value}", subject=coordinate.experiment
            )
        return handler(self, stage, coordinate)

    def _construct_population(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        context = _resolve_seed_context(coordinate)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"clients={len(context.clients)} split_checksum={context.split_manifest_checksum.value}",
        )

    def _fit_preprocessing(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        context = _resolve_seed_context(coordinate)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"state_set={context.state_set_checksum.value}",
        )

    def _materialize_dataset(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        result = materialize_dataset(MaterializeDatasetRequest(data_root=DATA_ROOT, datasets=(coordinate.dataset,)))
        publication = result.publications[0]
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"{publication.dataset.value} status={publication.publication_status.value}",
        )

    def _train_detector(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        autoencoder = _training_autoencoder(coordinate.dataset)
        feature_names = _training_feature_names(coordinate.dataset)
        training_protocol = _training_protocol_for(coordinate)
        context = _resolve_seed_context(coordinate)
        result = train_federated_detector(
            TrainFederatedDetectorRequest(
                request=FederatedTrainingRequest(
                    coordinate=context.coordinate,
                    clients=_client_training_inputs(
                        context.preprocessing.client_publications, context.clients, feature_names
                    ),
                    population_client_count=ClientCount(len(context.clients)),
                    autoencoder=autoencoder,
                    training_protocol=training_protocol,
                    checkpoint_protocol=CHECKPOINT_PROTOCOL,
                    training_seed=context.coordinate.training_seed,
                    batch_size=BATCH_SIZE,
                    learning_rate=LEARNING_RATE,
                    split_manifest_checksum=context.split_manifest_checksum,
                    output_directory=context.training_directory,
                ),
                overwrite=False,
            )
        )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED if result.publication_status.value == "published" else StageOutcome.REUSED,
            evidence=f"rounds={len(result.candidates)} status={result.publication_status.value}",
        )

    def _select_checkpoint(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        autoencoder = _training_autoencoder(coordinate.dataset)
        feature_names = _training_feature_names(coordinate.dataset)
        training_protocol = _training_protocol_for(coordinate)
        context = _resolve_seed_context(coordinate)
        training = train_federated_detector(
            TrainFederatedDetectorRequest(
                request=FederatedTrainingRequest(
                    coordinate=context.coordinate,
                    clients=_client_training_inputs(
                        context.preprocessing.client_publications,
                        context.clients,
                        feature_names,
                    ),
                    population_client_count=ClientCount(len(context.clients)),
                    autoencoder=autoencoder,
                    training_protocol=training_protocol,
                    checkpoint_protocol=CHECKPOINT_PROTOCOL,
                    training_seed=context.coordinate.training_seed,
                    batch_size=BATCH_SIZE,
                    learning_rate=LEARNING_RATE,
                    split_manifest_checksum=context.split_manifest_checksum,
                    output_directory=context.training_directory,
                ),
                overwrite=False,
            )
        )
        selection = select_federated_primary_checkpoint(
            SelectFederatedCheckpointRequest(
                coordinate=context.coordinate,
                client=None,
                candidates=training.candidates,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                preprocessing_state_set_checksum=context.state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                held_out_metrics=None,
                attack_labels_present=False,
            )
        )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"selected_round={selection.decision.selected.round_number.value}",
        )

    def _generate_scores(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        scores = self._score(coordinate)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"calibration={len(scores.calibration_records)} evaluation={len(scores.evaluation_records)}",
        )

    def _score(self, coordinate: ExperimentCoordinate) -> FederatedScoreArtifactManifest:
        training_protocol = _training_protocol_for(coordinate)
        autoencoder = _training_autoencoder(coordinate.dataset)
        feature_names = _training_feature_names(coordinate.dataset)
        context = _resolve_seed_context(coordinate)
        training = train_federated_detector(
            TrainFederatedDetectorRequest(
                request=FederatedTrainingRequest(
                    coordinate=context.coordinate,
                    clients=_client_training_inputs(
                        context.preprocessing.client_publications, context.clients, feature_names
                    ),
                    population_client_count=ClientCount(len(context.clients)),
                    autoencoder=autoencoder,
                    training_protocol=training_protocol,
                    checkpoint_protocol=CHECKPOINT_PROTOCOL,
                    training_seed=context.coordinate.training_seed,
                    batch_size=BATCH_SIZE,
                    learning_rate=LEARNING_RATE,
                    split_manifest_checksum=context.split_manifest_checksum,
                    output_directory=context.training_directory,
                ),
                overwrite=False,
            )
        )
        selected = select_federated_primary_checkpoint(
            SelectFederatedCheckpointRequest(
                coordinate=context.coordinate,
                client=None,
                candidates=training.candidates,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                preprocessing_state_set_checksum=context.state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                held_out_metrics=None,
                attack_labels_present=False,
            )
        ).decision.selected
        return generate_federated_scores(
            GenerateFederatedScoresRequest(
                checkpoint=selected,
                autoencoder=autoencoder,
                feature_names=feature_names,
                clients=_client_scoring_inputs(context.preprocessing.client_publications, context.clients),
                batch_size=BATCH_SIZE,
                output_directory=context.training_directory / "scores",
                preprocessing_state_set_checksum=context.state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                overwrite=False,
            )
        ).result.manifest

    def _build_calibration(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        scores = self._score(coordinate)
        eligible = _eligible_calibration_scores(scores)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"eligible_clients={len(eligible)}",
        )

    def _construct_thresholds(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        scores = self._score(coordinate)
        eligible = _eligible_calibration_scores(scores)
        family_by_client = _family_identities(
            _resolve_seed_context(coordinate).clients,
            _resolve_seed_context(coordinate).family_by_client,
        )
        threshold = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    coordinate.threshold_method,
                    scores.coordinate,
                    CANONICAL_QUANTILE,
                    population_capabilities(coordinate.population),
                    eligible,
                    family_by_client,
                ),
                output_directory=experiment_output_directory(OUTPUTS_ROOT, coordinate) / "threshold",
                overwrite=False,
            )
        ).result
        if isinstance(threshold, ThresholdUnavailableResult):
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.BLOCKED,
                evidence=f"threshold unavailable: {threshold.reason.value}",
            )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"method={coordinate.threshold_method.value}",
        )

    def _evaluate_detector(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        scores = self._score(coordinate)
        eligible = _eligible_calibration_scores(scores)
        context = _resolve_seed_context(coordinate)
        family_by_client = _family_identities(context.clients, context.family_by_client)
        threshold_result = construct_federated_thresholds(
            ConstructFederatedThresholdsRequest(
                request=ThresholdConstructionRequest(
                    coordinate.threshold_method,
                    scores.coordinate,
                    CANONICAL_QUANTILE,
                    population_capabilities(coordinate.population),
                    eligible,
                    family_by_client,
                ),
                output_directory=experiment_output_directory(OUTPUTS_ROOT, coordinate) / "threshold",
                overwrite=False,
            )
        ).result
        if isinstance(threshold_result, ThresholdUnavailableResult):
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.BLOCKED,
                evidence=f"threshold unavailable: {threshold_result.reason.value}",
            )
        evaluation_inputs = build_federated_evaluation_inputs(scores, coordinate.threshold_method)
        evaluation = evaluate_federated_detector(
            EvaluateFederatedDetectorRequest(
                score_manifest=scores,
                threshold_result=threshold_result,
                cohort=evaluation_inputs.cohort,
                fixed_score_evidence=evaluation_inputs.fixed_score_evidence,
                comparison_fixed_score_evidence=None,
                evidence_role=coordinate.evidence_role,
                conformal_coverage_inputs=(),
                threshold_estimation_inputs=(),
                communication_messages=(),
                traffic_rate_evidence=None,
                execution_identity=context.execution_identity,
                output_directory=experiment_output_directory(OUTPUTS_ROOT, coordinate) / "evaluation",
                overwrite=False,
            )
        )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"complete_digest={evaluation.complete_digest.value}",
        )

    def _analyze_evidence(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        result = metric_by_id(
            self._reload_evaluation(coordinate).population.metrics,
            coordinate.metric,
        )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"metric={coordinate.metric.value} status={result.status.value}",
        )

    def _reload_evaluation(self, coordinate: ExperimentCoordinate) -> FederatedEvaluationDocument:
        directory = experiment_output_directory(OUTPUTS_ROOT, coordinate)
        return _load_evaluation_document(directory / "evaluation" / FederatedEvaluationAssetName.DOCUMENT)

    def _verify_anchor(self, stage: PipelineStage, coordinate: ExperimentCoordinate) -> StageExecution:
        if coordinate.experiment is not ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            raise ScientificContractError(
                "the anchor gate applies only to the historical reproduction experiment",
                subject=coordinate.experiment,
            )
        result = verify_anchor(
            VerifyAnchorStageRequest(
                protocol=ANCHOR_DECISION_PROTOCOL,
                diagnostics_directory=experiment_output_directory(OUTPUTS_ROOT, coordinate) / "anchor",
                observations=None,
                historical_sources=None,
                request_independent_reproduction=False,
            )
        )
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"gate={result.status.gate_status.value} readiness={result.status.dependent_readiness.value}",
        )

    def _finalize_publication(
        self,
        stage: PipelineStage,
        coordinate: ExperimentCoordinate,
        provenance: ExecutionProvenance,
    ) -> StageExecution:
        autoencoder = _training_autoencoder(coordinate.dataset)
        feature_names = _training_feature_names(coordinate.dataset)
        training_protocol = _training_protocol_for(coordinate)
        context = _resolve_seed_context(coordinate)
        selection = select_federated_primary_checkpoint(
            SelectFederatedCheckpointRequest(
                coordinate=context.coordinate,
                client=None,
                candidates=train_federated_detector(
                    TrainFederatedDetectorRequest(
                        request=FederatedTrainingRequest(
                            coordinate=context.coordinate,
                            clients=_client_training_inputs(
                                context.preprocessing.client_publications,
                                context.clients,
                                feature_names,
                            ),
                            population_client_count=ClientCount(len(context.clients)),
                            autoencoder=autoencoder,
                            training_protocol=training_protocol,
                            checkpoint_protocol=CHECKPOINT_PROTOCOL,
                            training_seed=context.coordinate.training_seed,
                            batch_size=BATCH_SIZE,
                            learning_rate=LEARNING_RATE,
                            split_manifest_checksum=context.split_manifest_checksum,
                            output_directory=context.training_directory,
                        ),
                        overwrite=False,
                    )
                ).candidates,
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                preprocessing_state_set_checksum=context.state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                held_out_metrics=None,
                attack_labels_present=False,
            )
        ).decision.selected
        evaluation_document_path = (
            experiment_output_directory(OUTPUTS_ROOT, coordinate) / "evaluation" / FederatedEvaluationAssetName.DOCUMENT
        )
        if not evaluation_document_path.is_file():
            return StageExecution(
                stage=stage,
                outcome=StageOutcome.BLOCKED,
                evidence="finalize requires a completed evaluation document",
            )
        artifacts = (
            ArtifactRecord(
                kind=ArtifactKind.MODEL_TENSORS,
                relative_path=selection.tensor_path.relative_to(OUTPUTS_ROOT),
                checksum=selection.tensor_checksum,
                byte_count=ByteCount(selection.tensor_path.stat().st_size),
                state=ArtifactState.PUBLISHED,
            ),
            ArtifactRecord(
                kind=ArtifactKind.MANIFEST,
                relative_path=evaluation_document_path.relative_to(OUTPUTS_ROOT),
                checksum=checksum_file(evaluation_document_path),
                byte_count=ByteCount(evaluation_document_path.stat().st_size),
                state=ArtifactState.PUBLISHED,
            ),
        )
        record = build_completion_record(
            plan_digest=provenance.plan_digest,
            campaign_digest=provenance.campaign_digest,
            artifacts=artifacts,
        )
        directory = experiment_output_directory(OUTPUTS_ROOT, coordinate)
        write_completion_record(directory, record)
        return StageExecution(
            stage=stage,
            outcome=StageOutcome.COMPLETED,
            evidence=f"completion_state={record.state.value} artifacts={len(record.artifacts)}",
        )

    _COORDINATE_STAGE_HANDLERS: ClassVar[
        dict[PipelineStage, Callable[[GeneralStageRunner, PipelineStage, ExperimentCoordinate], StageExecution]]
    ] = {
        PipelineStage.MATERIALIZE_DATASET: _materialize_dataset,
        PipelineStage.CONSTRUCT_POPULATION: _construct_population,
        PipelineStage.FIT_PREPROCESSING: _fit_preprocessing,
        PipelineStage.TRAIN_DETECTOR: _train_detector,
        PipelineStage.SELECT_CHECKPOINT: _select_checkpoint,
        PipelineStage.GENERATE_SCORES: _generate_scores,
        PipelineStage.BUILD_CALIBRATION: _build_calibration,
        PipelineStage.CONSTRUCT_THRESHOLDS: _construct_thresholds,
        PipelineStage.EVALUATE_DETECTOR: _evaluate_detector,
        PipelineStage.ANALYZE_EVIDENCE: _analyze_evidence,
        PipelineStage.VERIFY_ANCHOR: _verify_anchor,
    }
