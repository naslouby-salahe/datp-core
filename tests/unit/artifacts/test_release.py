import csv
from datetime import date
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from tools.reproducibility import release
from tools.reproducibility.release import (
    ReleaseArtifact,
    ReleaseBuildRequest,
    ReleaseState,
    WithheldReleaseArtifact,
    build_release_bundle,
    campaign_analysis_release_artifacts,
    campaign_bounded_training_release_artifacts,
    campaign_evaluation_release_artifacts,
    campaign_publication_release_artifacts,
    campaign_release_artifacts,
    campaign_standard_training_release_artifacts,
    campaign_threshold_release_artifacts,
    preparation_release_artifacts,
    validate_release_bundle,
)

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import (
    CoordinateStableKey,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.core.numeric import Seed

_DIRECTORIES = (
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
_COLUMNS = (
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


def _release(root: Path) -> Path:
    for directory in _DIRECTORIES:
        (root / directory).mkdir(parents=True)
    artifacts = {
        "ROADMAP_LOCK.md": b"roadmap snapshot\n\n- Release state: `PUBLIC`\n",
        "SEEDS.csv": b"seed,purpose\n0,training\n",
        "README_REPRODUCIBILITY.md": b"reproduce\n",
        "METRICS/metrics.csv": b"metric,value\nfpr,0.05\n",
    }
    for relative_path, content in artifacts.items():
        (root / relative_path).write_bytes(content)
    manifest = root / "MANIFEST_SHA256.csv"
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=_COLUMNS)
        writer.writeheader()
        for relative_path, content in artifacts.items():
            writer.writerow(
                {
                    "relative_path": relative_path,
                    "sha256": sha256(content).hexdigest(),
                    "bytes": len(content),
                    "artifact_type": "metadata",
                    "dataset_id": "NA",
                    "population_id": "NA",
                    "training_method": "NA",
                    "training_seed": "NA",
                    "threshold_policy": "NA",
                    "experiment_id": "NA",
                }
            )
    (root / "MANIFEST_SHA256.sha256").write_text(
        f"{sha256(manifest.read_bytes()).hexdigest()}  MANIFEST_SHA256.csv\n",
        encoding="utf-8",
    )
    return root


def test_release_validation_accepts_complete_exact_inventory(tmp_path: Path) -> None:
    release = validate_release_bundle(_release(tmp_path))

    assert len(release.entries) == 4


def test_release_validation_rejects_unlisted_and_mutated_artifacts(tmp_path: Path) -> None:
    root = _release(tmp_path)
    (root / "METRICS" / "extra.csv").write_text("unlisted\n", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="inventory mismatch"):
        validate_release_bundle(root)

    (root / "METRICS" / "extra.csv").unlink()
    (root / "METRICS" / "metrics.csv").write_text("mutated\n", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="byte count mismatch"):
        validate_release_bundle(root)


def test_release_validation_rejects_an_invalid_manifest_sidecar(tmp_path: Path) -> None:
    root = _release(tmp_path)
    (root / "MANIFEST_SHA256.sha256").write_text("invalid\n", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="sidecar"):
        validate_release_bundle(root)


def test_release_builder_packages_explicit_retained_evidence_and_validates_it(tmp_path: Path) -> None:
    roadmap = tmp_path / "roadmap.md"
    source = tmp_path / "source.json"
    roadmap.write_text("authoritative roadmap\n", encoding="utf-8")
    source.write_text('{"metric": 0.05}\n', encoding="utf-8")

    release = build_release_bundle(
        ReleaseBuildRequest(
            root=tmp_path / "release",
            roadmap=roadmap,
            code_revision="deadbeef",
            literature_search_date=date(2026, 8, 13),
            state=ReleaseState.BLINDED_ARCHIVE,
            confirmatory_seeds=tuple(range(10)),
            artifacts=(
                ReleaseArtifact(
                    source=source,
                    relative_path=Path("METRICS/confirmatory.json"),
                    artifact_type="metric_table",
                    dataset_id="nbaiot",
                    population_id="nbaiot_natural_devices",
                    training_method="fedavg_autoencoder",
                    experiment_id="shared_vs_local_confirmation",
                ),
            ),
        )
    )

    assert len(release.entries) == 5
    assert (release.root / "METRICS" / "confirmatory.json").read_bytes() == source.read_bytes()
    readme = (release.root / "README_REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "python -m tools.reproducibility.release" in readme
    assert "datp-core validate-release" not in readme
    environment = (release.root / "ENVIRONMENT" / "runtime.txt").read_text(encoding="utf-8")
    for key in (
        "python=",
        "os_kernel=",
        "host_identifier=",
        "cpu_model=",
        "ram_bytes=",
        "gpu_model=",
        "gpu_count=",
        "cuda_runtime=",
        "gpu_driver=",
        "cudnn_version=",
        "dependency.torch=",
        "dependency.flwr=",
    ):
        assert key in environment


def test_license_restricted_release_requires_and_records_withheld_artifacts(tmp_path: Path) -> None:
    roadmap = tmp_path / "roadmap.md"
    withheld_source = tmp_path / "licensed_scores.parquet"
    roadmap.write_text("roadmap\n", encoding="utf-8")
    withheld_source.write_text("restricted", encoding="utf-8")
    request = ReleaseBuildRequest(
        root=tmp_path / "release",
        roadmap=roadmap,
        code_revision="deadbeef",
        literature_search_date=date(2026, 8, 13),
        state=ReleaseState.WITHHELD_LICENSE_RESTRICTED,
        confirmatory_seeds=tuple(range(10)),
        artifacts=(),
        withheld_artifacts=(
            WithheldReleaseArtifact(
                source=withheld_source,
                original_relative_path=Path("SCORES/nbaiot/licensed_scores.parquet"),
                license_reason="third-party dataset license",
                reconstruction_instructions="obtain the licensed source data and rerun the locked coordinate",
            ),
        ),
    )

    release = build_release_bundle(request)

    record = (release.root / "DATA_PROVENANCE" / "withheld_artifacts.csv").read_text(encoding="utf-8")
    assert "licensed_scores.parquet" in record
    assert sha256(b"restricted").hexdigest() in record
    assert not (release.root / "SCORES" / "nbaiot" / "licensed_scores.parquet").exists()
    (release.root / "DATA_PROVENANCE" / "withheld_artifacts.csv").write_text("invalid\n", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="withheld artifact record columns"):
        validate_release_bundle(release.root)


def test_release_evaluation_metadata_is_derived_from_the_persisted_coordinate(tmp_path: Path) -> None:
    document = cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            score_coordinate=SimpleNamespace(
                population=PopulationId.NBAIOT_NATURAL_DEVICES,
                model=TrainingModelId.FEDAVG_AUTOENCODER,
                training_seed=Seed(4),
            ),
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            execution_key=CoordinateStableKey("shared_vs_local_confirmation/coordinate"),
            execution_coordinate=SimpleNamespace(experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION),
        ),
    )

    artifact = release._release_artifact_from_document(
        tmp_path / "evaluation.json", Path("METRICS/evaluation.json"), document
    )

    assert artifact.dataset_id == "nbaiot"
    assert artifact.population_id == "nbaiot_natural_devices"
    assert artifact.training_seed == "4"
    assert artifact.threshold_policy == "local_threshold"
    assert artifact.experiment_id == "shared_vs_local_confirmation"


def test_campaign_release_discovery_rejects_output_roots_without_evaluation_evidence(tmp_path: Path) -> None:
    with pytest.raises(ArtifactIntegrityError, match="requires persisted evaluation documents"):
        campaign_evaluation_release_artifacts(tmp_path)


def test_campaign_threshold_release_discovery_requires_same_coordinate_evaluation(tmp_path: Path) -> None:
    result = tmp_path / "coordinate" / "threshold" / "threshold_result.json"
    result.parent.mkdir(parents=True)
    result.write_text("{}", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="no sibling evaluation evidence"):
        campaign_threshold_release_artifacts(tmp_path)


def test_campaign_threshold_release_discovery_inherits_evaluation_coordinate_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "coordinate"
    result = root / "threshold" / "threshold_result.json"
    temporal = result.parent / "temporal_threshold_provenance.json"
    evaluation = root / "evaluation" / "federated_evaluation.json"
    result.parent.mkdir(parents=True)
    evaluation.parent.mkdir()
    result.write_text("{}", encoding="utf-8")
    temporal.write_text("{}", encoding="utf-8")
    evaluation.write_text("{}", encoding="utf-8")
    coordinate_artifact = ReleaseArtifact(
        source=evaluation,
        relative_path=Path("METRICS/coordinate/evaluation/federated_evaluation.json"),
        artifact_type="federated_evaluation_document",
        dataset_id="nbaiot",
        population_id="nbaiot_natural_devices",
        training_method="fedavg_autoencoder",
        training_seed="4",
        threshold_policy="local_threshold",
        experiment_id="shared_vs_local_confirmation",
    )
    monkeypatch.setattr(release, "release_artifact_from_evaluation", lambda *_: coordinate_artifact)

    artifacts = campaign_threshold_release_artifacts(tmp_path)

    assert tuple(item.artifact_type for item in artifacts) == ("threshold_result", "temporal_threshold_provenance")
    assert all(item.training_seed == "4" for item in artifacts)
    assert all(item.experiment_id == "shared_vs_local_confirmation" for item in artifacts)


def test_standard_training_release_discovery_requires_coordinate_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluation = tmp_path / "experiment" / "evaluation" / "federated_evaluation.json"
    evaluation.parent.mkdir(parents=True)
    evaluation.write_text("{}", encoding="utf-8")
    training = tmp_path / "federated-training"
    training.mkdir()
    document = cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            score_coordinate=SimpleNamespace(), clients=(), threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD
        ),
    )
    monkeypatch.setattr(release, "_load_evaluation_document", lambda _: document)
    monkeypatch.setattr(release, "federated_training_directory", lambda *_: training)
    monkeypatch.setattr(
        release,
        "_release_artifact_from_document",
        lambda source, relative, _: ReleaseArtifact(source, relative, "evaluation", training_seed="4"),
    )

    with pytest.raises(ArtifactIntegrityError, match="coordinate release artifact is missing"):
        campaign_standard_training_release_artifacts(tmp_path)


