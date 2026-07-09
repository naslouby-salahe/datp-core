"""Tiny deterministic manifest fixture (docs/protocol/artifact_contracts.md #2)."""

from __future__ import annotations

from datp_core.domain.datasets import DatasetId
from datp_core.domain.partitions import SplitRole
from datp_core.domain.regimes import Regime
from datp_core.experiments.provenance import ArtifactCommon, ArtifactStatus, ScoreManifest


def tiny_score_manifest() -> ScoreManifest:
    return ScoreManifest(
        manifest_id="fixture-score-1",
        dataset_id=DatasetId.N_BAIOT,
        regime=Regime.A,
        seed=0,
        checkpoint_manifest_id="fixture-ckpt-1",
        split_role=SplitRole.CALIBRATION,
        common=ArtifactCommon(
            artifact_path="outputs/scores/fixture-score-1.json",
            created_at="2026-01-01T00:00:00Z",
            code_version="phase1-fixture",
            status=ArtifactStatus.COMPLETE,
        ),
    )
