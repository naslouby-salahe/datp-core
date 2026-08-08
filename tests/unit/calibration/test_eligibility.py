import polars as pl
import pytest
from tests.unit.calibration.helpers import attack_score_record, benign_score_record, some_client
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import PartitionRole, StableRowId
from datp_core.core.numeric import CalibrationSize, RowCount, Seed
from datp_core.data.populations.contracts import EligibleCohort
from datp_core.protocols.calibration import CalibrationEligibilityProtocol
from datp_core.thresholds.calibration.eligibility import (
    CalibrationSupport,
    EligibilityDecision,
    EligibilityStatus,
    calibration_support,
    decide_eligibility,
    eligible_clients,
    load_benign_calibration_references,
    reject_calibration_evaluation_overlap,
    reject_evaluation_partition_in_eligibility,
    reject_score_coordinate_mismatch,
    require_common_eligible_cohort,
)

PROTOCOL = CalibrationEligibilityProtocol(minimum_support=CalibrationSize(100))


def _support(client_id: str, count: int) -> CalibrationSupport:
    return CalibrationSupport(
        client=some_client(client_id),
        coordinate=fedavg_coordinate(Seed(0)),
        benign_calibration_count=RowCount(count),
        calibration_score_set_checksum=Checksum("a" * 64),
    )


def test_reject_evaluation_partition_in_eligibility_accepts_calibration() -> None:
    reject_evaluation_partition_in_eligibility(PartitionRole.CALIBRATION)


def test_reject_evaluation_partition_in_eligibility_rejects_evaluation() -> None:
    def call() -> None:
        reject_evaluation_partition_in_eligibility(PartitionRole.EVALUATION)

    with pytest.raises(LeakageError, match="calibration-partition scores only"):
        call()


def test_reject_calibration_evaluation_overlap_detects_shared_rows() -> None:
    def call() -> None:
        reject_calibration_evaluation_overlap(
            frozenset({StableRowId("row-1"), StableRowId("row-2")}),
            frozenset({StableRowId("row-2"), StableRowId("row-3")}),
        )

    with pytest.raises(LeakageError, match="must not share source rows"):
        call()


def test_reject_calibration_evaluation_overlap_allows_disjoint_rows() -> None:
    reject_calibration_evaluation_overlap(
        frozenset({StableRowId("row-1"), StableRowId("row-2")}),
        frozenset({StableRowId("row-3"), StableRowId("row-4")}),
    )


def test_reject_score_coordinate_mismatch(tmp_path) -> None:
    record_a = benign_score_record(tmp_path, "client_a", (0.1, 0.2, 0.3))
    record_b = benign_score_record(tmp_path, "client_b", (0.4, 0.5), seed=Seed(1))

    def call() -> None:
        reject_score_coordinate_mismatch((record_a, record_b))

    with pytest.raises(ScientificContractError, match="share one coordinate"):
        call()


def test_load_benign_calibration_references_rejects_attack_rows(tmp_path) -> None:
    record = attack_score_record(tmp_path, "client_a", (0.1, 0.2))

    def call() -> None:
        load_benign_calibration_references(record)

    with pytest.raises(LeakageError, match="attack-labelled rows"):
        call()


def test_load_benign_calibration_references_returns_one_reference_per_row(tmp_path) -> None:
    record = benign_score_record(tmp_path, "client_a", (0.1, 0.2, 0.3))
    references = load_benign_calibration_references(record)
    assert len(references) == 3
    assert {reference.stable_row_id for reference in references} == {
        "client_a-calibration-0",
        "client_a-calibration-1",
        "client_a-calibration-2",
    }


def test_load_benign_calibration_references_rejects_duplicate_stable_row_ids(tmp_path) -> None:
    record = benign_score_record(tmp_path, "client_a", (0.1, 0.2), row_id_prefix="duplicate-row-prefix")
    frame = pl.read_parquet(record.path).with_columns(pl.lit("same-row").alias("stable_row_id"))
    frame.write_parquet(record.path)

    def call() -> None:
        load_benign_calibration_references(record)

    with pytest.raises(ScientificContractError, match="unique stable source-row identities"):
        call()


def test_calibration_support_counts_benign_rows(tmp_path) -> None:
    record = benign_score_record(tmp_path, "client_a", (0.1, 0.2, 0.3, 0.4))
    references = load_benign_calibration_references(record)
    support = calibration_support(record, references, Checksum("a" * 64))
    assert support.benign_calibration_count == RowCount(4)


def test_decide_eligibility_marks_sufficient_support_as_eligible(tmp_path) -> None:
    record = benign_score_record(tmp_path, "client_a", tuple(float(i) for i in range(150)))
    references = load_benign_calibration_references(record)
    support = calibration_support(record, references, Checksum("a" * 64))
    decision = decide_eligibility(support, PROTOCOL)
    assert decision.support is support
    assert decision.status is EligibilityStatus.ELIGIBLE
    assert decision.reason is None


def test_decide_eligibility_marks_insufficient_support_as_excluded(tmp_path) -> None:
    record = benign_score_record(tmp_path, "client_a", (0.1, 0.2, 0.3))
    references = load_benign_calibration_references(record)
    support = calibration_support(record, references, Checksum("a" * 64))
    decision = decide_eligibility(support, PROTOCOL)
    assert decision.support is support
    assert decision.status is EligibilityStatus.EXCLUDED
    assert decision.reason is not None


def test_eligible_clients_filters_and_orders_deterministically() -> None:
    decisions = (
        EligibilityDecision(
            support=_support("client_b", 150),
            minimum_support=CalibrationSize(100),
            status=EligibilityStatus.ELIGIBLE,
            reason=None,
        ),
        EligibilityDecision(
            support=_support("client_a", 150),
            minimum_support=CalibrationSize(100),
            status=EligibilityStatus.ELIGIBLE,
            reason=None,
        ),
    )
    result = eligible_clients(decisions)
    assert [client.client_id for client in result] == ["client_a", "client_b"]


def test_require_common_eligible_cohort_accepts_matching_cohorts() -> None:
    cohort = EligibleCohort(clients=(some_client("client_a"), some_client("client_b")))
    result = require_common_eligible_cohort((cohort, cohort))
    assert result == cohort


def test_require_common_eligible_cohort_rejects_mismatched_cohorts() -> None:
    first = EligibleCohort(clients=(some_client("client_a"), some_client("client_b")))
    second = EligibleCohort(clients=(some_client("client_a"),))

    def call() -> None:
        require_common_eligible_cohort((first, second))

    with pytest.raises(ScientificContractError, match="same eligible cohort"):
        call()