def test_standard_training_release_discovery_retains_models_history_and_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluation = tmp_path / "experiment" / "evaluation" / "federated_evaluation.json"
    evaluation.parent.mkdir(parents=True)
    evaluation.write_text("{}", encoding="utf-8")
    training = tmp_path / "federated-training"
    client = "device_a"
    for name in ("terminal_model.safetensors", "round_summary.parquet", "client_rounds.parquet", "device_name.txt"):
        (training / name).parent.mkdir(parents=True, exist_ok=True)
        (training / name).write_text(name, encoding="utf-8")
    for name in ("calibration.parquet", "evaluation.parquet"):
        path = training / "scores" / client / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    document = cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            score_coordinate=SimpleNamespace(),
            clients=(SimpleNamespace(client=SimpleNamespace(client_id=SimpleNamespace(value=client))),),
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
    )
    coordinate = ReleaseArtifact(evaluation, Path("METRICS/evaluation.json"), "evaluation", training_seed="4")
    monkeypatch.setattr(release, "_load_evaluation_document", lambda _: document)
    monkeypatch.setattr(release, "federated_training_directory", lambda *_: training)
    monkeypatch.setattr(release, "_release_artifact_from_document", lambda *_: coordinate)

    artifacts = campaign_standard_training_release_artifacts(tmp_path)

    assert tuple(item.artifact_type for item in artifacts) == (
        "terminal_model",
        "training_history",
        "training_history",
        "training_history",
        "score_artifact",
        "score_artifact",
    )
    assert all(item.training_seed == "4" for item in artifacts)


