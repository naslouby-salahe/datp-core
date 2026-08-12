from types import SimpleNamespace
from typing import cast

from tests.unit.learning.federated.helpers import client_identity

from datp_core.analysis.mechanisms.support_strata import (
    CalibrationSupportStratum,
    campaign_fixed_support_strata,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.identifiers import AvailabilityStatus, PopulationId
from datp_core.core.numeric import RowCount, Seed
from datp_core.data.populations.contracts import ClientIdentity


def test_campaign_fixed_support_strata_uses_seed_median_then_canonical_client_id() -> None:
    clients = tuple(client_identity(f"client_{index}") for index in range(9))
    first = _document(seed=1, clients=clients, counts=tuple(range(10, 100, 10)))
    second = _document(seed=2, clients=clients, counts=tuple(range(11, 101, 10)))

    strata = campaign_fixed_support_strata((first, second))

    assert strata.availability is AvailabilityStatus.AVAILABLE
    assert tuple(entry.stratum for entry in strata.entries[:3]) == (CalibrationSupportStratum.LOW_SUPPORT,) * 3
    assert tuple(entry.stratum for entry in strata.entries[3:6]) == (CalibrationSupportStratum.MID_SUPPORT,) * 3
    assert tuple(entry.stratum for entry in strata.entries[6:]) == (CalibrationSupportStratum.HIGH_SUPPORT,) * 3
    assert strata.entries[0].support_score.value == 10.5


def test_campaign_fixed_support_strata_refuses_non_nine_device_population() -> None:
    document = _document(seed=1, clients=(client_identity("client_a"),), counts=(10,))

    strata = campaign_fixed_support_strata((document,))

    assert strata.availability is AvailabilityStatus.UNAVAILABLE
    assert strata.entries == ()


def _document(
    *, seed: int, clients: tuple[ClientIdentity, ...], counts: tuple[int, ...]
) -> FederatedEvaluationDocument:
    return cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            score_coordinate=SimpleNamespace(population=PopulationId.NBAIOT_NATURAL_DEVICES, training_seed=Seed(seed)),
            diagnostics=SimpleNamespace(
                calibration_support=tuple(
                    SimpleNamespace(client=client, source_benign_calibration_count=RowCount(count))
                    for client, count in zip(clients, counts, strict=True)
                )
            ),
        ),
    )
