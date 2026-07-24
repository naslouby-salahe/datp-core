"""`evaluate_readiness_gates` is the actual domain-level decision logic that prevents a
configured-but-ineligible experiment from ever executing: `data/materialization.py` fails the
materialization stage (`StageJobOutcome.infeasible`) whenever this function returns issues.
Prior coverage only exercised a different mechanism (a missing stage handler); this file drives
the real `suppression_behaviors`/`eligibility_gates` decision rule end to end.
"""

from datp_core.core.identifiers import ExperimentId
from datp_core.core.values import PositiveInt, Probability
from datp_core.data.manifests import SplitManifest, SplitManifestEntry, SplitMembership
from datp_core.data.readiness import evaluate_readiness_gates
from datp_core.experiments.models import EligibilityGateRecord


def _entry(row: int, membership: SplitMembership, *, client: str, attack: bool = False) -> SplitManifestEntry:
    return SplitManifestEntry(
        source_path="source.csv", source_row_index=row, client_id=client, membership=membership, is_attack=attack
    )


def _gate(
    *, minimum_eligible_client_proportion: float, applies_to_experiments: tuple[ExperimentId, ...]
) -> EligibilityGateRecord:
    return EligibilityGateRecord(
        identifier="gate",
        candidate_population="all_clients",
        minimum_benign_calibration_count=PositiveInt(2),
        minimum_eligible_client_proportion=Probability(minimum_eligible_client_proportion),
        evaluation_time="before_training",
        failure_outcome="typed_infeasibility_outcome",
        population_reduction_without_explicit_roadmap_authorization="forbidden",
        applies_to_experiments=applies_to_experiments,
    )


def _two_client_manifest() -> SplitManifest:
    """One eligible client (c1, 2 benign calibration rows) and one ineligible (c2, 1 row) -> 50%."""
    return SplitManifest(
        entries=(
            _entry(1, SplitMembership.TRAIN, client="c1"),
            _entry(2, SplitMembership.CALIBRATION, client="c1"),
            _entry(3, SplitMembership.CALIBRATION, client="c1"),
            _entry(4, SplitMembership.TEST, client="c1"),
            _entry(5, SplitMembership.TRAIN, client="c2"),
            _entry(6, SplitMembership.CALIBRATION, client="c2"),
            _entry(7, SplitMembership.TEST, client="c2"),
        ),
        minimum_benign_calibration_count=2,
    )


def test_experiment_below_the_configured_eligible_proportion_is_suppressed() -> None:
    experiment_id = ExperimentId("ineligible_experiment")
    gate = _gate(minimum_eligible_client_proportion=0.75, applies_to_experiments=(experiment_id,))

    issues = evaluate_readiness_gates(("gate",), {"gate": gate}, _two_client_manifest(), experiment_id)

    assert len(issues) == 1
    assert "eligible proportion 0.500 below minimum 0.75" in issues[0]


def test_experiment_meeting_the_configured_eligible_proportion_is_not_suppressed() -> None:
    experiment_id = ExperimentId("eligible_experiment")
    gate = _gate(minimum_eligible_client_proportion=0.5, applies_to_experiments=(experiment_id,))

    issues = evaluate_readiness_gates(("gate",), {"gate": gate}, _two_client_manifest(), experiment_id)

    assert issues == []


def test_gate_not_bound_to_the_experiment_never_suppresses_it() -> None:
    """A gate configured for a different experiment must never block this one, even if this
    experiment's manifest would fail the gate's threshold."""
    experiment_id = ExperimentId("unaffected_experiment")
    gate = _gate(minimum_eligible_client_proportion=1.0, applies_to_experiments=(ExperimentId("other_experiment"),))

    issues = evaluate_readiness_gates(("gate",), {"gate": gate}, _two_client_manifest(), experiment_id)

    assert issues == []


def test_unknown_gate_name_is_reported_rather_than_silently_ignored() -> None:
    experiment_id = ExperimentId("any_experiment")

    issues = evaluate_readiness_gates(("nonexistent_gate",), {}, _two_client_manifest(), experiment_id)

    assert issues == ["unknown readiness gate: nonexistent_gate"]
