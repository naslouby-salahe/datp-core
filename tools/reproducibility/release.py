from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from hashlib import sha256
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from platform import node, platform, processor
from re import fullmatch
from shutil import copy2
from subprocess import CalledProcessError, TimeoutExpired, run
from sys import argv, version

from tools.reproducibility.audit import AUDIT_REPORT_FILENAME, read_audit_report

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.artifacts.repositories.evaluations import FederatedEvaluationAssetName
from datp_core.artifacts.repositories.thresholds import FederatedThresholdAssetName
from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage
from datp_core.core.identifiers import PartitionRole
from datp_core.data.populations.contracts import SplitManifestDocument
from datp_core.data.populations.integrity import ordered_row_identity_set
from datp_core.data.registry import population_declaration
from datp_core.detector.checkpoints.identities import FederatedHistoryAssetName
from datp_core.detector.scoring.models import FederatedScoreAssetName
from datp_core.experiments.common.coordinates import ExternalTemporalExecutionIdentity
from datp_core.experiments.common.seeds import (
    ANCHOR_ANALYSIS_SEED,
    CONFIRMATORY_ANALYSIS_SEED,
    CONFIRMATORY_SEED_COHORT,
)
from datp_core.experiments.execution.layout import (
    ExecutionArtifactDirectory,
    bounded_evidence_seed_directory,
    federated_training_directory,
)

_MANIFEST_FILENAME = "MANIFEST_SHA256.csv"
_SIDECAR_FILENAME = "MANIFEST_SHA256.sha256"
_ROADMAP_LOCK_FILENAME = "ROADMAP_LOCK.md"
_ROADMAP_LOCK_TITLE = "# DATP-Core roadmap lock"
_ROADMAP_SNAPSHOT_HEADING = "## Exact roadmap snapshot"
_WITHHELD_RECORD_FILENAME = "withheld_artifacts.csv"
_SEED_REGISTRY_FILENAME = "SEEDS.csv"
_PUBLICATION_MANIFEST_FILENAME = "publication_source_manifest.json"
_CANONICAL_PROVENANCE_FILENAMES = frozenset({"dataset_manifest.json", "schema.json"})
_PREPROCESSING_FILENAMES = frozenset({"preprocessing_manifest.json", "state.skops", "validation_report.json"})
_SPLIT_IDENTITY_FILENAMES = frozenset(
    {
        "population_manifest.json",
        "membership.parquet",
        "split_manifest.json",
        "split_assignments.parquet",
        "matched_static_reference_manifest.json",
        "matched_static_reference_membership.parquet",
        "matched_static_reference_split_manifest.json",
        "matched_static_reference_split_assignments.parquet",
        "split_manifest.parquet",
    }
)
_CAMPAIGN_POPULATION_FILENAMES = frozenset(
    {
        "population_manifest.json",
        "membership.parquet",
        "matched_static_reference_manifest.json",
        "matched_static_reference_membership.parquet",
    }
)
_CAMPAIGN_SPLIT_FILENAMES = frozenset(
    {
        "split_manifest.json",
        "split_assignments.parquet",
        "matched_static_reference_split_manifest.json",
        "matched_static_reference_split_assignments.parquet",
    }
)
_REQUIRED_DIRECTORIES = (
    "DATA_PROVENANCE",
    "SPLIT_IDENTITY",
    "PREPROCESSING",
    "MODELS",
    "SCORES",
    "THRESHOLDS",
    "METRICS",
    "STATISTICS",
    "FIGURE_TABLE_DATA",
    "AUDIT_REPORTS",
    "ENVIRONMENT",
)
_REQUIRED_RECONSTRUCTION_DIRECTORIES = frozenset(
    {
        "DATA_PROVENANCE",
        "SPLIT_IDENTITY",
        "PREPROCESSING",
        "MODELS",
        "SCORES",
        "THRESHOLDS",
        "METRICS",
        "STATISTICS",
        "FIGURE_TABLE_DATA",
        "AUDIT_REPORTS",
    }
)
_REQUIRED_PUBLICATION_ARTIFACT_TYPES = frozenset(
    {
        "publication_source_manifest",
        "publication",
        "table_figure_source_data",
    }
)
_REQUIRED_FILES = (
    _ROADMAP_LOCK_FILENAME,
    _MANIFEST_FILENAME,
    _SIDECAR_FILENAME,
    _SEED_REGISTRY_FILENAME,
    "README_REPRODUCIBILITY.md",
)
_MANIFEST_COLUMNS = (
    "relative_path",
    "sha256",
    "bytes",
    "artifact_type",
    "dataset_id",
    "population_id",
    "training_method",
    "training_seed",
    "threshold_policy",
    "experiment_id",
)
_SCIENTIFIC_METADATA_COLUMNS = _MANIFEST_COLUMNS[3:]
_SEED_REGISTRY_COLUMNS = ("training_seed", "purpose", "derivation")
_SEED_REGISTRY_RECORDS = (
    ("confirmatory_bootstrap", str(CONFIRMATORY_ANALYSIS_SEED.value), "locked paired-inference analysis seed"),
    ("anchor_analysis", str(ANCHOR_ANALYSIS_SEED.value), "locked anchor-analysis seed"),
    ("cluster_initialization", "42", "locked cluster random_state"),
    (
        "calibration_subsample_replicate",
        "NA",
        "PCG64(sha256('DATP-Core|CALIBRATION_SUBSAMPLE|dataset|population|training_seed|client|replicate_index')[:8]"
        " mod 2^32); sorted stable_row_id pool; prefix sample",
    ),
    (
        "federated_client_round_stream",
        "NA",
        "derive_worker_seed(training_seed;round_number;population|client_id|identity_kind;training_stream), "
        "then derive_worker_seed(...;local_epoch)",
    ),
    (
        "fedavg_local_fine_tuning",
        "NA",
        "derive_worker_seed(training_seed;dataset text component;population text component;"
        "population|client_id|identity_kind;fedavg_local_fine_tuning)",
    ),
    (
        "kll_sketch_reconstruction",
        "NA",
        "derive_worker_seed(derive_worker_seed(training_seed;60000+k);70000+replicate_index); "
        "NumPy PCG64 permutation per client",
    ),
    (
        "detector_initialization",
        "NA",
        "training_seed passed to deterministic runtime configuration and autoencoder initialization",
    ),
)
_DIRECT_DEPENDENCIES = (
    "pydantic",
    "filelock",
    "networkx",
    "numpy",
    "pyarrow",
    "polars",
    "pandera",
    "duckdb",
    "datasketches",
    "matplotlib",
    "torch",
    "scikit-learn",
    "safetensors",
    "scipy",
    "structlog",
    "pingouin",
    "pandas",
    "statsmodels",
    "typer",
    "rich",
    "shellingham",
    "skops",
    "flwr",
)


@dataclass(frozen=True, slots=True)
class ReleaseManifestEntry:
    relative_path: Path
    digest: str
    byte_count: int
    artifact_type: str
    dataset_id: str
    population_id: str
    training_method: str
    training_seed: str
    threshold_policy: str
    experiment_id: str


