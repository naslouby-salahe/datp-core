import numpy as np
import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate
from tests.unit.thresholding.helpers import client_scores

from datp_core.analysis.metrics.threshold_estimation import ThresholdEstimationProvenance
from datp_core.analysis.metrics.threshold_evidence import verify_held_out_benign_scores
from datp_core.core.errors import ScientificContractError
from datp_core.core.numeric import CalibrationSize, Quantile, ReplicateIndex, Seed
from datp_core.experiments.execution.workspace import _pooled_calibration_quantile
from datp_core.thresholds.quantiles import exact_empirical_quantile


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


def test_threshold_estimation_oracle_pools_only_eligible_calibration_scores() -> None:
    scores_a = client_scores("client_a", (0.1, 0.2, 0.3))
    scores_b = client_scores("client_b", (0.4, 0.5))
    calibration_by_client = {scores_a.client: scores_a, scores_b.client: scores_b}
    quantile = Quantile(0.9)
    oracle = _pooled_calibration_quantile(calibration_by_client, quantile)
    pooled_calibration = np.asarray((0.1, 0.2, 0.3, 0.4, 0.5), dtype=np.float64)
    assert oracle == exact_empirical_quantile(pooled_calibration, quantile)
    # Held-out evaluation scores must never shape the estimator oracle (II-02);
    # the helper only ever consumes eligible benign calibration evidence.
    assert oracle.value != exact_empirical_quantile(np.asarray((99.0, 98.0), dtype=np.float64), quantile).value
