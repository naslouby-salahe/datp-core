"""Calibration stage exception handling: failed outcomes on error paths."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock

import polars as pl
import pytest

from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.enums import JobExecutionStatus, StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.thresholding.stages import CalibrationSubsamplingStageHandler


def _encode(frame: pl.DataFrame) -> bytes:
    buf = BytesIO()
    frame.write_parquet(buf)
    return buf.getvalue()


_VALID_FRAME = _encode(
    pl.DataFrame(
        {
            "client_id": ["c1", "c1", "c2"],
            "score": [0.1, 0.2, 0.3],
            "source_path": ["/a", "/a", "/b"],
            "source_row_index": [0, 1, 0],
        }
    )
)

_MISSING_COLUMNS_FRAME = _encode(
    pl.DataFrame(
        {
            "client_id": ["c1"],
            "score": [0.1],
        }
    )
)

_INSUFFICIENT_FRAME = _encode(
    pl.DataFrame(
        {
            "client_id": ["c1"],
            "score": [0.1],
            "source_path": ["/a"],
            "source_row_index": [0],
        }
    )
)


@pytest.fixture
def mock_store() -> MagicMock:
    store = MagicMock(spec=ArtifactStore)
    store.read_bytes.return_value = _VALID_FRAME
    return store


@pytest.fixture
def mock_config() -> MagicMock:
    cfg = MagicMock()
    experiment = MagicMock()
    subset = MagicMock()
    subset.selection_seed.value = 0
    experiment.calibration_subset = subset
    cfg.experiments.get.return_value = experiment
    namespace = MagicMock()
    namespace.key = "test_key"
    cfg.protocol_determinism.calibration_subsample_namespace = namespace
    cfg.protocol_determinism.derived_seed_digest_bytes = 8
    return cfg


@pytest.fixture
def mock_job() -> MagicMock:
    job = MagicMock(spec=StageJob)
    job.node_key.label = "test_node"
    job.stage = StageKind.CALIBRATION_SUBSAMPLING
    job.outputs = ()
    job.input_path.return_value = "scores/calibration.parquet"
    job.output_path.return_value = "scores/calibration_subset.parquet"

    ctx = MagicMock()
    ctx.experiment_id = "test_experiment"
    ctx.seed = 42
    ctx.calibration_sample_count = 10
    ctx.calibration_replicate = 1
    job.context = ctx
    return job


@pytest.fixture
def handler(mock_store: MagicMock, mock_config: MagicMock) -> CalibrationSubsamplingStageHandler:
    return CalibrationSubsamplingStageHandler(config=mock_config, store=mock_store)


def _assert_failed(outcome, *, store: MagicMock) -> None:
    assert outcome.status is JobExecutionStatus.FAILED
    assert outcome.error_message and len(outcome.error_message) > 0
    store.write_bytes_atomic.assert_not_called()


def test_invalid_sample_count_fails_cleanly(
    handler: CalibrationSubsamplingStageHandler, mock_store: MagicMock, mock_job: MagicMock
) -> None:
    mock_store.read_bytes.return_value = _INSUFFICIENT_FRAME
    mock_job.context.calibration_sample_count = 10
    outcome = handler.execute(mock_job)
    _assert_failed(outcome, store=mock_store)


def test_missing_required_columns_fails_cleanly(
    handler: CalibrationSubsamplingStageHandler, mock_store: MagicMock, mock_job: MagicMock
) -> None:
    mock_store.read_bytes.return_value = _MISSING_COLUMNS_FRAME
    outcome = handler.execute(mock_job)
    _assert_failed(outcome, store=mock_store)


def test_no_output_written_after_failure(
    handler: CalibrationSubsamplingStageHandler, mock_store: MagicMock, mock_job: MagicMock
) -> None:
    mock_store.read_bytes.return_value = _INSUFFICIENT_FRAME
    mock_job.context.calibration_sample_count = 10
    handler.execute(mock_job)
    mock_store.write_bytes_atomic.assert_not_called()


def test_invalid_replicate_fails_cleanly(
    handler: CalibrationSubsamplingStageHandler, mock_store: MagicMock, mock_job: MagicMock
) -> None:
    mock_job.context.calibration_replicate = -1
    outcome = handler.execute(mock_job)
    _assert_failed(outcome, store=mock_store)
