"""Unit tests for readiness-gate evaluation against the new data-package API.

Tests ``evaluate_readiness_gates`` with typed ``ReadinessGate`` contracts and
``MaterializedSplitSummary`` fixtures constructed directly -- no Parquet required.
"""

from datp_core.core.numbers import Probability
from datp_core.data.contracts.eligibility import ReadinessGate
from datp_core.data.contracts.enums import DatasetCapability, ReadinessGateFailureCode
from datp_core.data.contracts.values import GateId
from datp_core.data.manifests.summary import MaterializedSplitSummary
from datp_core.data.materialization.models import MaterializationEvidence
from datp_core.data.readiness.gates import evaluate_readiness_gates

_MATERIALIZATION_EVIDENCE = MaterializationEvidence(
    schema_version="materialized.v1",
    source_rows_seen=0,
    excluded_rows=0,
    canonical_rows=0,
    duplicate_rows_removed=0,
    conflicting_label_feature_group_count=0,
    written_rows=0,
    encoded_feature_names=(),
)


def _summary(
    *,
    client_ids: tuple[str, ...],
    eligible_ids: tuple[str, ...],
) -> MaterializedSplitSummary:
    """Build a minimal summary with the given client and eligible sets."""
    ineligible_ids = tuple(c for c in client_ids if c not in eligible_ids)
    return MaterializedSplitSummary(
        schema_version="split-summary.v1",
        dataset_id="test",
        setup_id="test",
        materialization_id="test",
        source_checksum="0" * 64,
        configuration_checksum="0" * 64,
        artifact_checksum="0" * 64,
        schema_checksum="0" * 64,
        preprocessing_checksum="0" * 64,
        artifact_shape="test",
        total_rows=0,
        split_counts=(),
        client_split_counts=(),
        class_counts=(),
        client_ids=client_ids,
        eligible_client_ids=eligible_ids,
        ineligible_client_ids=ineligible_ids,
        attack_rows=0,
        chronology_ranges=(),
        materialization=_MATERIALIZATION_EVIDENCE,
    )


def _gate(
    *,
    gate_id: str = "gate",
    min_clients: int = 1,
    min_proportion: float = 0.0,
    capabilities: tuple[DatasetCapability, ...] = (),
) -> ReadinessGate:
    """Build a readiness gate with the given thresholds."""
    return ReadinessGate(
        identifier=GateId(gate_id),
        minimum_eligible_clients=min_clients,
        minimum_eligible_proportion=Probability(min_proportion),
        required_capabilities=capabilities,
    )


class TestEligibleProportionThreshold:
    """Gate with ``minimum_eligible_proportion`` above the observed proportion."""

    def test_below_threshold_returns_failure(self) -> None:
        gate = _gate(min_proportion=0.75)
        summary = _summary(
            client_ids=("c1", "c2", "c3", "c4"),
            eligible_ids=("c1", "c2"),
        )

        failures = evaluate_readiness_gates(
            gates=(gate,),
            capabilities=(),
            summary=summary,
        )

        assert len(failures) == 1
        f = failures[0]
        assert f.gate_id == "gate"
        assert f.code is ReadinessGateFailureCode.MINIMUM_ELIGIBLE_PROPORTION
        assert "0.75" in f.detail

    def test_at_threshold_passes(self) -> None:
        gate = _gate(min_proportion=0.5)
        summary = _summary(
            client_ids=("c1", "c2", "c3", "c4"),
            eligible_ids=("c1", "c2"),
        )

        failures = evaluate_readiness_gates(
            gates=(gate,),
            capabilities=(),
            summary=summary,
        )

        assert failures == ()


