"""Validates docs/protocol/reuse_policy.md (P0-T09)."""

import re
from pathlib import Path

DOC = Path(__file__).parents[2] / "docs" / "protocol" / "reuse_policy.md"

HEAVY_STAGES = {
    "Data preparation / preprocessing",
    "Client split manifest",
    "Model training (FedAvg / FedProx / personalized)",
    "Checkpoint selection / freeze",
    "Calibration/test score generation",
}

CHEAP_STAGES = {
    "Threshold computation (B0–B4)",
    "Threshold variants (q, τ-shrink, cal-size, B2-conf)",
    "Metric evaluation",
    "Statistical analysis (bootstrap, paired tests)",
    "Mechanism analyses",
    "Table export",
    "Figure export",
    "Claim mapping",
}


def _stage_rows() -> list[tuple[str, str]]:
    text = DOC.read_text()
    section = re.search(r"## Stage Classification.*?(?=\n## |\Z)", text, flags=re.DOTALL)
    assert section is not None
    rows = re.findall(r"^\| ([^|]+) \| (Heavy|Cheap) \|", section.group(0), flags=re.MULTILINE)
    return [(stage.strip(), cls) for stage, cls in rows]


def test_stage_classification_complete() -> None:
    rows = _stage_rows()
    stages_by_class = {"Heavy": set(), "Cheap": set()}
    for stage, cls in rows:
        stages_by_class[cls].add(stage)
    assert stages_by_class["Heavy"] == HEAVY_STAGES
    assert stages_by_class["Cheap"] == CHEAP_STAGES


def test_invalidation_triggers_listed() -> None:
    text = DOC.read_text()
    section = re.search(r"## Six Invalidation Triggers.*?(?=\n## |\Z)", text, flags=re.DOTALL)
    assert section is not None
    numbered = re.findall(r"^\d+\. ", section.group(0), flags=re.MULTILINE)
    assert len(numbered) == 6


def test_threshold_stage_not_marked_heavy() -> None:
    rows = _stage_rows()
    for stage, cls in rows:
        if stage.startswith("Threshold"):
            assert cls == "Cheap"
