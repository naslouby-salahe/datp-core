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
    build_release_bundle,
    campaign_evaluation_release_artifacts,
    campaign_publication_release_artifacts,
    campaign_threshold_release_artifacts,
    validate_release_bundle,
)

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.errors import ArtifactIntegrityError
from datp_core.core.identifiers import CoordinateStableKey, FederatedThresholdMethod, PopulationId, TrainingModelId
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
        "ROADMAP_LOCK.md": b"roadmap snapshot\n",
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
