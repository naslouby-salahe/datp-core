import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.threshold_estimation import ThresholdEstimationProvenance
from datp_core.analysis.metrics.threshold_evidence import verify_held_out_benign_scores
from datp_core.core.errors import ScientificContractError
from datp_core.core.numeric import CalibrationSize, Quantile, ReplicateIndex, Seed


def test_threshold_estimation_rejects_an_empty_held_out_benign_score_set() -> None:
    provenance = ThresholdEstimationProvenance(
        client_identity("client_a"),
        fedavg_coordinate(Seed(5)),
        Seed(5),
        CalibrationSize(10),
        ReplicateIndex(0),
        Quantile(0.9),
    )

    with pytest.raises(ScientificContractError, match="non-empty"):
        verify_held_out_benign_scores(
            client=provenance.client,
            coordinate=provenance.coordinate,
            scores=(),
        )