def test_bounded_training_release_discovery_uses_persisted_execution_coordinate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluation = tmp_path / "experiment" / "evaluation" / "federated_evaluation.json"
    evaluation.parent.mkdir(parents=True)
    evaluation.write_text("{}", encoding="utf-8")
    training = tmp_path / "bounded-training" / "training"
    client = "device_a"
    for name in ("terminal_model.safetensors", "round_summary.parquet", "client_rounds.parquet", "device_name.txt"):
        path = training / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    for name in ("calibration.parquet", "evaluation.parquet"):
        path = training / "scores" / client / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
    execution_coordinate = SimpleNamespace(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        temporal_state=None,
        training_seed=Seed(4),
    )
    document = cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            score_coordinate=SimpleNamespace(),
            execution_coordinate=execution_coordinate,
            clients=(SimpleNamespace(client=SimpleNamespace(client_id=SimpleNamespace(value=client))),),
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        ),
    )
    coordinate = ReleaseArtifact(evaluation, Path("METRICS/evaluation.json"), "evaluation", training_seed="4")
    monkeypatch.setattr(release, "_load_evaluation_document", lambda _: document)
    monkeypatch.setattr(release, "bounded_evidence_seed_directory", lambda *_: training.parent)
    monkeypatch.setattr(release, "_release_artifact_from_document", lambda *_: coordinate)

    artifacts = campaign_bounded_training_release_artifacts(tmp_path)

    assert len(artifacts) == 6
    assert all(item.training_seed == "4" for item in artifacts)


