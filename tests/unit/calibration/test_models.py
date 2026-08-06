import pytest
from tests.unit.calibration.helpers import some_client
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.calibration.models import (
    CalibrationReplicateManifest,
    CalibrationSampleReference,
    CalibrationSubsample,
    CalibrationSupport,
    CalibrationUnavailableReason,
    EligibilityDecision,
    EligibilityStatus,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import CalibrationSize, ReplicateIndex, RowCount, Seed
from datp_core.domain.values.identifiers import StableRowId
from datp_core.domain.values.ratios import ScoreValue

CLIENT_A = some_client("client_a")
CLIENT_B = some_client("client_b")
COORDINATE = fedavg_coordinate(Seed(0))
REPLICATE_ZERO = ReplicateIndex(0)


def _reference(client, row_id: str, value: float = 1.0) -> CalibrationSampleReference:
    return CalibrationSampleReference(client=client, stable_row_id=StableRowId(row_id), score=ScoreValue(value))


def _support(count: int) -> CalibrationSupport:
    return CalibrationSupport(
        client=CLIENT_A,
        coordinate=COORDINATE,
        benign_calibration_count=RowCount(count),
        calibration_score_set_checksum=Checksum("a" * 64),
    )


def _subsample(size: int, row_ids: tuple[str, ...]) -> CalibrationSubsample:
    return CalibrationSubsample(
        size=CalibrationSize(size),
        replicate_index=REPLICATE_ZERO,
        references=tuple(_reference(CLIENT_A, row_id) for row_id in row_ids),
    )


def test_calibration_support_is_frozen_and_holds_provenance() -> None:
    support = _support(120)
    assert support.benign_calibration_count.value == 120


def test_eligibility_decision_eligible_requires_meeting_minimum_support() -> None:
    def build() -> EligibilityDecision:
        return EligibilityDecision(
            support=_support(50),
            minimum_support=CalibrationSize(100),
            status=EligibilityStatus.ELIGIBLE,
            reason=None,
        )

    with pytest.raises(ScientificContractError, match="meet the minimum support"):
        build()


def test_eligibility_decision_eligible_cannot_carry_a_reason() -> None:
    def build() -> EligibilityDecision:
        return EligibilityDecision(
            support=_support(120),
            minimum_support=CalibrationSize(100),
            status=EligibilityStatus.ELIGIBLE,
            reason=CalibrationUnavailableReason.INSUFFICIENT_BENIGN_SUPPORT,
        )

    with pytest.raises(ScientificContractError, match="cannot carry an unavailability reason"):
        build()


def test_eligibility_decision_excluded_requires_a_reason() -> None:
    def build() -> EligibilityDecision:
        return EligibilityDecision(
            support=_support(50),
            minimum_support=CalibrationSize(100),
            status=EligibilityStatus.EXCLUDED,
            reason=None,
        )

    with pytest.raises(ScientificContractError, match="require a typed unavailability reason"):
        build()


def test_eligibility_decision_is_eligible_reflects_status() -> None:
    support = _support(120)
    decision = EligibilityDecision(
        support=support,
        minimum_support=CalibrationSize(100),
        status=EligibilityStatus.ELIGIBLE,
        reason=None,
    )
    assert decision.is_eligible


def test_calibration_subsample_rejects_size_mismatch() -> None:
    references = (_reference(CLIENT_A, "r0"),)

    def build() -> CalibrationSubsample:
        return CalibrationSubsample(
            size=CalibrationSize(2),
            replicate_index=REPLICATE_ZERO,
            references=references,
        )

    with pytest.raises(ScientificContractError, match="equal the declared calibration size"):
        build()


def test_calibration_subsample_rejects_duplicate_references() -> None:
    references = (_reference(CLIENT_A, "r0"), _reference(CLIENT_A, "r0"))

    def build() -> CalibrationSubsample:
        return CalibrationSubsample(
            size=CalibrationSize(2),
            replicate_index=REPLICATE_ZERO,
            references=references,
        )

    with pytest.raises(ScientificContractError, match="without replacement"):
        build()


def test_calibration_subsample_rejects_mixed_clients() -> None:
    references = (_reference(CLIENT_A, "r0"), _reference(CLIENT_B, "r1"))

    def build() -> CalibrationSubsample:
        return CalibrationSubsample(
            size=CalibrationSize(2),
            replicate_index=REPLICATE_ZERO,
            references=references,
        )

    with pytest.raises(ScientificContractError, match="exactly one client"):
        build()


def test_replicate_index_rejects_negative_values() -> None:
    def build() -> ReplicateIndex:
        return ReplicateIndex(-1)

    with pytest.raises(ValueError, match="replicate index"):
        build()


def test_replicate_manifest_requires_nested_subsamples() -> None:
    smaller = _subsample(2, ("r0", "r1"))
    larger = _subsample(3, ("r2", "r3", "r4"))

    def build() -> CalibrationReplicateManifest:
        return CalibrationReplicateManifest(
            client=CLIENT_A,
            coordinate=COORDINATE,
            training_seed=Seed(0),
            replicate_index=REPLICATE_ZERO,
            full_calibration_count=RowCount(5),
            subsamples=(smaller, larger),
            unavailable_sizes=(),
            unavailable_reason=None,
        )

    with pytest.raises(ScientificContractError, match="subset of the same replicate's larger subsample"):
        build()


def test_replicate_manifest_accepts_properly_nested_subsamples() -> None:
    smaller = _subsample(2, ("r0", "r1"))
    larger = _subsample(3, ("r0", "r1", "r2"))
    manifest = CalibrationReplicateManifest(
        client=CLIENT_A,
        coordinate=COORDINATE,
        training_seed=Seed(0),
        replicate_index=REPLICATE_ZERO,
        full_calibration_count=RowCount(3),
        subsamples=(smaller, larger),
        unavailable_sizes=(),
        unavailable_reason=None,
    )
    assert len(manifest.subsamples) == 2


def test_replicate_manifest_requires_reason_for_unavailable_sizes() -> None:
    def build() -> CalibrationReplicateManifest:
        return CalibrationReplicateManifest(
            client=CLIENT_A,
            coordinate=COORDINATE,
            training_seed=Seed(0),
            replicate_index=REPLICATE_ZERO,
            full_calibration_count=RowCount(1),
            subsamples=(),
            unavailable_sizes=(CalibrationSize(500),),
            unavailable_reason=None,
        )

    with pytest.raises(ScientificContractError, match="exactly one typed reason"):
        build()


def test_replicate_manifest_rejects_foreign_client_references() -> None:
    foreign_subsample = CalibrationSubsample(
        size=CalibrationSize(1),
        replicate_index=REPLICATE_ZERO,
        references=(_reference(CLIENT_B, "r0"),),
    )

    def build() -> CalibrationReplicateManifest:
        return CalibrationReplicateManifest(
            client=CLIENT_A,
            coordinate=COORDINATE,
            training_seed=Seed(0),
            replicate_index=REPLICATE_ZERO,
            full_calibration_count=RowCount(1),
            subsamples=(foreign_subsample,),
            unavailable_sizes=(),
            unavailable_reason=None,
        )

    with pytest.raises(ScientificContractError, match="belong to the manifest client"):
        build()
