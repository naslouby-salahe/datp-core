"""Validates docs/protocol/artifact_contracts.md (P0-T05)."""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
DOC = ROOT / "docs" / "protocol" / "artifact_contracts.md"

ARTIFACT_CLASSES = [
    "Raw data",
    "Preprocessed data",
    "Split manifest",
    "Training checkpoints (in-progress)",
    "Frozen checkpoints",
    "Calibration scores",
    "Test scores",
    "Threshold artifacts",
    "Prediction artifacts",
    "Per-client metrics",
    "Per-seed metrics",
    "Bootstrap summaries",
    "Paired-test summaries",
    "Raw output tables",
    "Raw output figures",
    "Curated result tables",
    "Curated result figures",
    "Claim-evidence maps",
    "Run manifests",
    "Config snapshots",
]

REQUIRED_README_PATHS = [
    ROOT / "data" / "README.md",
    ROOT / "checkpoints" / "README.md",
    ROOT / "outputs" / "README.md",
    ROOT / "results" / "README.md",
]


def _artifact_table_rows() -> list[str]:
    text = DOC.read_text()
    section = re.search(r"## 2\. Pipeline Artifact Contracts.*?(?=\n## |\Z)", text, flags=re.DOTALL)
    assert section is not None
    rows = re.findall(r"^\| ([^|]+) \|", section.group(0), flags=re.MULTILINE)
    return [r.strip() for r in rows if r.strip() != "Artifact" and not r.strip().startswith("---")]


def test_every_artifact_has_manifest_fields() -> None:
    rows = _artifact_table_rows()
    assert rows == ARTIFACT_CLASSES


def test_readmes_exist() -> None:
    for path in REQUIRED_README_PATHS:
        assert path.exists(), f"missing {path}"


def test_results_excludes_heavy_artifacts() -> None:
    text = DOC.read_text()
    assert "`results/` excludes heavy artifacts" in text
