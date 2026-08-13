from datp_core.analysis.mechanisms.association import (
    AssociationIssue,
    AssociationObservation,
    heterogeneity_benefit_association,
)
from datp_core.core.identifiers import ExperimentId, PopulationId, RegimeLabel
from datp_core.core.numeric import MetricValue, Seed


def test_association_below_five_observations_retains_no_coefficients() -> None:
    result = heterogeneity_benefit_association(tuple(AssociationObservation.model_construct() for _ in range(4)))

    assert result.issue is AssociationIssue.INSUFFICIENT_EVIDENCE
    assert result.statistics is None


def test_association_rejects_duplicate_seed_regime_observations() -> None:
    observation = AssociationObservation.model_construct(
        seed=Seed(0),
        experiment=ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        regime_label=RegimeLabel("natural"),
        heterogeneity=MetricValue(0.2),
        benefit=MetricValue(0.1),
    )

    try:
        heterogeneity_benefit_association((observation, observation, observation, observation, observation))
    except ValueError as error:
        assert "unique by seed" in str(error)
    else:
        raise AssertionError("duplicate association observations must be rejected")
