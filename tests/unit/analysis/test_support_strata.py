from types import SimpleNamespace
from typing import cast

import pytest
from tests.unit.learning.federated.helpers import client_identity

from datp_core.analysis.mechanisms import ThresholdMovementCohort
from datp_core.analysis.mechanisms.support_strata import (
    CalibrationSupportStratum,
    campaign_fixed_support_strata,
    summarize_support_stratum_campaign,
    support_stratum_seed_outcomes,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.identifiers import AvailabilityStatus, PopulationId
from datp_core.core.numeric import MetricValue, RowCount, Seed
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


def test_support_stratum_outcomes_use_fixed_three_client_membership() -> None:
    clients = tuple(client_identity(f"client_{index}") for index in range(9))
    shared = _document(seed=1, clients=clients, counts=tuple(range(10, 100, 10)))
    local = _document(seed=1, clients=clients, counts=tuple(range(10, 100, 10)))
    cast(SimpleNamespace, shared).diagnostics.held_out_operating_points = tuple(
        SimpleNamespace(client=client, absolute_target_error=MetricValue(0.2)) for client in clients
    )
    cast(SimpleNamespace, local).diagnostics.held_out_operating_points = tuple(
        SimpleNamespace(client=client, absolute_target_error=MetricValue(0.1)) for client in clients
    )
    strata = campaign_fixed_support_strata((shared,))
    cohort = cast(
        ThresholdMovementCohort,
        SimpleNamespace(
            movements=tuple(SimpleNamespace(client=client, delta_fpr=MetricValue(-0.1)) for client in clients)
        ),
    )

    report = support_stratum_seed_outcomes(strata, ((shared, local),), (cohort,))

    assert report.availability is AvailabilityStatus.AVAILABLE
    assert len(report.outcomes) == 3
    assert report.outcomes[0].mean_fpr_relief.value == pytest.approx(0.1)
    assert report.outcomes[0].shared_mean_absolute_target_error.value == pytest.approx(0.2)

    summary = summarize_support_stratum_campaign(report)

    assert summary.availability is AvailabilityStatus.AVAILABLE
    assert summary.summaries[0].mean_fpr_relief.arithmetic_mean.value == pytest.approx(0.1)


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
