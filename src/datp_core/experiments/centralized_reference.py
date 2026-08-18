from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.analysis.metrics.models import AvailableMetric, MetricStatus, metric_by_id
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import (
    ErrorMessage,
    ReportEvidenceError,
)
from datp_core.core.identifiers import (
    AvailabilityStatus,
    CentralizedModelId,
    ClaimWording,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    FileContentText,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
)
from datp_core.core.numeric import Seed
from datp_core.data.populations.declarations import split_protocol_for_population
from datp_core.data.preprocessing.centralized import (
    CentralizedPopulationPreprocessingRequest,
    preprocess_centralized_population,
)
from datp_core.detector.checkpoints.protocols import DIAGNOSTIC_SNAPSHOT_PROTOCOL
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
from datp_core.presentation.export import (
    PUBLICATION_FILENAME,
    PublicationBundle,
    ReportProvenance,
    export_markdown,
    format_publication_metric,
)
from datp_core.presentation.tables import (
    EvidenceText,
    PublicationTable,
    TableCell,
    TableCellRenderedValue,
    TableTitle,
)
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
    claim_wording: ClaimWording


NBAIOT_CENTRALIZED_REFERENCE = CentralizedReferenceScope(
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    dataset=DatasetId.NBAIOT,
    autoencoder=NBAIOT_AUTOENCODER,
    seed_cohort=CONFIRMATORY_SEED_COHORT,
    provenance_experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
    claim_wording=ClaimWording(
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
    claim_wording=ClaimWording(
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
    split_protocol = split_protocol_for_population(population)
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
    training = train_centralized_detector(
        TrainCentralizedDetectorRequest(
            coordinate=coordinate,
            training_features=pl.read_parquet(preprocessing.result.paths.train),
            feature_names=feature_names,
            preprocessing_state=preprocessing.result.fitted_state,
            training_seed=training_seed,
            autoencoder=scope.autoencoder,
            diagnostic_snapshot_protocol=DIAGNOSTIC_SNAPSHOT_PROTOCOL,
        )
    )
    scores = generate_centralized_scores(
        GenerateCentralizedScoresRequest(
            coordinate=coordinate,
            training=training.training,
            autoencoder=scope.autoencoder,
            feature_names=feature_names,
            calibration_features=pl.read_parquet(preprocessing.result.paths.calibration),
            evaluation_features=pl.read_parquet(preprocessing.result.paths.evaluation),
            batch_size=BATCH_SIZE,
            output_directory=directory / CentralizedReferenceArtifactDirectory.SCORES,
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
    return OUTPUTS_ROOT / CentralizedReferenceArtifactDirectory.ROOT / scope.population.value / str(training_seed.value)


def report_centralized_reference(
    scope: CentralizedReferenceScope,
    *,
    output_root: Path,
    overwrite: bool,
) -> Path:
    root = output_root / CentralizedReferenceArtifactDirectory.ROOT / scope.population.value
    evaluations: list[CentralizedEvaluationDocument] = []
    for seed in scope.seed_cohort.values:
        evaluation_directory = root / str(seed.value) / CentralizedReferenceArtifactDirectory.EVALUATION
        document_path = evaluation_directory / CentralizedEvaluationPublicationAsset.EVALUATION
        if not document_path.is_file():
            raise ReportEvidenceError(
                ErrorMessage(f"centralized reference evaluation is incomplete for seed {seed.value}"),
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
        FileContentText(canonical_json_text(manifest)),
    )
    export_markdown(
        _centralized_reference_publication(scope, manifest),
        report_directory / CentralizedReferenceReportAsset.PUBLICATION,
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
        split_protocol=split_protocol_for_population(scope.population),
        preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    )
    if coordinate != expected:
        raise ReportEvidenceError(
            ErrorMessage(f"centralized reference coordinate does not match the locked programme for seed {seed.value}"),
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
                    rendered_value=TableCellRenderedValue(format_publication_metric(metric.value.value)),
                    evidence=EvidenceText(
                        f"pooled centralized held-out metric; seed={evaluation.coordinate.training_seed.value}"
                    ),
                )
            )
        else:
            cells.append(
                TableCell(
                    metric=metric_id,
                    availability=_metric_availability(metric.status),
                    rendered_value=TableCellRenderedValue(""),
                    evidence=EvidenceText(f"unavailable: {metric.reason.value}"),
                )
            )
    return PublicationTable(
        title=TableTitle(f"Centralized reference seed {evaluation.coordinate.training_seed.value}"),
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
