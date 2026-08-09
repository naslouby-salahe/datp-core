from datp_core.core.identifiers import ClientIdentityToken
from datp_core.core.numeric import ClientCount
from datp_core.data.populations.construction import FeasibilityAssessmentRequest, feasibility_from_candidates
from datp_core.data.populations.contracts import PopulationFeasibilityReason, PopulationFeasibilityStatus


def test_feasibility_matches_declaration() -> None:
    feasibility = feasibility_from_candidates(
        FeasibilityAssessmentRequest(
            expected_count=ClientCount(2),
            candidate_ids=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            accepted_ids=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            expected_identities=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            chronology_required=False,
        )
    )
    assert feasibility.status is PopulationFeasibilityStatus.FEASIBLE
    assert feasibility.reason is PopulationFeasibilityReason.CANDIDATE_SET_MATCHES_DECLARATION


def test_feasibility_detects_identity_mismatch() -> None:
    feasibility = feasibility_from_candidates(
        FeasibilityAssessmentRequest(
            expected_count=ClientCount(2),
            candidate_ids=(ClientIdentityToken("a"), ClientIdentityToken("c")),
            accepted_ids=(ClientIdentityToken("a"), ClientIdentityToken("c")),
            expected_identities=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            chronology_required=False,
        )
    )
    assert feasibility.status is PopulationFeasibilityStatus.INFEASIBLE
    assert feasibility.reason is PopulationFeasibilityReason.IDENTITY_SET_MISMATCH


def test_feasibility_detects_candidate_count_mismatch() -> None:
    feasibility = feasibility_from_candidates(
        FeasibilityAssessmentRequest(
            expected_count=ClientCount(3),
            candidate_ids=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            accepted_ids=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            expected_identities=None,
            chronology_required=False,
        )
    )
    assert feasibility.status is PopulationFeasibilityStatus.INFEASIBLE
    assert feasibility.reason is PopulationFeasibilityReason.CANDIDATE_COUNT_MISMATCH


def test_feasibility_requires_chronology_evidence_when_required() -> None:
    feasibility = feasibility_from_candidates(
        FeasibilityAssessmentRequest(
            expected_count=ClientCount(9),
            candidate_ids=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            accepted_ids=(),
            expected_identities=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            chronology_required=True,
        )
    )
    assert feasibility.status is PopulationFeasibilityStatus.INFEASIBLE
    assert feasibility.reason is PopulationFeasibilityReason.CHRONOLOGY_EVIDENCE_INSUFFICIENT


def test_feasibility_detects_empty_accepted_clients() -> None:
    feasibility = feasibility_from_candidates(
        FeasibilityAssessmentRequest(
            expected_count=ClientCount(2),
            candidate_ids=(ClientIdentityToken("a"), ClientIdentityToken("b")),
            accepted_ids=(),
            expected_identities=None,
            chronology_required=False,
        )
    )
    assert feasibility.status is PopulationFeasibilityStatus.INFEASIBLE
    assert feasibility.reason is PopulationFeasibilityReason.EMPTY_ACCEPTED_CLIENTS
