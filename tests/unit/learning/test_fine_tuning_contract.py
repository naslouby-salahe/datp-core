from tests.unit.learning.federated.helpers import client_identity

from datp_core.core.identifiers import DatasetId
from datp_core.core.numeric import Seed
from datp_core.detector.training.engine import derive_fedavg_local_fine_tuning_seed


def test_fine_tuning_seed_is_stable_per_client_and_distinct_between_clients() -> None:
    first = client_identity("client_1")
    second = client_identity("client_2")

    assert derive_fedavg_local_fine_tuning_seed(
        DatasetId.NBAIOT, Seed(7), first
    ) == derive_fedavg_local_fine_tuning_seed(DatasetId.NBAIOT, Seed(7), first)
    assert derive_fedavg_local_fine_tuning_seed(
        DatasetId.NBAIOT, Seed(7), first
    ) != derive_fedavg_local_fine_tuning_seed(DatasetId.NBAIOT, Seed(7), second)
