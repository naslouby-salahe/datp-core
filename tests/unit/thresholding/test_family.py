import pytest
from tests.unit.thresholding.helpers import client_scores, identity

from datp_core.domain.enums import AvailabilityStatus
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import FamilyIdentity, Quantile
from datp_core.thresholding.family import construct_family_threshold

QUANTILE = Quantile(0.5)
CLIENT_A = client_scores("client_a", (1.0, 2.0, 3.0))
CLIENT_B = client_scores("client_b", (10.0, 20.0, 30.0))
CLIENT_C = client_scores("client_c", (100.0, 200.0, 300.0))
DOORBELL = FamilyIdentity("doorbell")
WEBCAM = FamilyIdentity("webcam")
THERMOSTAT = FamilyIdentity("thermostat")


def test_construct_family_threshold_averages_eligible_local_thresholds_within_a_family() -> None:
    family_by_client = (
        (identity("client_a"), DOORBELL),
        (identity("client_b"), DOORBELL),
        (identity("client_c"), WEBCAM),
    )
    result = construct_family_threshold((CLIENT_A, CLIENT_B, CLIENT_C), QUANTILE, family_by_client)
    families = {family.family_id: family for family in result.families}
    doorbell_threshold = families[DOORBELL].family_threshold
    webcam_threshold = families[WEBCAM].family_threshold
    assert families[DOORBELL].status is AvailabilityStatus.AVAILABLE
    assert doorbell_threshold is not None
    assert doorbell_threshold.value == (2.0 + 20.0) / 2
    assert webcam_threshold is not None
    assert webcam_threshold.value == 200.0


def test_construct_family_threshold_marks_family_without_eligible_members_unavailable() -> None:
    family_by_client = (
        (identity("client_a"), DOORBELL),
        (identity("client_z"), THERMOSTAT),
    )
    result = construct_family_threshold((CLIENT_A,), QUANTILE, family_by_client)
    families = {family.family_id: family for family in result.families}
    assert families[THERMOSTAT].status is AvailabilityStatus.UNAVAILABLE
    assert families[THERMOSTAT].family_threshold is None
    assert not families[THERMOSTAT].members


def test_construct_family_threshold_rejects_empty_taxonomy() -> None:
    def call():
        return construct_family_threshold((CLIENT_A,), QUANTILE, ())

    with pytest.raises(ScientificContractError, match="non-empty family taxonomy"):
        call()


def test_construct_family_threshold_requires_at_least_one_eligible_client() -> None:
    family_by_client = ((identity("client_z"), DOORBELL),)

    def call():
        return construct_family_threshold((), QUANTILE, family_by_client)

    with pytest.raises(ScientificContractError, match="at least one eligible client"):
        call()


def test_construct_family_threshold_rejects_duplicate_eligible_clients() -> None:
    family_by_client = ((identity("client_a"), DOORBELL),)

    with pytest.raises(ScientificContractError, match="unique"):
        construct_family_threshold((CLIENT_A, CLIENT_A), QUANTILE, family_by_client)


def test_construct_family_threshold_rejects_missing_taxonomy_for_eligible_client() -> None:
    family_by_client = ((identity("client_b"), DOORBELL),)

    with pytest.raises(ScientificContractError, match="missing a family taxonomy entry"):
        construct_family_threshold((CLIENT_A,), QUANTILE, family_by_client)
