"""Unit tests for AnalysisArtifactRepository."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import datp_core.analysis.runtime.artifacts as artifacts_module
from datp_core.analysis.errors import ArtifactMissingError
from datp_core.analysis.runtime.artifacts import AnalysisArtifactRepository, _ArtifactPathIndex
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates, StageInput


def test_no_analysis_input_bundle_alias() -> None:
    assert not hasattr(artifacts_module, "AnalysisInputBundle")


def test_no_public_store_property() -> None:
    repo = AnalysisArtifactRepository(store=MagicMock())
    assert not hasattr(repo, "store")


def test_no_raw_path_methods_on_repository() -> None:
    repo = AnalysisArtifactRepository(store=MagicMock())
    assert not hasattr(repo, "threshold_frame")
    assert not hasattr(repo, "calibration_score_frame")
    assert not hasattr(repo, "test_score_frame")
    assert not hasattr(repo, "client_metric_frame")
    assert not hasattr(repo, "read_bytes")


def test_artifact_path_index_resolution() -> None:
    stage_input = MagicMock(spec=StageInput)
    stage_input.coordinates = AnalysisInputCoordinates(
        producer_stage=StageKind.THRESHOLD_CONSTRUCTION,
        output_name="thresholds",
        context=MagicMock(),
    )
    stage_input.relative_path = "output/thresholds.parquet"

    index = _ArtifactPathIndex.from_stage_inputs((stage_input,))
    path = index.resolve(
        producer_stage=StageKind.THRESHOLD_CONSTRUCTION,
        output_name="thresholds",
        context=stage_input.coordinates.context,
    )
    assert path == "output/thresholds.parquet"

    with pytest.raises(ArtifactMissingError):
        index.resolve(
            producer_stage=StageKind.MODEL_TRAINING,
            output_name="checkpoint",
            context=stage_input.coordinates.context,
        )
