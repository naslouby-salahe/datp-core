"""Privacy-incompatible centralized reference execution and report consumption.

The centralized reference is a pooled-data autoencoder baseline with a pooled benign quantile
threshold. It provides context for the cost of federation and is never part of the
federated threshold-scope causal ladder. Every scope uses its own pooled
preprocessing, model, and scores; federated state is never reused.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.analysis.metrics.models import AvailableMetric, MetricStatus, metric_by_id
from datp_core.artifacts.serializers.json import canonical_checksum, canonical_json_text
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ReportEvidenceError
from datp_core.core.identifiers import (
    AvailabilityStatus,
    CentralizedModelId,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
)
from datp_core.core.numeric import Seed
from datp_core.data.populations.publication import ConstructDeclaredPopulationRequest, construct_declared_population
from datp_core.data.preprocessing.centralized import (
    CentralizedPopulationPreprocessingRequest,
    preprocess_centralized_population,
)
from datp_core.detector.checkpoints.protocols import CHECKPOINT_PROTOCOL
from datp_core.detector.checkpoints.service import (
    SelectCentralizedCheckpointRequest,
    select_centralized_primary_checkpoint,
)
from datp_core.detector.scoring.centralized import generate_centralized_scores
from datp_core.detector.scoring.models import GenerateCentralizedScoresRequest
from datp_core.detector.training.centralized import CentralizedTrainingCoordinate
from datp_core.detector.training.centralized_publication import (
    TrainCentralizedDetectorRequest,
    train_centralized_detector,
)
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.protocols import BATCH_SIZE, CICIOT2023_AUTOENCODER, NBAIOT_AUTOENCODER
from datp_core.experiments.common.seeds import (
    BOUNDED_EVIDENCE_SEED_COHORT,
    CONFIRMATORY_SEED_COHORT,
    SeedCohort,
)
from datp_core.experiments.execution.context import training_feature_names
from datp_core.experiments.execution.layout import ExecutionArtifactDirectory
from datp_core.presentation.export import PUBLICATION_FILENAME, PublicationBundle, ReportProvenance, export_markdown
from datp_core.presentation.tables import PublicationTable, TableCell
from datp_core.presentation.validation import ClaimKind, ClaimRequest, EvidenceDecision, validate_claim
from datp_core.runtime.configuration import DATA_ROOT, OUTPUTS_ROOT
from datp_core.runtime.filesystem import write_text_atomically
from datp_core.thresholds.centralized import (
    CENTRALIZED_POOLED_METRICS,
    CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
    CentralizedEvaluationDocument,
    CentralizedEvaluationPublicationAsset,
    ConstructCentralizedThresholdRequest,
    EvaluateCentralizedDetectorRequest,
    EvaluateCentralizedDetectorResult,
    construct_centralized_threshold,
    evaluate_centralized_detector,
)


class CentralizedReferenceArtifactDirectory(StrEnum):
    ROOT = "centralized_reference"
    TRAINING = "training"
    SCORES = "scores"
    THRESHOLD = "threshold"
    EVALUATION = "evaluation"


class CentralizedReferenceReportAsset(StrEnum):
    DIRECTORY = "report"
    MANIFEST = "centralized_reference_manifest.json"
    PUBLICATION = PUBLICATION_FILENAME
    COMPLETE = "COMPLETE"


class CentralizedReferenceReportManifest(StrictModel):
    population: PopulationId
    evaluations: tuple[CentralizedEvaluationDocument, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedReferenceScope:
    population: PopulationId
    dataset: DatasetId
    autoencoder: AutoencoderProtocol
    seed_cohort: SeedCohort
    provenance_experiment: ExperimentId
    claim_wording: str #TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists


NBAIOT_CENTRALIZED_REFERENCE = CentralizedReferenceScope(
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    dataset=DatasetId.NBAIOT,
    autoencoder=NBAIOT_AUTOENCODER,
    seed_cohort=CONFIRMATORY_SEED_COHORT,
    provenance_experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
    claim_wording=(
        "The privacy-incompatible centralized reference is independent pooled context "
        "for the cost of federation and is not part of the federated threshold-scope "
        "causal ladder."
    ),
)

CIC_CENTRALIZED_REFERENCE = CentralizedReferenceScope(
    population=PopulationId.CICIOT_FILE_CLIENTS,
    dataset=DatasetId.CICIOT2023,
    autoencoder=CICIOT2023_AUTOENCODER,
    seed_cohort=BOUNDED_EVIDENCE_SEED_COHORT,
    provenance_experiment=ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
    claim_wording=(
        "The privacy-incompatible centralized reference is independent pooled context "
        "for the cost of federation under the CICIoT2023 file-defined applicability "
        "boundary and is not part of the federated threshold-scope causal ladder."
    ),
)


def run_centralized_reference_seed(
    scope: CentralizedReferenceScope,
    training_seed: Seed,
) -> EvaluateCentralizedDetectorResult:
    population = scope.population
    split_protocol = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    population_result = construct_declared_population(
        ConstructDeclaredPopulationRequest(
            population=population,
            dataset=scope.dataset,
            canonical_root=DATA_ROOT / ExecutionArtifactDirectory.CANONICAL_DATA / scope.dataset.value,
            partition_seed=training_seed,
            split_protocol=split_protocol,
            controlled_condition=None,
        )
    )
    preprocessing = preprocess_centralized_population(
        CentralizedPopulationPreprocessingRequest(
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
    directory = centralized_reference_directory(scope, training_seed)
    feature_names = training_feature_names(scope.dataset)
    split_checksum = population_result.split_manifest.assignment_checksum
    preprocessing_checksum = preprocessing.result.fitted_state.estimator_checksum
    training = train_centralized_detector(
        TrainCentralizedDetectorRequest(
            coordinate=coordinate,
            training_features=pl.read_parquet(preprocessing.result.paths.train),
            feature_names=feature_names,
            preprocessing_state=preprocessing.result.fitted_state,
            split_manifest_checksum=split_checksum,
            output_directory=directory / CentralizedReferenceArtifactDirectory.TRAINING,
            training_seed=training_seed,
            autoencoder=scope.autoencoder,
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
            checkpoint=selection.selected,
            autoencoder=scope.autoencoder,
            feature_names=feature_names,
            calibration_features=pl.read_parquet(preprocessing.result.paths.calibration),
            evaluation_features=pl.read_parquet(preprocessing.result.paths.evaluation),
            batch_size=BATCH_SIZE,
            output_directory=directory / CentralizedReferenceArtifactDirectory.SCORES,
            preprocessing_state_checksum=preprocessing_checksum,
            overwrite=False,
        )
    )
    threshold = construct_centralized_threshold(
        ConstructCentralizedThresholdRequest(
            coordinate=coordinate,
            calibration_scores=scores.scoring.calibration_scores,
            output_directory=directory / CentralizedReferenceArtifactDirectory.THRESHOLD,
            protocol=CENTRALIZED_POOLED_QUANTILE_PROTOCOL,
            overwrite=False,
        )
    )
    return evaluate_centralized_detector(
        EvaluateCentralizedDetectorRequest(
            coordinate=coordinate,
            evaluation_scores=scores.scoring.evaluation_scores,
            threshold=threshold.threshold,
            output_directory=directory / CentralizedReferenceArtifactDirectory.EVALUATION,
            overwrite=False,
        )
    )


def centralized_reference_directory(scope: CentralizedReferenceScope, training_seed: Seed) -> Path:
    return OUTPUTS_ROOT / CentralizedReferenceArtifactDirectory.ROOT / scope.population.value / str(
        training_seed.value
    )


def centralized_reference_completion_marker(scope: CentralizedReferenceScope) -> Path:
    return (
        OUTPUTS_ROOT
        / CentralizedReferenceArtifactDirectory.ROOT
        / scope.population.value
        / CentralizedReferenceReportAsset.COMPLETE
    )


def centralized_reference_report_complete(scope: CentralizedReferenceScope) -> Path:
    return (
        OUTPUTS_ROOT
        / CentralizedReferenceArtifactDirectory.ROOT
        / scope.population.value
        / CentralizedReferenceReportAsset.DIRECTORY
        / CentralizedReferenceReportAsset.COMPLETE
    )


def report_centralized_reference(
    scope: CentralizedReferenceScope,
    *,
    output_root: Path,
    overwrite: bool,
) -> Path:
    """Validate every independent centralized-reference artifact and publish the contextual reference."""
    root = output_root / CentralizedReferenceArtifactDirectory.ROOT / scope.population.value
    if not (root / CentralizedReferenceReportAsset.COMPLETE).is_file():
        raise ReportEvidenceError(
            "centralized reference completion marker is missing; "
            "centralized-reference seed artifacts are not all present",
            subject=scope.population,
        )
    evaluations: list[CentralizedEvaluationDocument] = []
    for seed in scope.seed_cohort.values:
        evaluation_directory = (
            root / str(seed.value) / CentralizedReferenceArtifactDirectory.EVALUATION
        )
        document_path = evaluation_directory / CentralizedEvaluationPublicationAsset.EVALUATION
        complete = evaluation_directory / CentralizedEvaluationPublicationAsset.COMPLETE
        if not document_path.is_file() or not complete.is_file():
            raise ReportEvidenceError(
                f"centralized reference evaluation is incomplete for seed {seed.value}",
                subject=scope.population,
            )
        document = CentralizedEvaluationDocument.model_validate_json(document_path.read_text(encoding="utf-8"))
        _validate_centralized_reference_coordinate(scope, document.coordinate, seed)
        evaluations.append(document)
    manifest = CentralizedReferenceReportManifest(
        population=scope.population,
        evaluations=tuple(evaluations),
    )
    report_directory = root / CentralizedReferenceReportAsset.DIRECTORY
    if overwrite and report_directory.exists():
        rmtree(report_directory)
    report_directory.mkdir(parents=True, exist_ok=True)
    write_text_atomically(
        report_directory / CentralizedReferenceReportAsset.MANIFEST,
        canonical_json_text(manifest),
    )
    export_markdown(
        _centralized_reference_publication(scope, manifest),
        report_directory / CentralizedReferenceReportAsset.PUBLICATION,
    )
    write_text_atomically(
        report_directory / CentralizedReferenceReportAsset.COMPLETE,
        canonical_checksum(manifest).value + "\n",
    )
    return report_directory


def _validate_centralized_reference_coordinate(
    scope: CentralizedReferenceScope,
    coordinate: CentralizedTrainingCoordinate,
    seed: Seed,
) -> None:
    expected = CentralizedTrainingCoordinate(
        population=scope.population,
        training_seed=seed,
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    )
    if coordinate != expected:
        raise ReportEvidenceError(
            f"centralized reference coordinate does not match the locked programme for seed {seed.value}",
            subject=scope.population,
        )


def _centralized_reference_publication(
    scope: CentralizedReferenceScope,
    manifest: CentralizedReferenceReportManifest,
) -> PublicationBundle:
    all_metrics_available = all(
        all(isinstance(metric, AvailableMetric) for metric in evaluation.metrics) for evaluation in manifest.evaluations
    )
    availability = AvailabilityStatus.AVAILABLE if all_metrics_available else AvailabilityStatus.UNAVAILABLE
    claim = validate_claim(
        ClaimRequest(
            kind=ClaimKind.SUPPORTIVE,
            evidence_role=EvidenceRole.SUPPORTIVE,
            metric=MetricId.FALSE_POSITIVE_RATE,
            availability=availability,
            evidence_decision=EvidenceDecision.SUPPORTED if all_metrics_available else EvidenceDecision.BOUNDARY,
            verified_anchor_gate=None,
            traffic_rate_available=False,
            population=scope.population,
            wording=scope.claim_wording,
        )
    )
    return PublicationBundle(
        provenance=ReportProvenance(
            experiment=scope.provenance_experiment,
            population=scope.population,
            evidence_role=EvidenceRole.SUPPORTIVE,
            analysis_checksum=canonical_checksum(manifest),
        ),
        claims=(claim,),
        tables=tuple(_centralized_reference_table(evaluation) for evaluation in manifest.evaluations),
        figures=(),
    )


def _centralized_reference_table(evaluation: CentralizedEvaluationDocument) -> PublicationTable:
    cells: list[TableCell] = []
    for metric_id in CENTRALIZED_POOLED_METRICS:
        metric = metric_by_id(evaluation.metrics, metric_id)
        if isinstance(metric, AvailableMetric):
            cells.append(
                TableCell(
                    metric=metric_id,
                    availability=AvailabilityStatus.AVAILABLE,
                    rendered_value=f"{metric.value.value:.6g}",
                    evidence=f"pooled centralized held-out metric; seed={evaluation.coordinate.training_seed.value}",
                )
            )
        else:
            cells.append(
                TableCell(
                    metric=metric_id,
                    availability=_metric_availability(metric.status),
                    rendered_value="",
                    evidence=f"unavailable: {metric.reason.value}",
                )
            )
    return PublicationTable(
        title=f"Centralized reference seed {evaluation.coordinate.training_seed.value}",
        cells=tuple(cells),
    )


def _metric_availability(status: MetricStatus) -> AvailabilityStatus:
    match status:
        case MetricStatus.AVAILABLE:
            return AvailabilityStatus.AVAILABLE
        case MetricStatus.UNAVAILABLE | MetricStatus.BLOCKED:
            return AvailabilityStatus.UNAVAILABLE
        case MetricStatus.UNDEFINED:
            return AvailabilityStatus.UNDEFINED
        case MetricStatus.SUPPRESSED:
            return AvailabilityStatus.SUPPRESSED
        case MetricStatus.INFEASIBLE:
            return AvailabilityStatus.INFEASIBLE
