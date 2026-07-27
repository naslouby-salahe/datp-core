"""Unit tests for persistence."""

from __future__ import annotations

from unittest.mock import MagicMock

from datp_core.analysis.contracts import FederatedProximalLossObservation, FederatedProximalSelectionResult
from datp_core.analysis.enums import AnalysisResultKind
from datp_core.analysis.runtime.persistence import _adapter, persist_analysis_results
from datp_core.artifacts.store import ArtifactStore
from datp_core.core.identifiers import AnalysisLabel
from datp_core.pipeline.stages.jobs import StageJob


def test_persist_analysis_results() -> None:

    store = MagicMock(spec=ArtifactStore)
    job = MagicMock(spec=StageJob)
    job.output_path.return_value = "results/statistical_result.json"

    result = FederatedProximalSelectionResult(
        analysis_label=AnalysisLabel("sel"),
        selected_proximal_mu=0.05,
        locked_primary_round=5,
        calibration_losses=(FederatedProximalLossObservation(proximal_mu=0.05, mean_benign_calibration_loss=0.02),),
    )

    persist_analysis_results(store=store, job=job, results=[result])

    store.write_bytes_atomic.assert_called_once()
    called_path, called_payload = store.write_bytes_atomic.call_args[0]
    assert called_path == "results/statistical_result.json"

    decoded = _adapter.validate_json(called_payload)
    assert isinstance(decoded, tuple)
    assert len(decoded) == 1
    assert decoded[0].result_kind == AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION
    assert decoded[0].payload_version == 1
