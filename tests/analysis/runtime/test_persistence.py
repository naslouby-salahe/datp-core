"""Unit tests for persistence."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from datp_core.analysis.contracts import FederatedProximalLossObservation, FederatedProximalSelectionResult
from datp_core.analysis.enums import AnalysisResultKind
from datp_core.analysis.runtime.persistence import persist_analysis_results
from datp_core.analysis.runtime.runner import register_analysis_capabilities
from datp_core.core.identifiers import AnalysisLabel


def test_persist_analysis_results() -> None:
    register_analysis_capabilities()

    store = MagicMock()
    job = MagicMock()
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

    decoded_envelopes = json.loads(called_payload.decode("utf-8"))
    assert isinstance(decoded_envelopes, list)
    assert len(decoded_envelopes) == 1
    assert decoded_envelopes[0]["result_kind"] == AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION.value
    assert decoded_envelopes[0]["payload_version"] == 1