class ReleaseState(StrEnum):
    PUBLIC = "PUBLIC"
    BLINDED_ARCHIVE = "BLINDED_ARCHIVE"
    WITHHELD_LICENSE_RESTRICTED = "WITHHELD_LICENSE_RESTRICTED"


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    source: Path
    relative_path: Path
    artifact_type: str
    dataset_id: str = "NA"
    population_id: str = "NA"
    training_method: str = "NA"
    training_seed: str = "NA"
    threshold_policy: str = "NA"
    experiment_id: str = "NA"


@dataclass(frozen=True, slots=True)
class WithheldReleaseArtifact:
    source: Path
    original_relative_path: Path
    license_reason: str
    reconstruction_instructions: str


@dataclass(frozen=True, slots=True)
class ReleaseBuildRequest:
    root: Path
    roadmap: Path
    code_revision: str
    literature_search_date: date
    state: ReleaseState
    confirmatory_seeds: tuple[int, ...]
    artifacts: tuple[ReleaseArtifact, ...]
    withheld_artifacts: tuple[WithheldReleaseArtifact, ...] = ()
    submission_date: date | None = None


@dataclass(frozen=True, slots=True)
class ReleaseValidation:
    root: Path
    entries: tuple[ReleaseManifestEntry, ...]


@dataclass(frozen=True, slots=True)
class RoadmapLock:
    state: ReleaseState
    literature_search_date: date
    submission_date: date | None


def release_artifact_from_evaluation(source: Path, relative_path: Path) -> ReleaseArtifact:
    """Bind released evaluation evidence to its persisted scientific coordinate."""

    return _release_artifact_from_document(source, relative_path, _load_evaluation_document(source))


