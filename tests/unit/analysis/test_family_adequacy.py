import pytest
from tests.unit.thresholding.helpers import identity

from datp_core.analysis.mechanisms.divergence import ClientScoreVector, jensen_shannon_divergence
from datp_core.analysis.mechanisms.family_adequacy import family_explanatory_adequacy
from datp_core.core.identifiers import FamilyIdentity
from datp_core.core.numeric import MetricValue, PairedObservationCount, Seed, ThresholdValue
from datp_core.data.populations.contracts import FamilyAssignment
from datp_core.presentation.export import _render_family_explanatory_adequacy


def test_family_adequacy_separates_pairs_and_excludes_singleton_thresholds() -> None:
    client_a, client_b, client_c = (identity(name) for name in ("client_a", "client_b", "client_c"))
    family_a = FamilyIdentity("family_a")
    family_b = FamilyIdentity("family_b")
    assignments = (
        FamilyAssignment(client_a, family_a),
        FamilyAssignment(client_b, family_a),
        FamilyAssignment(client_c, family_b),
    )
    divergence = jensen_shannon_divergence(
        (
            ClientScoreVector(client=client_a, scores=(MetricValue(0.0), MetricValue(0.1))),
            ClientScoreVector(client=client_b, scores=(MetricValue(0.0), MetricValue(0.1))),
            ClientScoreVector(client=client_c, scores=(MetricValue(5.0), MetricValue(6.0))),
        )
    )

    result = family_explanatory_adequacy(
        seed=Seed(2),
        divergence=divergence,
        family_by_client=assignments,
        local_thresholds=tuple(
            zip(assignments, (ThresholdValue(0.1), ThresholdValue(0.3), ThresholdValue(0.9)), strict=True)
        ),
    )

    assert result.within_family_pair_count == PairedObservationCount(1)
    assert result.between_family_pair_count == PairedObservationCount(2)
    assert result.within_family_js == MetricValue(0.0)
    assert result.family_separation_js is not None and result.family_separation_js.value > 0.9
    assert result.mean_within_family_threshold_sd == MetricValue(0.1414213562373095)
    assert result.singleton_families == (family_b,)
    assert tuple(str(line) for line in _render_family_explanatory_adequacy(result)) == (
        "Seed: 2",
        "Within-family pairs: 1",
        "Between-family pairs: 2",
        "Singleton families: family_b",
        "Within-family JS: 0.000",
        "Between-family JS: 1.000",
        "Family separation JS: 1.000",
        "Mean within-family threshold SD: 0.141",
        "Between-family threshold SD: 0.495",
    )


def test_family_adequacy_retains_nonpositive_separation() -> None:
    client_a, client_b, client_c = (identity(name) for name in ("client_a", "client_b", "client_c"))
    assignments = (
        FamilyAssignment(client_a, FamilyIdentity("family_a")),
        FamilyAssignment(client_b, FamilyIdentity("family_a")),
        FamilyAssignment(client_c, FamilyIdentity("family_b")),
    )
    divergence = jensen_shannon_divergence(
        (
            ClientScoreVector(client=client_a, scores=(MetricValue(0.0), MetricValue(0.1))),
            ClientScoreVector(client=client_b, scores=(MetricValue(5.0), MetricValue(6.0))),
            ClientScoreVector(client=client_c, scores=(MetricValue(0.0), MetricValue(0.1))),
        )
    )

    result = family_explanatory_adequacy(
        seed=Seed(2),
        divergence=divergence,
        family_by_client=assignments,
        local_thresholds=tuple(
            zip(assignments, (ThresholdValue(0.1), ThresholdValue(0.3), ThresholdValue(0.9)), strict=True)
        ),
    )

    assert result.family_separation_js is not None
    assert result.family_separation_js.value == pytest.approx(-0.5)
