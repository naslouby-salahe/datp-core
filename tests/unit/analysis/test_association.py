from datp_core.analysis.mechanisms.association import (
    AssociationIssue,
    AssociationObservation,
    heterogeneity_benefit_association,
)


def test_association_below_five_observations_retains_no_coefficients() -> None:
    result = heterogeneity_benefit_association(
        tuple(AssociationObservation.model_construct() for _ in range(4))
    )

    assert result.issue is AssociationIssue.INSUFFICIENT_EVIDENCE
    assert result.statistics is None