def test_preparation_release_discovery_retains_only_declared_metadata(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    canonical = data_root / "canonical" / "nbaiot"
    processed = data_root / "processed" / "nbaiot" / "coordinate"
    canonical.mkdir(parents=True)
    processed.mkdir(parents=True)
    (canonical / "dataset_manifest.json").write_text("{}", encoding="utf-8")
    (canonical / "part-00000.parquet").write_text("raw-like rows", encoding="utf-8")
    (processed / "preprocessing_manifest.json").write_text("{}", encoding="utf-8")
    (processed / "state.skops").write_text("state", encoding="utf-8")
    (processed / "split_manifest.parquet").write_text("split", encoding="utf-8")
    (processed / "train.parquet").write_text("processed rows", encoding="utf-8")

    artifacts = preparation_release_artifacts(data_root)

    assert tuple(item.relative_path for item in artifacts) == (
        Path("DATA_PROVENANCE/canonical/nbaiot/dataset_manifest.json"),
        Path("PREPROCESSING/nbaiot/coordinate/preprocessing_manifest.json"),
        Path("SPLIT_IDENTITY/nbaiot/coordinate/split_manifest.parquet"),
        Path("PREPROCESSING/nbaiot/coordinate/state.skops"),
    )


def test_campaign_analysis_release_discovery_retains_only_declared_derived_evidence(tmp_path: Path) -> None:
    analysis = tmp_path / "experiment" / "analysis" / "summary.json"
    diagnostic = tmp_path / "anchor" / "diagnostics" / "gate.json"
    report = tmp_path / "experiment" / "analysis_report.md"
    ignored = tmp_path / "experiment" / "scores" / "calibration.parquet"
    for path in (analysis, diagnostic, report, ignored):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.name, encoding="utf-8")

    artifacts = campaign_analysis_release_artifacts(tmp_path)

    assert tuple(item.relative_path for item in artifacts) == (
        Path("AUDIT_REPORTS/anchor/diagnostics/gate.json"),
        Path("STATISTICS/experiment/analysis/summary.json"),
        Path("AUDIT_REPORTS/experiment/analysis_report.md"),
    )


def test_campaign_release_assembly_requires_unique_destinations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    artifact = ReleaseArtifact(source, Path("METRICS/evidence.json"), "evidence")
    for mapper in (
        "preparation_release_artifacts",
        "campaign_evaluation_release_artifacts",
        "campaign_threshold_release_artifacts",
        "campaign_standard_training_release_artifacts",
        "campaign_bounded_training_release_artifacts",
        "campaign_analysis_release_artifacts",
        "campaign_publication_release_artifacts",
    ):
        monkeypatch.setattr(release, mapper, lambda *_: (artifact,))

    with pytest.raises(ArtifactIntegrityError, match="destinations must be unique"):
        campaign_release_artifacts(tmp_path, tmp_path)


def test_campaign_publication_release_discovery_requires_the_rendered_publication(tmp_path: Path) -> None:
    manifest = tmp_path / "analysis" / "publication_source_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"sources": [{"filename": "publication_source_data.csv"}]}', encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="has no publication"):
        campaign_publication_release_artifacts(tmp_path)

    publication = manifest.parent / "publication.md"
    publication.write_text("# results\n", encoding="utf-8")
    source_data = manifest.parent / "publication_source_data.csv"
    source_data.write_text("metric,value\nfpr,0.05\n", encoding="utf-8")
    artifacts = campaign_publication_release_artifacts(tmp_path)
    assert tuple(item.relative_path for item in artifacts) == (
        Path("FIGURE_TABLE_DATA/analysis/publication_source_manifest.json"),
        Path("FIGURE_TABLE_DATA/analysis/publication.md"),
        Path("FIGURE_TABLE_DATA/analysis/publication_source_data.csv"),
    )


def test_campaign_publication_release_discovery_rejects_missing_declared_source(tmp_path: Path) -> None:
    manifest = tmp_path / "analysis" / "publication_source_manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"sources": [{"filename": "missing.csv"}]}', encoding="utf-8")
    (manifest.parent / "publication.md").write_text("# results\n", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError, match="source is missing or invalid"):
        campaign_publication_release_artifacts(tmp_path)