class TestRequiredCapability:
    """Gate with a capability the dataset does not advertise."""

    def test_missing_required_capability_returns_failure(self) -> None:
        gate = _gate(capabilities=(DatasetCapability.BENIGN_CALIBRATION,))
        summary = _summary(client_ids=("c1",), eligible_ids=("c1",))

        failures = evaluate_readiness_gates(
            gates=(gate,),
            capabilities=(DatasetCapability.ATTACK_EVALUATION,),
            summary=summary,
        )

        assert len(failures) == 1
        f = failures[0]
        assert f.gate_id == "gate"
        assert f.code is ReadinessGateFailureCode.REQUIRED_CAPABILITY_MISSING
        assert "benign_calibration" in f.detail

    def test_present_capability_passes(self) -> None:
        gate = _gate(capabilities=(DatasetCapability.BENIGN_CALIBRATION,))
        summary = _summary(client_ids=("c1",), eligible_ids=("c1",))

        failures = evaluate_readiness_gates(
            gates=(gate,),
            capabilities=(DatasetCapability.BENIGN_CALIBRATION,),
            summary=summary,
        )

        assert failures == ()


class TestMinimumEligibleClients:
    """Gate with ``minimum_eligible_clients`` above the observed count."""

    def test_below_minimum_returns_failure(self) -> None:
        gate = _gate(min_clients=2)
        summary = _summary(
            client_ids=("c1", "c2", "c3"),
            eligible_ids=("c1",),
        )

        failures = evaluate_readiness_gates(
            gates=(gate,),
            capabilities=(),
            summary=summary,
        )

        assert len(failures) == 1
        f = failures[0]
        assert f.gate_id == "gate"
        assert f.code is ReadinessGateFailureCode.MINIMUM_ELIGIBLE_CLIENTS
        assert "requires 2" in f.detail
        assert "1" in f.detail

    def test_at_minimum_passes(self) -> None:
        gate = _gate(min_clients=2)
        summary = _summary(
            client_ids=("c1", "c2", "c3"),
            eligible_ids=("c1", "c2"),
        )

        failures = evaluate_readiness_gates(
            gates=(gate,),
            capabilities=(),
            summary=summary,
        )

        assert failures == ()


class TestAllGatesPassing:
    """Multiple gates all satisfied."""

    def test_multiple_satisfied_gates_return_empty(self) -> None:
        gate1 = ReadinessGate(
            identifier=GateId("proportion_gate"),
            minimum_eligible_clients=1,
            minimum_eligible_proportion=Probability(0.0),
            required_capabilities=(),
        )
        gate2 = ReadinessGate(
            identifier=GateId("capability_gate"),
            minimum_eligible_clients=1,
            minimum_eligible_proportion=Probability(0.0),
            required_capabilities=(
                DatasetCapability.BENIGN_CALIBRATION,
                DatasetCapability.ATTACK_EVALUATION,
            ),
        )
        summary = _summary(
            client_ids=("c1", "c2"),
            eligible_ids=("c1", "c2"),
        )

        failures = evaluate_readiness_gates(
            gates=(gate1, gate2),
            capabilities=(
                DatasetCapability.BENIGN_CALIBRATION,
                DatasetCapability.ATTACK_EVALUATION,
            ),
            summary=summary,
        )

        assert failures == ()


class TestMultipleFailures:
    """A single gate that triggers all three failure codes."""

    def test_aggregates_all_failure_codes(self) -> None:
        gate = ReadinessGate(
            identifier=GateId("strict_gate"),
            minimum_eligible_clients=5,
            minimum_eligible_proportion=Probability(0.9),
            required_capabilities=(DatasetCapability.TEMPORAL_RECALIBRATION,),
        )
        summary = _summary(
            client_ids=("c1", "c2"),
            eligible_ids=("c1",),
        )

        failures = evaluate_readiness_gates(
            gates=(gate,),
            capabilities=(),
            summary=summary,
        )

        assert len(failures) == 3
        codes = {f.code for f in failures}
        assert codes == {
            ReadinessGateFailureCode.MINIMUM_ELIGIBLE_CLIENTS,
            ReadinessGateFailureCode.MINIMUM_ELIGIBLE_PROPORTION,
            ReadinessGateFailureCode.REQUIRED_CAPABILITY_MISSING,
        }
        for f in failures:
            assert f.gate_id == "strict_gate"
