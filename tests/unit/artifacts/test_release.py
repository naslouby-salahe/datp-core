import csv
from hashlib import sha256
from pathlib import Path

import pytest

from datp_core.artifacts.release import validate_release_bundle
from datp_core.core.errors import ArtifactIntegrityError

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
