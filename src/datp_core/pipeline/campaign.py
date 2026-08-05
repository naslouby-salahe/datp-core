"""Deterministic campaigns and the canonical confirmatory execution workflow."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path

import polars as pl
from pydantic import ValidationError

from datp_core.analysis.contrasts import PairedContrast
from datp_core.datasets.catalogue import dataset_binding
from datp_core.domain.enums import (
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    ScoreFrameColumn,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import (
    Checksum,
    ClientCount,
    FamilyIdentity,
    FeatureName,
    FeatureNameSequence,
    MetricValue,
    Seed,
    checksum_file,
)
from datp_core.evaluation.controls import FixedScoreEvidence, build_federated_evaluation_inputs
from datp_core.evaluation.models import MetricStatus, metric_by_id
from datp_core.evaluation.population import FederatedEvaluationAssetName, FederatedEvaluationDocument
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
    construct_declared_population,
)
from datp_core.pipeline.construct_thresholds import (
    ConstructFederatedThresholdsRequest,
    construct_federated_thresholds,
)
from datp_core.pipeline.evaluate_detector import (
    EvaluateFederatedDetectorRequest,
    evaluate_federated_detector,
)
from datp_core.pipeline.execution import (
    ExperimentExecution,
    ExperimentOutputStore,
    StageRunner,
    execute_experiment,
)
from datp_core.pipeline.fit_preprocessing import (
    FitFederatedPreprocessingRequest,
    FitFederatedPreprocessingResult,
    fit_federated_preprocessing,
)
from datp_core.pipeline.generate_scores import GenerateFederatedScoresRequest, generate_federated_scores
from datp_core.pipeline.planning import ExperimentCoordinate, ExperimentPlan, PlanDisposition
from datp_core.pipeline.select_checkpoint import (
    SelectFederatedCheckpointRequest,
    select_federated_primary_checkpoint,
)
from datp_core.pipeline.train_detector import TrainFederatedDetectorRequest, train_federated_detector
from datp_core.populations.capabilities import population_capabilities
from datp_core.populations.catalogue import resolve_population
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import ClientPreprocessingResult
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.runtime import DATA_ROOT, OUTPUTS_ROOT
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.statistics import CONFIRMATORY_INFERENCE_PROTOCOL
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    FEDAVG_TRAINING_PROTOCOL,
    LEARNING_RATE,
    NBAIOT_AUTOENCODER,
)
from datp_core.pipeline.scoring.service import ClientScoringInput
from datp_core.protocols.inference import FixedScoreInvariant, ScoreArtifactManifest
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.identities import ThresholdUnavailableResult
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
    scores: ScoreArtifactManifest
    eligible: tuple[ClientBenignCalibrationScores, ...]
    family_by_client: tuple[tuple[ClientIdentity, FamilyIdentity], ...]
    previous_evidence: FixedScoreEvidence | None


def build_campaign(plan: ExperimentPlan) -> CampaignPlan:
    coordinates = tuple(
        entry.coordinate for entry in plan.entries if entry.disposition is PlanDisposition.EXECUTABLE
    )
    entries = tuple(CampaignEntry(ordinal=index, coordinate=coordinate) for index, coordinate in enumerate(coordinates))
    return CampaignPlan(entries=entries, digest=_campaign_digest(entries))


def execute_campaign(
    *,
    campaign: CampaignPlan,
    stage_runner: StageRunner,
    output_store: ExperimentOutputStore,
    output_root: Path,
) -> CampaignExecution:
    experiments = tuple(
        execute_experiment(
            coordinate=entry.coordinate,
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


def _score_confirmatory_seed(context: ConfirmatorySeedContext) -> ScoreArtifactManifest:
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
    score_manifest: ScoreArtifactManifest,
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
        (_client_with_id(clients, client_id), FamilyIdentity(family))
        for client_id, family in family_by_client
    )


def _client_with_id(clients: tuple[ClientIdentity, ...], client_id: str) -> ClientIdentity:
    client = next((candidate for candidate in clients if candidate.client_id == client_id), None)
    if client is None:
        raise ScientificContractError(f"population manifest is missing client {client_id}")
    return client


def _confirmatory_contrast(training_seed: Seed) -> PairedContrast:
    shared = _load_evaluation_document(
        _evaluation_path(training_seed, FederatedThresholdMethod.SHARED_THRESHOLD)
    )
    local = _load_evaluation_document(
        _evaluation_path(training_seed, FederatedThresholdMethod.LOCAL_THRESHOLD)
    )
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
    return (
        OUTPUTS_ROOT
        / "federated"
        / coordinate.population.value
        / str(coordinate.training_seed.value)
        / coordinate.split_protocol.value
        / coordinate.preprocessing_identity.value
        / coordinate.model.value
    )


def _confirmatory_seed_directory(training_seed: Seed) -> Path:
    return OUTPUTS_ROOT / "confirmatory" / PopulationId.NBAIOT_NATURAL_DEVICES.value / str(training_seed.value)


def _campaign_digest(entries: tuple[CampaignEntry, ...]) -> str:
    payload = "\n".join(f"{entry.ordinal}|{entry.coordinate.stable_key}" for entry in entries).encode("utf-8")
    return blake2b(payload, digest_size=32).hexdigest()
