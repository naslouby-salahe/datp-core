from types import SimpleNamespace
from typing import cast

import polars as pl
import pytest

from datp_core.analysis.temporal import temporal_drift_js
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ScoreFrameColumn, TemporalState
from datp_core.detector.scoring.models import FederatedScoreRecord


def test_temporal_state_names_do_not_claim_continuous_adaptation() -> None:
    assert all("continuous" not in state.value and "stream" not in state.value for state in TemporalState)


def test_temporal_drift_js_uses_unsmoothed_pooled_type7_quantile_bins(tmp_path) -> None:
    historical = tmp_path / "historical.parquet"
    future = tmp_path / "future.parquet"
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (0.0, 0.0, 0.0, 1.0)}).write_parquet(historical)
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (0.0, 1.0, 1.0, 1.0)}).write_parquet(future)
    client = object()

    divergence = temporal_drift_js(
        cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=historical)),
        cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=future)),
    )

    assert divergence.value == pytest.approx(0.18872187554086717)


def test_temporal_drift_js_blocks_a_collapsed_pooled_quantile_grid(tmp_path) -> None:
    historical = tmp_path / "historical.parquet"
    future = tmp_path / "future.parquet"
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (1.0, 1.0)}).write_parquet(historical)
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (1.0, 1.0)}).write_parquet(future)
    client = object()

    with pytest.raises(ScientificContractError, match="two nonzero-width pooled quantile bins"):
        temporal_drift_js(
            cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=historical)),
            cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=future)),
        )
