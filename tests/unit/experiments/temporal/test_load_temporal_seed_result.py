from pathlib import Path

import pytest

from datp_core.core.errors import ReportEvidenceError
from datp_core.core.identifiers import FederatedThresholdMethod, TemporalState
from datp_core.core.numeric import Seed
from datp_core.experiments.temporal import load_temporal_seed_result
from datp_core.experiments.temporal.run import _temporal_coordinates, _temporal_declaration


def test_load_temporal_seed_result_fails_explicitly_without_persisted_evaluations(tmp_path: Path) -> None:
    with pytest.raises(ReportEvidenceError):
        load_temporal_seed_result(Seed(0), output_root=tmp_path)


def test_temporal_state_keeps_method_specific_execution_coordinates() -> None:
    coordinates = _temporal_coordinates(Seed(0), _temporal_declaration())

    shared = coordinates.for_state_method(TemporalState.FROZEN_FUTURE, FederatedThresholdMethod.SHARED_THRESHOLD)
    local = coordinates.for_state_method(TemporalState.FROZEN_FUTURE, FederatedThresholdMethod.LOCAL_THRESHOLD)

    assert shared.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD
    assert local.threshold_method is FederatedThresholdMethod.LOCAL_THRESHOLD
    assert shared.execution_key != local.execution_key
    assert shared.dataset is local.dataset
    assert shared.population is local.population
    assert shared.split_protocol is local.split_protocol
    assert shared.preprocessing_protocol is local.preprocessing_protocol
    assert shared.training_model is local.training_model
