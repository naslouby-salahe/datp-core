"""Shared miniature fixtures for Phase 09 thresholding unit tests."""

from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.domain.values import Checksum, Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity
from datp_core.thresholding.quantiles import ClientBenignCalibrationScores

COORDINATE = fedavg_coordinate(Seed(0))
DEFAULT_CALIBRATION_MANIFEST_CHECKSUM = Checksum("c" * 64)
DEFAULT_SCORE_SET_CHECKSUM = Checksum("d" * 64)


def client_scores(
    client_id: str,
    scores: tuple[float, ...],
    *,
    coordinate: FederatedTrainingCoordinate = COORDINATE,
    calibration_manifest_checksum: Checksum = DEFAULT_CALIBRATION_MANIFEST_CHECKSUM,
    score_set_checksum: Checksum = DEFAULT_SCORE_SET_CHECKSUM,
) -> ClientBenignCalibrationScores:
    return ClientBenignCalibrationScores(
        client=client_identity(client_id),
        coordinate=coordinate,
        scores=scores,
        calibration_manifest_checksum=calibration_manifest_checksum,
        score_set_checksum=score_set_checksum,
    )


def identity(client_id: str) -> ClientIdentity:
    return client_identity(client_id)
