"""Shared miniature fixtures for thresholding unit tests."""

from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.core.numeric import ScoreValue, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedTrainingCoordinate
from datp_core.thresholds.quantiles import ClientBenignCalibrationScores

COORDINATE = fedavg_coordinate(Seed(0))


def client_scores(
    client_id: str,
    scores: tuple[float, ...],
    *,
    coordinate: FederatedTrainingCoordinate = COORDINATE,
) -> ClientBenignCalibrationScores:
    return ClientBenignCalibrationScores(
        client=client_identity(client_id),
        coordinate=coordinate,
        scores=tuple(ScoreValue(value) for value in scores),
    )


def identity(client_id: str) -> ClientIdentity:
    return client_identity(client_id)