def _load_evaluation_document(source: Path) -> FederatedEvaluationDocument:
    try:
        return FederatedEvaluationDocument.model_validate_json(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ArtifactIntegrityError(ErrorMessage(f"released evaluation document is unreadable: {source}")) from error


def campaign_evaluation_release_artifacts(output_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Discover only persisted evaluation documents and bind each release entry to its stored coordinate."""

    documents = tuple(sorted(output_root.rglob(FederatedEvaluationAssetName.DOCUMENT.value)))
    if not documents:
        raise ArtifactIntegrityError(ErrorMessage("campaign release requires persisted evaluation documents"))
    return tuple(
        release_artifact_from_evaluation(
            document,
            Path("METRICS") / document.relative_to(output_root),
        )
        for document in documents
    )


def campaign_threshold_release_artifacts(output_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Discover threshold outputs and inherit provenance from their same-coordinate evaluation document."""

    results = tuple(sorted(output_root.rglob(FederatedThresholdAssetName.RESULT.value)))
    if not results:
        raise ArtifactIntegrityError(ErrorMessage("campaign release requires persisted threshold results"))
    artifacts: list[ReleaseArtifact] = []
    for result in results:
        artifacts.extend(_threshold_release_artifacts_for_result(output_root, result))
    return tuple(artifacts)


def campaign_standard_training_release_artifacts(output_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Release standard federated models, histories, and score files from typed evaluation coordinates only."""

    documents = tuple(sorted(output_root.rglob(FederatedEvaluationAssetName.DOCUMENT.value)))
    training_evidence: dict[Path, tuple[Path, FederatedEvaluationDocument]] = {}
    for source in documents:
        document = _load_evaluation_document(source)
        directory = federated_training_directory(document.score_coordinate, output_root)
        if directory.is_dir():
            training_evidence.setdefault(directory, (source, document))
    if not training_evidence:
        raise ArtifactIntegrityError(ErrorMessage("campaign release requires standard federated training evidence"))
    artifacts: list[ReleaseArtifact] = []
    for directory, (source, document) in sorted(training_evidence.items()):
        coordinate = _release_artifact_from_document(
            source, Path("METRICS") / source.relative_to(output_root), document
        )
        artifacts.extend(_standard_training_release_artifacts(output_root, directory, document, coordinate))
    return tuple(artifacts)


def campaign_bounded_training_release_artifacts(output_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Release bounded/temporal model and score evidence using each persisted full execution coordinate."""

    documents = tuple(sorted(output_root.rglob(FederatedEvaluationAssetName.DOCUMENT.value)))
    training_evidence: dict[Path, tuple[Path, FederatedEvaluationDocument]] = {}
    for source in documents:
        document = _load_evaluation_document(source)
        coordinate = document.execution_coordinate
        if coordinate is None:
            continue
        identity = ExternalTemporalExecutionIdentity(
            experiment=coordinate.experiment,
            population=coordinate.population,
            evidence_role=coordinate.evidence_role,
            temporal_state=coordinate.temporal_state,
        )
        directory = (
            bounded_evidence_seed_directory(identity, coordinate.training_seed, output_root)
            / ExecutionArtifactDirectory.TRAINING
        )
        if directory.is_dir():
            training_evidence.setdefault(directory, (source, document))
    if not training_evidence:
        raise ArtifactIntegrityError(ErrorMessage("campaign release requires bounded training evidence"))
    artifacts: list[ReleaseArtifact] = []
    for directory, (source, document) in sorted(training_evidence.items()):
        coordinate_artifact = _release_artifact_from_document(
            source, Path("METRICS") / source.relative_to(output_root), document
        )
        artifacts.extend(_standard_training_release_artifacts(output_root, directory, document, coordinate_artifact))
    return tuple(artifacts)


def preparation_release_artifacts(data_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Retain preparation metadata while leaving raw and bulk processed rows subject to license policy."""

    canonical = data_root / "canonical"
    processed = data_root / "processed"
    if not canonical.is_dir() or not processed.is_dir():
        raise ArtifactIntegrityError(
            ErrorMessage("release preparation evidence requires canonical and processed data roots")
        )
    artifacts: list[ReleaseArtifact] = []
    for source in sorted(
        path for path in canonical.rglob("*") if path.is_file() and path.name in _CANONICAL_PROVENANCE_FILENAMES
    ):
        artifacts.append(
            ReleaseArtifact(
                source, Path("DATA_PROVENANCE") / source.relative_to(data_root), "canonical_data_provenance"
            )
        )
    for source in sorted(path for path in processed.rglob("*") if path.is_file()):
        if source.name in _PREPROCESSING_FILENAMES:
            artifacts.append(
                ReleaseArtifact(source, Path("PREPROCESSING") / source.relative_to(processed), "preprocessing_state")
            )
        elif source.name in _SPLIT_IDENTITY_FILENAMES:
            artifacts.append(
                ReleaseArtifact(source, Path("SPLIT_IDENTITY") / source.relative_to(processed), "split_identity")
            )
    if not artifacts:
        raise ArtifactIntegrityError(
            ErrorMessage("release preparation evidence contains no declared metadata artifacts")
        )
    return tuple(artifacts)


def campaign_analysis_release_artifacts(output_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Retain only explicitly named analysis, diagnostic, and report artifacts from a campaign output tree."""

    artifacts: list[ReleaseArtifact] = []
    for source in sorted(path for path in output_root.rglob("*") if path.is_file()):
        relative = source.relative_to(output_root)
        if "analysis" in relative.parts:
            artifacts.append(ReleaseArtifact(source, Path("STATISTICS") / relative, "analysis_result"))
        elif (
            source.name == AUDIT_REPORT_FILENAME
            or "diagnostics" in relative.parts
            or source.name.endswith(("_report.md", "_summary.txt"))
        ):
            artifacts.append(ReleaseArtifact(source, Path("AUDIT_REPORTS") / relative, "audit_report"))
    if not artifacts:
        raise ArtifactIntegrityError(
            ErrorMessage("campaign release requires retained analysis or audit-report evidence")
        )
    return tuple(artifacts)


def campaign_population_split_release_artifacts(output_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Retain every persisted population, membership, and split identity produced by execution."""

    artifacts: list[ReleaseArtifact] = []
    for source in sorted(path for path in output_root.rglob("*") if _is_regular_file(path)):
        relative = source.relative_to(output_root)
        if source.name in _CAMPAIGN_POPULATION_FILENAMES:
            artifacts.append(
                ReleaseArtifact(source, Path("SPLIT_IDENTITY") / relative, "population_construction_identity")
            )
        elif source.name in _CAMPAIGN_SPLIT_FILENAMES:
            artifacts.append(ReleaseArtifact(source, Path("SPLIT_IDENTITY") / relative, "split_identity"))
    if not artifacts:
        raise ArtifactIntegrityError(
            ErrorMessage("campaign release requires persisted population and split identity evidence")
        )
    return tuple(artifacts)


def campaign_release_artifacts(output_root: Path, data_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Assemble every required campaign evidence category before release bundle construction."""

    artifacts = tuple(
        artifact
        for group in (
            preparation_release_artifacts(data_root),
            campaign_evaluation_release_artifacts(output_root),
            campaign_threshold_release_artifacts(output_root),
            campaign_standard_training_release_artifacts(output_root),
            campaign_bounded_training_release_artifacts(output_root),
            campaign_population_split_release_artifacts(output_root),
            campaign_analysis_release_artifacts(output_root),
            campaign_publication_release_artifacts(output_root),
        )
        for artifact in group
    )
    _require_unique_release_artifacts(artifacts)
    return artifacts


def _standard_training_release_artifacts(
    output_root: Path,
    directory: Path,
    document: FederatedEvaluationDocument,
    coordinate: ReleaseArtifact,
) -> tuple[ReleaseArtifact, ...]:
    required_history = (
        FederatedHistoryAssetName.TERMINAL_MODEL,
        FederatedHistoryAssetName.ROUND_SUMMARY,
        FederatedHistoryAssetName.CLIENT_ROUNDS,
        FederatedHistoryAssetName.DEVICE_NAME,
    )
    artifacts = [
        _required_coordinate_artifact(
            output_root,
            directory / name.value,
            "terminal_model" if name is FederatedHistoryAssetName.TERMINAL_MODEL else "training_history",
            coordinate,
        )
        for name in required_history
    ]
    personalized = directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
    if personalized.is_file():
        artifacts.append(
            _artifact_with_coordinate_metadata(
                personalized,
                Path("MODELS") / personalized.relative_to(output_root),
                "personalized_training_history",
                coordinate,
            )
        )
    score_root = directory / ExecutionArtifactDirectory.SCORES.value
    for client_result in document.clients:
        client = client_result.client.client_id.value
        for asset in (FederatedScoreAssetName.CALIBRATION, FederatedScoreAssetName.EVALUATION):
            artifacts.append(
                _required_coordinate_artifact(
                    output_root,
                    score_root / client / asset.value,
                    "score_artifact",
                    coordinate,
                )
            )
        future = score_root / client / FederatedScoreAssetName.FUTURE_RECALIBRATION.value
        if future.is_file():
            artifacts.append(
                _artifact_with_coordinate_metadata(
                    future, Path("SCORES") / future.relative_to(output_root), "future_recalibration_score", coordinate
                )
            )
    return tuple(artifacts)


def _required_coordinate_artifact(
    output_root: Path,
    source: Path,
    artifact_type: str,
    coordinate: ReleaseArtifact,
) -> ReleaseArtifact:
    if not source.is_file():
        raise ArtifactIntegrityError(ErrorMessage(f"coordinate release artifact is missing: {source}"))
    logical_directory = "MODELS" if artifact_type in {"terminal_model", "training_history"} else "SCORES"
    return _artifact_with_coordinate_metadata(
        source, Path(logical_directory) / source.relative_to(output_root), artifact_type, coordinate
    )


def _threshold_release_artifacts_for_result(output_root: Path, result: Path) -> tuple[ReleaseArtifact, ...]:
    evaluation = result.parent.parent / "evaluation" / FederatedEvaluationAssetName.DOCUMENT.value
    if not evaluation.is_file():
        raise ArtifactIntegrityError(ErrorMessage(f"threshold result has no sibling evaluation evidence: {result}"))
    coordinate_artifact = release_artifact_from_evaluation(
        evaluation, Path("METRICS") / evaluation.relative_to(output_root)
    )
    relative = result.relative_to(output_root)
    artifacts = [
        _artifact_with_coordinate_metadata(
            result,
            Path("THRESHOLDS") / relative,
            "threshold_result",
            coordinate_artifact,
        )
    ]
    temporal_provenance = result.parent / FederatedThresholdAssetName.TEMPORAL_PROVENANCE.value
    if temporal_provenance.is_file():
        artifacts.append(
            _artifact_with_coordinate_metadata(
                temporal_provenance,
                Path("THRESHOLDS") / temporal_provenance.relative_to(output_root),
                "temporal_threshold_provenance",
                coordinate_artifact,
            )
        )
    return tuple(artifacts)


def _artifact_with_coordinate_metadata(
    source: Path,
    relative_path: Path,
    artifact_type: str,
    coordinate_artifact: ReleaseArtifact,
) -> ReleaseArtifact:
    return ReleaseArtifact(
        source=source,
        relative_path=relative_path,
        artifact_type=artifact_type,
        dataset_id=coordinate_artifact.dataset_id,
        population_id=coordinate_artifact.population_id,
        training_method=coordinate_artifact.training_method,
        training_seed=coordinate_artifact.training_seed,
        threshold_policy=coordinate_artifact.threshold_policy,
        experiment_id=coordinate_artifact.experiment_id,
    )


def campaign_publication_release_artifacts(output_root: Path) -> tuple[ReleaseArtifact, ...]:
    """Retain publications and every manifest-declared table/figure source file."""

    manifests = tuple(sorted(output_root.rglob(_PUBLICATION_MANIFEST_FILENAME)))
    artifacts: list[ReleaseArtifact] = []
    for manifest in manifests:
        relative = manifest.relative_to(output_root)
        artifacts.append(ReleaseArtifact(manifest, Path("FIGURE_TABLE_DATA") / relative, "publication_source_manifest"))
        publication = manifest.parent / "publication.md"
        if not _is_regular_file(publication):
            raise ArtifactIntegrityError(ErrorMessage(f"publication source manifest has no publication: {manifest}"))
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ArtifactIntegrityError(
                ErrorMessage(f"publication source manifest is unreadable: {manifest}")
            ) from error
        _validate_declared_publication(manifest, payload, publication)
        artifacts.append(
            ReleaseArtifact(
                publication,
                Path("FIGURE_TABLE_DATA") / relative.parent / publication.name,
                "publication",
            )
        )
        for source in _publication_source_paths(manifest):
            artifacts.append(
                ReleaseArtifact(
                    source,
                    Path("FIGURE_TABLE_DATA") / relative.parent / source.name,
                    "table_figure_source_data",
                )
            )
    return tuple(artifacts)


def _publication_source_paths(manifest: Path) -> tuple[Path, ...]:
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        sources = payload["sources"]
    except (OSError, ValueError, KeyError) as error:
        raise ArtifactIntegrityError(ErrorMessage(f"publication source manifest is unreadable: {manifest}")) from error
    if not isinstance(sources, list) or not sources:
        raise ArtifactIntegrityError(ErrorMessage(f"publication source manifest has no declared sources: {manifest}"))
    paths: list[Path] = []
    for source in sources:
        if not isinstance(source, dict) or not isinstance(filename := source.get("filename"), str):
            raise ArtifactIntegrityError(ErrorMessage(f"publication source manifest has an invalid source: {manifest}"))
        path = Path(filename)
        if (
            path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 1
            or not _is_regular_file(manifest.parent / path)
        ):
            raise ArtifactIntegrityError(
                ErrorMessage(f"publication source is missing or invalid: {manifest} / {filename}")
            )
        _validate_declared_publication_source(manifest, source, manifest.parent / path)
        paths.append(manifest.parent / path)
    if len(paths) != len(set(paths)):
        raise ArtifactIntegrityError(ErrorMessage(f"publication source manifest repeats a source: {manifest}"))
    return tuple(paths)


def _validate_declared_publication(manifest: Path, payload: object, publication: Path) -> None:
    """Bind the rendered claim text itself to the source manifest before release assembly."""

    if not isinstance(payload, dict):
        raise ArtifactIntegrityError(ErrorMessage(f"publication source manifest is invalid: {manifest}"))
    declared_name = payload.get("publication")
    if declared_name != publication.name:
        raise ArtifactIntegrityError(
            ErrorMessage(f"publication source manifest names an invalid publication: {manifest}")
        )
    declared_bytes = payload.get("publication_bytes")
    if not isinstance(declared_bytes, int) or declared_bytes != publication.stat().st_size:
        raise ArtifactIntegrityError(ErrorMessage(f"publication byte count does not match: {manifest}"))
    declared_digest = payload.get("publication_sha256")
    if (
        not isinstance(declared_digest, str)
        or fullmatch(r"[0-9a-f]{64}", declared_digest) is None
        or declared_digest != _sha256_file(publication)
    ):
        raise ArtifactIntegrityError(ErrorMessage(f"publication digest does not match: {manifest}"))


def _validate_declared_publication_source(manifest: Path, source: object, path: Path) -> None:
    """Verify optional export-time source integrity fields before a release copies the bytes."""

    if not isinstance(source, dict):
        return
    declared_bytes = source.get("bytes")
    if declared_bytes is not None and (not isinstance(declared_bytes, int) or declared_bytes != path.stat().st_size):
        raise ArtifactIntegrityError(
            ErrorMessage(f"publication source byte count does not match: {manifest} / {path.name}")
        )
    declared_digest = source.get("sha256")
    if declared_digest is not None and (
        not isinstance(declared_digest, str)
        or fullmatch(r"[0-9a-f]{64}", declared_digest) is None
        or declared_digest != _sha256_file(path)
    ):
        raise ArtifactIntegrityError(
            ErrorMessage(f"publication source digest does not match: {manifest} / {path.name}")
        )
    declared_rows = source.get("row_count")
    if declared_rows is not None and (
        not isinstance(declared_rows, int) or declared_rows != _publication_source_row_count(path)
    ):
        raise ArtifactIntegrityError(
            ErrorMessage(f"publication source row count does not match: {manifest} / {path.name}")
        )


def _publication_source_row_count(path: Path) -> int:
    if path.suffix != ".csv":
        return 1
    with path.open(encoding="utf-8", newline="") as stream:
        return sum(1 for _ in csv.DictReader(stream))


def _release_artifact_from_document(
    source: Path,
    relative_path: Path,
    document: FederatedEvaluationDocument,
) -> ReleaseArtifact:
    coordinate = document.score_coordinate
    execution_coordinate = document.execution_coordinate
    if execution_coordinate is None:
        raise ArtifactIntegrityError(
            ErrorMessage("released evaluation document requires a persisted complete execution coordinate")
        )
    return ReleaseArtifact(
        source=source,
        relative_path=relative_path,
        artifact_type="federated_evaluation_document",
        dataset_id=population_declaration(coordinate.population).dataset.value,
        population_id=coordinate.population.value,
        training_method=coordinate.model.value,
        training_seed=str(coordinate.training_seed.value),
        threshold_policy=document.threshold_method.value,
        experiment_id=execution_coordinate.experiment.value,
    )


def validate_release_bundle(root: Path) -> ReleaseValidation:
    """Validate the complete released-byte inventory required for reconstruction."""

    _require_payload_layout(root)
    roadmap_lock = _read_roadmap_lock(root / _ROADMAP_LOCK_FILENAME)
    _validate_seed_registry(root / _SEED_REGISTRY_FILENAME)
    _validate_release_state_and_withheld_records(root, roadmap_lock)
    _validate_retained_audit_reports(root)
    manifest_path = root / _MANIFEST_FILENAME
    _validate_manifest_sidecar(manifest_path, root / _SIDECAR_FILENAME)
    entries = _read_manifest(manifest_path)
    _validate_manifest_files(root, entries)
    _validate_released_split_identity_evidence(root, entries)
    return ReleaseValidation(root=root, entries=entries)


def _validate_retained_audit_reports(root: Path) -> None:
    for report in sorted((root / "AUDIT_REPORTS").rglob(AUDIT_REPORT_FILENAME)):
        audit_report = read_audit_report(report)
        for record in audit_report.records:
            for evidence_path in record.evidence_paths:
                if not (root / evidence_path).is_file():
                    raise ArtifactIntegrityError(
                        ErrorMessage(f"audit record references a missing release artifact: {evidence_path}")
                    )


def _validate_released_split_identity_evidence(root: Path, entries: tuple[ReleaseManifestEntry, ...]) -> None:
    """Verify released split manifests prove the ordered identities of each reportable partition."""

    for entry in entries:
        if entry.artifact_type != "split_identity" or entry.relative_path.name not in {
            "split_manifest.json",
            "matched_static_reference_split_manifest.json",
        }:
            continue
        suffix = (
            "split_assignments.parquet"
            if entry.relative_path.name == "split_manifest.json"
            else "matched_static_reference_split_assignments.parquet"
        )
        assignments_path = root / entry.relative_path.with_name(suffix)
        if not _is_regular_file(assignments_path):
            raise ArtifactIntegrityError(
                ErrorMessage(f"released split manifest has no assignment artifact: {entry.relative_path}")
            )
        try:
            import polars as pl

            manifest = SplitManifestDocument.model_validate_json(
                (root / entry.relative_path).read_text(encoding="utf-8")
            )
            assignments = pl.read_parquet(assignments_path)
        except (OSError, ValueError, pl.exceptions.PolarsError) as error:
            raise ArtifactIntegrityError(
                ErrorMessage(f"released split identity evidence is unreadable: {entry.relative_path}")
            ) from error
        expected = (
            (PartitionRole.TRAIN, manifest.train_ordered_rows),
            (PartitionRole.CALIBRATION, manifest.calibration_ordered_rows),
            (PartitionRole.EVALUATION, manifest.evaluation_ordered_rows),
        )
        if any(ordered_row_identity_set(assignments, role) != row_set for role, row_set in expected):
            raise ArtifactIntegrityError(
                ErrorMessage(f"released split ordered-row identity proof does not match: {entry.relative_path}")
            )


def _validate_seed_registry(path: Path) -> None:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != _SEED_REGISTRY_COLUMNS:
            raise ArtifactIntegrityError(ErrorMessage("release seed registry columns do not match the locked schema"))
        rows = tuple(reader)
    if any(any(row.get(column) in {None, ""} for column in _SEED_REGISTRY_COLUMNS) for row in rows):
        raise ArtifactIntegrityError(ErrorMessage("release seed registry fields must be explicit"))
    training_rows = tuple(row for row in rows if row["purpose"] == "confirmatory_training")
    expected_training_seeds = tuple(str(seed.value) for seed in CONFIRMATORY_SEED_COHORT.values)
    if len(training_rows) != len(expected_training_seeds):
        raise ArtifactIntegrityError(
            ErrorMessage("release seed registry requires exactly ten confirmatory training seeds")
        )
    if tuple(row["training_seed"] for row in training_rows) != expected_training_seeds or any(
        row["derivation"] != "declared_confirmatory_seed_cohort" for row in training_rows
    ):
        raise ArtifactIntegrityError(
            ErrorMessage("release seed registry confirmatory cohort does not match the locked seed declaration")
        )
    nested_rows = tuple(row for row in rows if row["purpose"] != "confirmatory_training")
    expected_nested_rows = tuple(
        {"training_seed": seed, "purpose": purpose, "derivation": derivation}
        for purpose, seed, derivation in _SEED_REGISTRY_RECORDS
    )
    if nested_rows != expected_nested_rows:
        raise ArtifactIntegrityError(
            ErrorMessage("release seed registry does not declare the complete locked nested-seed derivations")
        )


def _read_roadmap_lock(path: Path) -> RoadmapLock:
    contents = path.read_bytes()
    marker = f"{_ROADMAP_SNAPSHOT_HEADING}\n\n".encode()
    header, separator, snapshot = contents.partition(marker)
    if not separator or not snapshot:
        raise ArtifactIntegrityError(ErrorMessage("release roadmap lock must contain an exact roadmap snapshot"))
    try:
        lines = tuple(header.decode("utf-8").splitlines())
    except UnicodeDecodeError as error:
        raise ArtifactIntegrityError(ErrorMessage("release roadmap lock header must be UTF-8")) from error
    if len(lines) != 8 or lines[0] != _ROADMAP_LOCK_TITLE or lines[1] != "" or lines[-1] != "":
        raise ArtifactIntegrityError(ErrorMessage("release roadmap lock header does not match the locked schema"))
    digest = _roadmap_lock_value(lines[2], "Roadmap SHA-256")
    revision = _roadmap_lock_value(lines[3], "Code revision")
    search_date = _roadmap_lock_value(lines[4], "Literature search date")
    if fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ArtifactIntegrityError(ErrorMessage("release roadmap lock requires a lowercase roadmap SHA-256 digest"))
    if digest != sha256(snapshot).hexdigest():
        raise ArtifactIntegrityError(ErrorMessage("release roadmap snapshot does not match its locked SHA-256 digest"))
    if not revision or any(character.isspace() for character in revision):
        raise ArtifactIntegrityError(ErrorMessage("release roadmap lock requires a code revision"))
    try:
        parsed_search_date = date.fromisoformat(search_date)
    except ValueError as error:
        raise ArtifactIntegrityError(
            ErrorMessage("release roadmap lock requires an ISO literature search date")
        ) from error
    submission_date = _submission_date_from_lock(lines[5])
    if submission_date is not None:
        elapsed_days = (submission_date - parsed_search_date).days
        if not 0 <= elapsed_days <= 14:
            raise ArtifactIntegrityError(
                ErrorMessage("submission-time literature search must be dated 0 through 14 days before submission")
            )
    try:
        state = ReleaseState(_roadmap_lock_value(lines[6], "Release state"))
    except ValueError as error:
        raise ArtifactIntegrityError(ErrorMessage("release roadmap lock contains an unknown release state")) from error
    return RoadmapLock(
        state=state,
        literature_search_date=parsed_search_date,
        submission_date=submission_date,
    )


def _roadmap_lock_value(line: str, label: str) -> str:
    prefix = f"- {label}: `"
    if not line.startswith(prefix) or not line.endswith("`"):
        raise ArtifactIntegrityError(ErrorMessage(f"release roadmap lock field is malformed: {label}"))
    return line.removeprefix(prefix).removesuffix("`")


def _submission_date_from_lock(line: str) -> date | None:
    value = _roadmap_lock_value(line, "Submission date")
    if value == "NOT_APPLICABLE":
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ArtifactIntegrityError(
            ErrorMessage("release roadmap lock requires an ISO submission date or NOT_APPLICABLE")
        ) from error


def _validate_release_state_and_withheld_records(root: Path, roadmap_lock: RoadmapLock) -> None:
    record = root / "DATA_PROVENANCE" / _WITHHELD_RECORD_FILENAME
    if roadmap_lock.state is ReleaseState.WITHHELD_LICENSE_RESTRICTED:
        if not record.is_file():
            raise ArtifactIntegrityError(
                ErrorMessage("license-restricted release is missing withheld artifact records")
            )
        _validate_withheld_artifact_records(record)
    elif record.exists():
        raise ArtifactIntegrityError(ErrorMessage("non-restricted release must not contain withheld artifact records"))


def _validate_withheld_artifact_records(path: Path) -> None:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        expected_columns = (
            "original_relative_path",
            "sha256",
            "bytes",
            "license_reason",
            "reconstruction_instructions",
        )
        if tuple(reader.fieldnames or ()) != expected_columns:
            raise ArtifactIntegrityError(
                ErrorMessage("withheld artifact record columns do not match the locked schema")
            )
        rows = tuple(reader)
    if not rows:
        raise ArtifactIntegrityError(ErrorMessage("withheld artifact record must list at least one artifact"))
    paths: list[Path] = []
    for row in rows:
        values = tuple(row.get(column) for column in expected_columns)
        if any(value is None or value == "" for value in values):
            raise ArtifactIntegrityError(ErrorMessage("withheld artifact record fields must be explicit"))
        original = Path(_required_value(row, "original_relative_path"))
        _require_relative_artifact_path(original)
        if fullmatch(r"[0-9a-f]{64}", _required_value(row, "sha256")) is None:
            raise ArtifactIntegrityError(ErrorMessage("withheld artifact record requires lowercase SHA-256 digests"))
        try:
            if int(_required_value(row, "bytes")) < 0:
                raise ValueError
        except ValueError as error:
            raise ArtifactIntegrityError(
                ErrorMessage("withheld artifact record byte count must be non-negative")
            ) from error
        paths.append(original)
    if len(paths) != len(frozenset(paths)):
        raise ArtifactIntegrityError(ErrorMessage("withheld artifact record repeats an original path"))


def build_release_bundle(request: ReleaseBuildRequest) -> ReleaseValidation:
    """Build a release only from explicit retained artifacts, then validate its exact byte inventory."""

    if request.root.exists():
        raise ArtifactIntegrityError(ErrorMessage("release destination must not already exist"))
    if not request.roadmap.is_file():
        raise ArtifactIntegrityError(ErrorMessage("release roadmap snapshot is missing"))
    if not request.code_revision:
        raise ArtifactIntegrityError(ErrorMessage("release requires a code revision"))
    if request.submission_date is not None:
        elapsed_days = (request.submission_date - request.literature_search_date).days
        if not 0 <= elapsed_days <= 14:
            raise ArtifactIntegrityError(
                ErrorMessage("submission-time literature search must be dated 0 through 14 days before submission")
            )
    if request.confirmatory_seeds != tuple(seed.value for seed in CONFIRMATORY_SEED_COHORT.values):
        raise ArtifactIntegrityError(ErrorMessage("release requires the locked ordered ten-seed confirmatory cohort"))
    _require_unique_release_artifacts(request.artifacts)
    _validate_withheld_artifacts(request)
    request.root.mkdir(parents=True)
    for directory in _REQUIRED_DIRECTORIES:
        (request.root / directory).mkdir()
    _write_release_metadata(request)
    for artifact in request.artifacts:
        _copy_release_artifact(request.root, artifact)
    _write_manifest(request.root, request.artifacts)
    return validate_release_bundle(request.root)


def _require_payload_layout(root: Path) -> None:
    missing = tuple(name for name in _REQUIRED_FILES if not _is_regular_file(root / name))
    missing_directories = tuple(name for name in _REQUIRED_DIRECTORIES if not _is_regular_directory(root / name))
    if missing or missing_directories:
        raise ArtifactIntegrityError(
            ErrorMessage(
                "release bundle payload is incomplete: "
                f"files={','.join(missing) or 'none'}; directories={','.join(missing_directories) or 'none'}"
            )
        )


def _require_unique_release_artifacts(artifacts: tuple[ReleaseArtifact, ...]) -> None:
    paths = tuple(item.relative_path for item in artifacts)
    if len(paths) != len(frozenset(paths)):
        raise ArtifactIntegrityError(ErrorMessage("release artifact destinations must be unique"))
    for artifact in artifacts:
        if not _is_regular_file(artifact.source):
            raise ArtifactIntegrityError(ErrorMessage(f"release source artifact is missing: {artifact.source}"))
        _require_relative_artifact_path(artifact.relative_path)
        _require_descriptive_scientific_metadata(
            (
                artifact.artifact_type,
                artifact.dataset_id,
                artifact.population_id,
                artifact.training_method,
                artifact.training_seed,
                artifact.threshold_policy,
                artifact.experiment_id,
            )
        )


def _validate_withheld_artifacts(request: ReleaseBuildRequest) -> None:
    withheld = request.withheld_artifacts
    if request.state is ReleaseState.WITHHELD_LICENSE_RESTRICTED and not withheld:
        raise ArtifactIntegrityError(ErrorMessage("license-restricted releases require withheld artifact records"))
    if request.state is not ReleaseState.WITHHELD_LICENSE_RESTRICTED and withheld:
        raise ArtifactIntegrityError(
            ErrorMessage("withheld artifact records require the license-restricted release state")
        )
    paths = tuple(item.original_relative_path for item in withheld)
    if len(paths) != len(frozenset(paths)):
        raise ArtifactIntegrityError(ErrorMessage("withheld artifact records must have unique original paths"))
    for artifact in withheld:
        if (
            not _is_regular_file(artifact.source)
            or not artifact.license_reason
            or not artifact.reconstruction_instructions
        ):
            raise ArtifactIntegrityError(ErrorMessage("withheld artifact record is incomplete"))
        _require_relative_artifact_path(artifact.original_relative_path)


def _write_release_metadata(request: ReleaseBuildRequest) -> None:
    roadmap_digest = _sha256_file(request.roadmap)
    (request.root / _ROADMAP_LOCK_FILENAME).write_bytes(
        (
            _ROADMAP_LOCK_TITLE + "\n\n"
            f"- Roadmap SHA-256: `{roadmap_digest}`\n"
            f"- Code revision: `{request.code_revision}`\n"
            f"- Literature search date: `{request.literature_search_date.isoformat()}`\n"
            "- Submission date: `"
            f"{request.submission_date.isoformat() if request.submission_date else 'NOT_APPLICABLE'}`\n"
            f"- Release state: `{request.state.value}`\n\n" + _ROADMAP_SNAPSHOT_HEADING + "\n\n"
        ).encode()
        + request.roadmap.read_bytes()
    )
    _write_seed_registry(request.root / _SEED_REGISTRY_FILENAME, request.confirmatory_seeds)
    (request.root / "ENVIRONMENT" / "runtime.txt").write_text("\n".join(_environment_lines()) + "\n", encoding="utf-8")
    if request.withheld_artifacts:
        _write_withheld_artifact_records(request.root, request.withheld_artifacts)
    (request.root / "README_REPRODUCIBILITY.md").write_text(
        "# Reproducibility release\n\n"
        f"State: `{request.state.value}`. Validate this bundle with "
        "`python -m tools.reproducibility.release <root>`.\n",
        encoding="utf-8",
    )


def _write_seed_registry(path: Path, confirmatory_seeds: tuple[int, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(_SEED_REGISTRY_COLUMNS)
        writer.writerows(
            (seed, "confirmatory_training", "declared_confirmatory_seed_cohort") for seed in confirmatory_seeds
        )
        writer.writerows((seed, purpose, derivation) for purpose, seed, derivation in _SEED_REGISTRY_RECORDS)


def _copy_release_artifact(root: Path, artifact: ReleaseArtifact) -> None:
    destination = root / artifact.relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(artifact.source, destination)
    if not _is_regular_file(destination) or _sha256_file(destination) != _sha256_file(artifact.source):
        raise ArtifactIntegrityError(
            ErrorMessage(f"release artifact copy is not byte-identical: {artifact.relative_path}")
        )
    if (
        artifact.artifact_type == "federated_evaluation_document"
        and artifact.relative_path.name == FederatedEvaluationAssetName.DOCUMENT.value
    ):
        persisted = _release_artifact_from_document(
            destination,
            artifact.relative_path,
            _load_evaluation_document(destination),
        )
        if _release_artifact_metadata(persisted) != _release_artifact_metadata(artifact):
            raise ArtifactIntegrityError(
                ErrorMessage(
                    "release evaluation artifact coordinate does not match persisted document: "
                    f"{artifact.relative_path}"
                )
            )


def _write_withheld_artifact_records(root: Path, artifacts: tuple[WithheldReleaseArtifact, ...]) -> None:
    path = root / "DATA_PROVENANCE" / _WITHHELD_RECORD_FILENAME
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("original_relative_path", "sha256", "bytes", "license_reason", "reconstruction_instructions"))
        writer.writerows(
            (
                str(artifact.original_relative_path),
                _sha256_file(artifact.source),
                artifact.source.stat().st_size,
                artifact.license_reason,
                artifact.reconstruction_instructions,
            )
            for artifact in artifacts
        )


def _installed_version(distribution: str) -> str:
    try:
        return package_version(distribution)
    except PackageNotFoundError:
        return "NA"


def _environment_lines() -> tuple[str, ...]:
    gpu_model, gpu_count, cuda_runtime, gpu_driver, cudnn_version = _gpu_environment()
    return (
        f"python={version.replace(chr(10), ' ')}",
        f"os_kernel={platform()}",
        f"host_identifier={node() or 'NA'}",
        f"cpu_model={processor() or 'NA'}",
        f"ram_bytes={_ram_bytes()}",
        f"gpu_model={gpu_model}",
        f"gpu_count={gpu_count}",
        f"cuda_runtime={cuda_runtime}",
        f"gpu_driver={gpu_driver}",
        f"cudnn_version={cudnn_version}",
        *(f"dependency.{distribution}={_installed_version(distribution)}" for distribution in _DIRECT_DEPENDENCIES),
    )


def _ram_bytes() -> str:
    try:
        return str(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        return "NA"


def _gpu_environment() -> tuple[str, str, str, str, str]:
    try:
        import torch
    except ImportError:
        return ("NA", "0", "NA", "NA", "NA")
    if not torch.cuda.is_available():
        return ("NA", "0", torch.version.cuda or "NA", "NA", "NA")
    count = torch.cuda.device_count()
    models = ";".join(torch.cuda.get_device_name(index) for index in range(count)) or "NA"
    cudnn = torch.backends.cudnn.version()
    return (
        models,
        str(count),
        torch.version.cuda or "NA",
        _gpu_driver_version(),
        str(cudnn) if cudnn is not None else "NA",
    )


def _gpu_driver_version() -> str:
    try:
        completed = run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (CalledProcessError, FileNotFoundError, OSError, TimeoutExpired):
        return "NA"
    values = tuple(sorted({line.strip() for line in completed.stdout.splitlines() if line.strip()}))
    return ";".join(values) or "NA"


def _write_manifest(root: Path, artifacts: tuple[ReleaseArtifact, ...]) -> None:
    entries = tuple(
        _entry_from_file(root, relative_path, artifact)
        for relative_path, artifact in _generated_release_artifacts(root, artifacts)
    )
    path = root / _MANIFEST_FILENAME
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(_MANIFEST_COLUMNS)
        writer.writerows(
            (
                str(entry.relative_path),
                entry.digest,
                entry.byte_count,
                entry.artifact_type,
                entry.dataset_id,
                entry.population_id,
                entry.training_method,
                entry.training_seed,
                entry.threshold_policy,
                entry.experiment_id,
            )
            for entry in entries
        )
    (root / _SIDECAR_FILENAME).write_text(
        f"{_sha256_file(path)}  {_MANIFEST_FILENAME}\n",
        encoding="utf-8",
    )


def _generated_release_artifacts(
    root: Path,
    artifacts: tuple[ReleaseArtifact, ...],
) -> tuple[tuple[Path, ReleaseArtifact], ...]:
    generated = (
        ReleaseArtifact(root / _ROADMAP_LOCK_FILENAME, Path(_ROADMAP_LOCK_FILENAME), "roadmap_lock"),
        ReleaseArtifact(root / "SEEDS.csv", Path("SEEDS.csv"), "seed_registry"),
        ReleaseArtifact(root / "README_REPRODUCIBILITY.md", Path("README_REPRODUCIBILITY.md"), "readme"),
        ReleaseArtifact(root / "ENVIRONMENT" / "runtime.txt", Path("ENVIRONMENT/runtime.txt"), "environment"),
        *(
            (
                ReleaseArtifact(
                    root / "DATA_PROVENANCE" / _WITHHELD_RECORD_FILENAME,
                    Path("DATA_PROVENANCE") / _WITHHELD_RECORD_FILENAME,
                    "withheld_artifact_provenance",
                ),
            )
            if (root / "DATA_PROVENANCE" / _WITHHELD_RECORD_FILENAME).is_file()
            else ()
        ),
    )
    return tuple((item.relative_path, item) for item in (*generated, *artifacts))


def _entry_from_file(root: Path, relative_path: Path, artifact: ReleaseArtifact) -> ReleaseManifestEntry:
    path = root / relative_path
    return ReleaseManifestEntry(
        relative_path=relative_path,
        digest=_sha256_file(path),
        byte_count=path.stat().st_size,
        artifact_type=artifact.artifact_type,
        dataset_id=artifact.dataset_id,
        population_id=artifact.population_id,
        training_method=artifact.training_method,
        training_seed=artifact.training_seed,
        threshold_policy=artifact.threshold_policy,
        experiment_id=artifact.experiment_id,
    )


def _validate_manifest_sidecar(manifest_path: Path, sidecar_path: Path) -> None:
    expected = f"{_sha256_file(manifest_path)}  {_MANIFEST_FILENAME}\n"
    actual = sidecar_path.read_text(encoding="utf-8")
    if actual != expected:
        raise ArtifactIntegrityError(ErrorMessage("release manifest sidecar does not match the exact manifest bytes"))


def _read_manifest(path: Path) -> tuple[ReleaseManifestEntry, ...]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or tuple(reader.fieldnames) != _MANIFEST_COLUMNS:
            raise ArtifactIntegrityError(ErrorMessage("release manifest columns do not match the locked schema"))
        entries = tuple(_manifest_entry(row) for row in reader)
    if not entries:
        raise ArtifactIntegrityError(ErrorMessage("release manifest must list released artifacts"))
    paths = tuple(entry.relative_path for entry in entries)
    if len(paths) != len(frozenset(paths)):
        raise ArtifactIntegrityError(ErrorMessage("release manifest repeats an artifact path"))
    return entries


def _manifest_entry(row: dict[str, str | None]) -> ReleaseManifestEntry:
    values = tuple(row.get(column) for column in _MANIFEST_COLUMNS)
    if any(value is None or value == "" for value in values):
        raise ArtifactIntegrityError(ErrorMessage("release manifest fields must use explicit values or NA"))
    relative_path = Path(_required_value(row, "relative_path"))
    _require_relative_artifact_path(relative_path)
    digest = _required_value(row, "sha256")
    if fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ArtifactIntegrityError(ErrorMessage("release manifest requires lowercase SHA-256 digests"))
    try:
        byte_count = int(_required_value(row, "bytes"))
    except ValueError as error:
        raise ArtifactIntegrityError(ErrorMessage("release manifest byte count must be an integer")) from error
    if byte_count < 0:
        raise ArtifactIntegrityError(ErrorMessage("release manifest byte count must be non-negative"))
    entry = ReleaseManifestEntry(
        relative_path=relative_path,
        digest=digest,
        byte_count=byte_count,
        artifact_type=_required_value(row, "artifact_type"),
        dataset_id=_required_value(row, "dataset_id"),
        population_id=_required_value(row, "population_id"),
        training_method=_required_value(row, "training_method"),
        training_seed=_required_value(row, "training_seed"),
        threshold_policy=_required_value(row, "threshold_policy"),
        experiment_id=_required_value(row, "experiment_id"),
    )
    _require_descriptive_scientific_metadata(
        (
            entry.artifact_type,
            entry.dataset_id,
            entry.population_id,
            entry.training_method,
            entry.training_seed,
            entry.threshold_policy,
            entry.experiment_id,
        )
    )
    return entry


def _require_descriptive_scientific_metadata(values: tuple[str, ...]) -> None:
    for column, value in zip(_SCIENTIFIC_METADATA_COLUMNS, values, strict=True):
        normalized = value.casefold()
        if fullmatch(r"b\d+", normalized) or fullmatch(r"population[-_ ]?[a-z]", normalized):
            raise ArtifactIntegrityError(
                ErrorMessage(f"release manifest contains a retired opaque identity in {column}")
            )


def _require_relative_artifact_path(relative_path: Path) -> None:
    if (
        relative_path == Path(".")
        or relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.name
        in {
            _MANIFEST_FILENAME,
            _SIDECAR_FILENAME,
        }
    ):
        raise ArtifactIntegrityError(ErrorMessage("release manifest contains an invalid artifact path"))


def _required_value(row: dict[str, str | None], column: str) -> str:
    value = row.get(column)
    if value is None or value == "":
        raise ArtifactIntegrityError(ErrorMessage(f"release manifest field is missing: {column}"))
    return value


def _validate_manifest_files(root: Path, entries: tuple[ReleaseManifestEntry, ...]) -> None:
    links = tuple(path.relative_to(root) for path in root.rglob("*") if path.is_symlink())
    if links:
        raise ArtifactIntegrityError(
            ErrorMessage("release bundle must not contain symbolic links: " + ",".join(str(path) for path in links))
        )
    listed = frozenset(entry.relative_path for entry in entries)
    actual = frozenset(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and path.name not in {_MANIFEST_FILENAME, _SIDECAR_FILENAME}
    )
    if listed != actual:
        raise ArtifactIntegrityError(
            ErrorMessage(
                "release manifest inventory mismatch: "
                f"missing={','.join(str(path) for path in sorted(actual - listed)) or 'none'}; "
                f"unexpected={','.join(str(path) for path in sorted(listed - actual)) or 'none'}"
            )
        )
    represented_directories = frozenset(
        entry.relative_path.parts[0]
        for entry in entries
        if entry.relative_path.parts and entry.relative_path.parts[0] in _REQUIRED_RECONSTRUCTION_DIRECTORIES
    )
    missing_evidence = tuple(sorted(_REQUIRED_RECONSTRUCTION_DIRECTORIES - represented_directories))
    if missing_evidence:
        raise ArtifactIntegrityError(
            ErrorMessage(
                "release manifest is missing required reconstruction evidence directories: "
                + ",".join(missing_evidence)
            )
        )
    _validate_publication_output_inventory(root, entries)
    for entry in entries:
        path = root / entry.relative_path
        if not _is_regular_file(path):
            raise ArtifactIntegrityError(ErrorMessage(f"release artifact is not a regular file: {entry.relative_path}"))
        if path.stat().st_size != entry.byte_count:
            raise ArtifactIntegrityError(ErrorMessage(f"release artifact byte count mismatch: {entry.relative_path}"))
        if _sha256_file(path) != entry.digest:
            raise ArtifactIntegrityError(ErrorMessage(f"release artifact digest mismatch: {entry.relative_path}"))


def _validate_publication_output_inventory(root: Path, entries: tuple[ReleaseManifestEntry, ...]) -> None:
    """Require every published figure/table source chain to be explicitly reconstructable."""

    artifact_types = frozenset(entry.artifact_type for entry in entries)
    missing_types = tuple(sorted(_REQUIRED_PUBLICATION_ARTIFACT_TYPES - artifact_types))
    if missing_types:
        raise ArtifactIntegrityError(
            ErrorMessage("release manifest is missing publication output artifacts: " + ",".join(missing_types))
        )
    listed = frozenset(entry.relative_path for entry in entries)
    entries_by_path = {entry.relative_path: entry for entry in entries}
    manifests = tuple(entry for entry in entries if entry.artifact_type == "publication_source_manifest")
    publications = frozenset(entry.relative_path for entry in entries if entry.artifact_type == "publication")
    declared_publications: set[Path] = set()
    for manifest in manifests:
        if manifest.relative_path.parts[:1] != ("FIGURE_TABLE_DATA",):
            raise ArtifactIntegrityError(ErrorMessage("publication source manifest is outside FIGURE_TABLE_DATA"))
        try:
            payload = json.loads((root / manifest.relative_path).read_text(encoding="utf-8"))
            publication_name = payload["publication"]
            sources = payload["sources"]
        except (OSError, ValueError, KeyError) as error:
            raise ArtifactIntegrityError(
                ErrorMessage(f"released publication source manifest is unreadable: {manifest.relative_path}")
            ) from error
        if not isinstance(publication_name, str) or not isinstance(sources, list) or not sources:
            raise ArtifactIntegrityError(
                ErrorMessage(f"released publication source manifest is incomplete: {manifest.relative_path}")
            )
        publication = manifest.relative_path.parent / publication_name
        publication_path = Path(publication_name)
        if (
            publication_path.is_absolute()
            or ".." in publication_path.parts
            or len(publication_path.parts) != 1
            or publication not in publications
        ):
            raise ArtifactIntegrityError(
                ErrorMessage(
                    f"released publication source manifest has no listed publication: {manifest.relative_path}"
                )
            )
        declared_publications.add(publication)
        _validate_declared_publication(root / manifest.relative_path, payload, root / publication)
        declared_sources: set[Path] = set()
        for source in sources:
            if not isinstance(source, dict) or not isinstance(filename := source.get("filename"), str):
                raise ArtifactIntegrityError(
                    ErrorMessage(
                        f"released publication source manifest has an invalid source: {manifest.relative_path}"
                    )
                )
            source_path = Path(filename)
            resolved = manifest.relative_path.parent / source_path
            if (
                source_path.is_absolute()
                or ".." in source_path.parts
                or len(source_path.parts) != 1
                or resolved not in listed
                or entries_by_path[resolved].artifact_type != "table_figure_source_data"
            ):
                raise ArtifactIntegrityError(
                    ErrorMessage(
                        "released publication source is missing, invalid, or not retained as "
                        f"table/figure source data: {manifest.relative_path} / {filename}"
                    )
                )
            _validate_declared_publication_source(
                root / manifest.relative_path,
                source,
                root / resolved,
            )
            declared_sources.add(resolved)
        if len(declared_sources) != len(sources):
            raise ArtifactIntegrityError(
                ErrorMessage(f"released publication source manifest repeats a source: {manifest.relative_path}")
            )
    if publications != declared_publications:
        raise ArtifactIntegrityError(ErrorMessage("every released publication must have exactly one source manifest"))


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _release_artifact_metadata(artifact: ReleaseArtifact) -> tuple[Path, str, str, str, str, str, str, str]:
    return (
        artifact.relative_path,
        artifact.artifact_type,
        artifact.dataset_id,
        artifact.population_id,
        artifact.training_method,
        artifact.training_seed,
        artifact.threshold_policy,
        artifact.experiment_id,
    )


def _is_regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _is_regular_directory(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def main() -> None:
    """Validate an already-created reproducibility release outside the runtime CLI."""

    if len(argv) != 2:
        raise SystemExit("usage: python -m tools.reproducibility.release <release-root>")
    try:
        release = validate_release_bundle(Path(argv[1]))
    except (ArtifactIntegrityError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"release={release.root}")
    print(f"artifacts={len(release.entries)}")


if __name__ == "__main__":
    main()
