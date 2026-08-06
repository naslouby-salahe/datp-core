"""Ditto personalized-model threshold-scope stress execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.analysis.mechanisms import (
    AbsorptionCohortResult,
    AbsorptionSeedObservation,
    decide_absorption_cohort,
    decide_model_absorption,
)
from datp_core.datasets.partitioning.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.datasets.registry import population_capabilities
from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import (
    ContractSubject,
    DatasetId,
    EvaluationCohort,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ScoreFrameColumn,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum, checksum_file
from datp_core.domain.values.counts import ClientCount, Seed
from datp_core.domain.values.identifiers import FeatureNameSequence
from datp_core.domain.values.ratios import DittoRegularization, MetricValue, ScoreValue
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.cohort.construction import build_evaluation_cohort_manifest
from datp_core.evaluation.cohort.evidence import client_partition_counts_from_scores
from datp_core.evaluation.confusion import calculate_confusion_counts
from datp_core.evaluation.fixed_score.checksums import evaluation_label_checksum, source_row_checksum
from datp_core.evaluation.models import ClientMetricResult, MetricStatus, metric_by_id
from datp_core.learning.federated.ditto import DittoTrainingRequest
from datp_core.learning.federated.models import (
    DittoTrainingCoordinates,
    FederatedTrainingCoordinate,
    PreparedClientProvenance,
)
from datp_core.learning.federated.training import preprocessing_state_set_checksum
from datp_core.pipeline.checkpoints.service import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
from datp_core.pipeline.decision.federated import ConstructFederatedThresholdsRequest, construct_federated_thresholds
from datp_core.pipeline.execution.context import (
    client_training_inputs,
    client_with_id,
    family_identities,
    training_feature_names,
)
from datp_core.pipeline.execution.layout import ExecutionArtifactDirectory, ExecutionRootDirectory
from datp_core.pipeline.preparation.populations import ConstructDeclaredPopulationRequest, construct_declared_population
from datp_core.pipeline.scoring.federated import publish_federated_scores
from datp_core.pipeline.scoring.models import (
    ClientScoringInput,
    FederatedScoreArtifactManifest,
    FederatedScoreRecord,
    GenerateFederatedScoresRequest,
)
from datp_core.pipeline.training.personalized import (
    TrainDittoDetectorRequest,
    TrainDittoDetectorResult,
    train_ditto_detector,
)
from datp_core.preprocessing.models import (
    ClientPreprocessingResult,
    FederatedPreprocessingOutcome,
    FederatedPreprocessingRequest,
)
from datp_core.preprocessing.service import preprocess_federated
from datp_core.protocols.calibration import CANONICAL_QUANTILE
from datp_core.protocols.inference import FixedScoreInvariant
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    LEARNING_RATE,
    MODEL_ABSORPTION_DECISION_PROTOCOL,
    NBAIOT_AUTOENCODER,
    resolve_ditto_protocol,
)
from datp_core.reporting.export import export_mechanism_publication
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT
from datp_core.thresholding.assignments import FamilyAssignment, ThresholdAssignment
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.methods.local import LocalThresholdResult
from datp_core.thresholding.methods.shared import SharedThresholdResult
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores


class DittoArtifactBranch(StrEnum):
    GLOBAL_MODEL = "global_model"
    PERSONALIZED_MODELS = "personalized_models"
    THRESHOLDS = "thresholds"


@dataclass(frozen=True, slots=True, kw_only=True)
class DittoStressTestResult:
    personalized_coordinate: FederatedTrainingCoordinate
    shared_threshold: SharedThresholdResult
    local_threshold: LocalThresholdResult
    shared_threshold_metrics: tuple[ClientMetricResult, ...]
    local_threshold_metrics: tuple[ClientMetricResult, ...]


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


def run_ditto_stress_test_seed(*, training_seed: Seed, regularization: DittoRegularization) -> DittoStressTestResult:
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
                    context.preprocessing.client_publications, context.clients, feature_names
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
                    training_seed, regularization, DittoArtifactBranch.GLOBAL_MODEL
                ),
                personalized_output_directory=ditto_directory(
                    training_seed,
                    regularization,
                    DittoArtifactBranch.PERSONALIZED_MODELS,
                ),
            ),
            overwrite=False,
        )
    )
    scores = _personalized_scores(
        training=training,
        personalized_coordinate=personalized_coordinate,
        context=context,
        feature_names=feature_names,
        training_seed=training_seed,
        regularization=regularization,
    )
    capabilities = population_capabilities(population)
    threshold_directory = ditto_directory(training_seed, regularization, DittoArtifactBranch.THRESHOLDS)
    shared = construct_federated_thresholds(
        ConstructFederatedThresholdsRequest(
            request=ThresholdConstructionRequest(
                method=FederatedThresholdMethod.SHARED_THRESHOLD,
                coordinate=personalized_coordinate,
                quantile=CANONICAL_QUANTILE,
                capabilities=capabilities,
                eligible=scores.eligible_calibration,
                family_by_client=context.family_by_client,
            ),
            output_directory=threshold_directory / FederatedThresholdMethod.SHARED_THRESHOLD.value,
            overwrite=False,
        )
    ).result
    local = construct_federated_thresholds(
        ConstructFederatedThresholdsRequest(
            request=ThresholdConstructionRequest(
                method=FederatedThresholdMethod.LOCAL_THRESHOLD,
                coordinate=personalized_coordinate,
                quantile=CANONICAL_QUANTILE,
                capabilities=capabilities,
                eligible=scores.eligible_calibration,
                family_by_client=context.family_by_client,
            ),
            output_directory=threshold_directory / FederatedThresholdMethod.LOCAL_THRESHOLD.value,
            overwrite=False,
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
    return DittoStressTestResult(
        personalized_coordinate=personalized_coordinate,
        shared_threshold=shared,
        local_threshold=local,
        shared_threshold_metrics=tuple(
            _client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.SHARED_THRESHOLD,
                population,
                scores.manifests.require(assignment.client),
                assignment,
            )
            for assignment in shared.assignments
        ),
        local_threshold_metrics=tuple(
            _client_metric(
                personalized_coordinate,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
                population,
                scores.manifests.require(assignment.client),
                assignment,
            )
            for assignment in local.assignments
        ),
    )


def analyze_ditto_absorption(
    results: tuple[DittoStressTestResult, ...],
    *,
    reference_effects: tuple[MetricValue, ...],
    output_directory: Path,
) -> AbsorptionCohortResult:
    """Cohort-level absorption analysis for completed Ditto stress-test seeds."""
    if len(results) != len(reference_effects):
        raise ScientificContractError("absorption analysis requires one reference effect per Ditto seed result")
    observations = tuple(
        AbsorptionSeedObservation(
            seed=result.personalized_coordinate.training_seed,
            experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
            reference_model=TrainingModelId.FEDAVG_AUTOENCODER,
            personalized_model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
            reference_effect=reference,
            personalized_effect=_population_cv_effect(result),
        )
        for result, reference in zip(results, reference_effects, strict=True)
    )
    # Keep single-seed diagnostic path reachable from production.
    if observations:
        decide_model_absorption(
            observations[0].reference_effect,
            observations[0].personalized_effect,
            MODEL_ABSORPTION_DECISION_PROTOCOL,
        )
    cohort = decide_absorption_cohort(observations, MODEL_ABSORPTION_DECISION_PROTOCOL)
    export_mechanism_publication(
        (cohort,),
        experiment=ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        output_directory=output_directory,
    )
    return cohort


def _population_cv_effect(result: DittoStressTestResult) -> MetricValue:
    shared_values = _available_fpr_values(result.shared_threshold_metrics)
    local_values = _available_fpr_values(result.local_threshold_metrics)
    if not shared_values or not local_values or len(shared_values) != len(local_values):
        raise ScientificContractError("Ditto absorption requires available paired client FPR values")
    shared_mean = sum(shared_values) / len(shared_values)
    local_mean = sum(local_values) / len(local_values)
    return MetricValue(shared_mean - local_mean)


def _available_fpr_values(metrics: tuple[ClientMetricResult, ...]) -> tuple[float, ...]:
    values: list[float] = []
    for item in metrics:
        outcome = metric_by_id(item.metrics, MetricId.FALSE_POSITIVE_RATE)
        if outcome.status is MetricStatus.AVAILABLE and outcome.value is not None:
            values.append(outcome.value.value)
    return tuple(values)


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
                client=client_with_id(clients, item.client_identity.value),
                preprocessing_checksum=item.fitted_state.estimator_checksum,
            )
            for item in preprocessing.client_publications
        )
    )
    return DittoPopulationContext(
        clients=clients,
        family_by_client=family_identities(clients, population_result.construction.manifest.family_by_client),
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
) -> PersonalizedScoreCollection:
    eligible: list[ClientBenignCalibrationScores] = []
    manifests: list[ClientOwned[ClientIdentity, FederatedScoreArtifactManifest]] = []
    personalized_directory = ditto_directory(training_seed, regularization, DittoArtifactBranch.PERSONALIZED_MODELS)
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
                autoencoder=NBAIOT_AUTOENCODER,
                feature_names=feature_names,
                clients=(_client_scoring_input(context.preprocessing.client_publications, client),),
                batch_size=BATCH_SIZE,
                output_directory=personalized_directory / client.client_id / ExecutionArtifactDirectory.SCORES,
                preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
                split_manifest_checksum=context.split_manifest_checksum,
                overwrite=False,
            )
        ).manifest
        manifests.append(ClientOwned(client=client, value=manifest))
        invariant = FixedScoreInvariant.from_manifest(manifest)
        record = _score_record_for_client(manifest.calibration_records, client, PartitionRole.CALIBRATION)
        eligible.append(
            ClientBenignCalibrationScores(
                client,
                personalized_coordinate,
                tuple(
                    ScoreValue(float(value))
                    for value in pl.read_parquet(record.path)[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
                ),
                checksum_file(record.path),
                invariant.calibration_score_set_checksum,
            )
        )
    return PersonalizedScoreCollection(
        eligible_calibration=tuple(eligible),
        manifests=ClientCollection(items=tuple(manifests)),
    )


def _client_scoring_input(
    publications: tuple[ClientPreprocessingResult, ...],
    client: ClientIdentity,
) -> ClientScoringInput:
    matches = tuple(item for item in publications if item.client_identity.value == client.client_id)
    if len(matches) != 1:
        raise ScientificContractError(f"expected one preprocessing publication for {client.client_id}")
    publication = matches[0]
    return ClientScoringInput(
        client=client,
        calibration_features=pl.read_parquet(publication.paths.calibration),
        evaluation_features=pl.read_parquet(publication.paths.evaluation),
    )


def _client_metric(
    coordinate: FederatedTrainingCoordinate,
    threshold_method: FederatedThresholdMethod,
    population: PopulationId,
    manifest: FederatedScoreArtifactManifest,
    assignment: ThresholdAssignment,
) -> ClientMetricResult:
    record = _score_record_for_client(manifest.evaluation_records, assignment.client, PartitionRole.EVALUATION)
    frame = pl.read_parquet(record.path)
    error_values = frame[ScoreFrameColumn.RECONSTRUCTION_ERROR.value].to_list()
    outcome_values = frame[ScoreFrameColumn.OUTCOME_LABEL.value].to_list()
    scores = tuple(ScoreValue(float(value)) for value in error_values)
    labels = tuple(PopulationOutcomeLabel(str(value)) for value in outcome_values)
    rows = tuple(str(value) for value in frame[ScoreFrameColumn.STABLE_ROW_ID.value].to_list())
    cohort_manifest = build_evaluation_cohort_manifest(
        population=population,
        partition_seed=coordinate.training_seed,
        client_counts=client_partition_counts_from_scores(manifest),
    )
    eligibility_matches = tuple(item for item in cohort_manifest.records if item.client == assignment.client)
    if len(eligibility_matches) != 1:
        raise ScientificContractError(
            f"expected one evaluation-cohort record for {assignment.client.client_id}",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    eligibility = eligibility_matches[0]
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


def _score_record_for_client(
    records: tuple[FederatedScoreRecord, ...],
    client: ClientIdentity,
    role: PartitionRole,
) -> FederatedScoreRecord:
    matches = tuple(item for item in records if item.scored_client == client)
    if len(matches) != 1:
        raise ScientificContractError(
            f"expected one {role.value} score record for {client.client_id}",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    return matches[0]


def ditto_directory(
    training_seed: Seed,
    regularization: DittoRegularization,
    branch: DittoArtifactBranch,
) -> Path:
    return (
        OUTPUTS_ROOT
        / ExecutionRootDirectory.DITTO_STRESS_TEST
        / PopulationId.NBAIOT_NATURAL_DEVICES.value
        / str(training_seed.value)
        / str(regularization.value)
        / branch.value
    )
