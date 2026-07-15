from datp_core.domain.evaluation.statistical_results import (
    AbsorptionBand,
    ClaimOutcome,
    StatisticalMethod,
)


def test_statistical_method_members_and_serialized_values_are_stable() -> None:
    assert tuple(StatisticalMethod) == (
        StatisticalMethod.BCA_BOOTSTRAP,
        StatisticalMethod.PERCENTILE_BOOTSTRAP,
        StatisticalMethod.WILCOXON_SIGNED_RANK,
        StatisticalMethod.CLIFFS_DELTA,
        StatisticalMethod.SPEARMAN,
        StatisticalMethod.LINEAR_REGRESSION_R2,
    )
    assert StatisticalMethod.BCA_BOOTSTRAP.value == "bca_bootstrap"


def test_claim_outcome_has_exactly_seven_members_with_stable_values() -> None:
    assert tuple(ClaimOutcome) == (
        ClaimOutcome.STRONG_POSITIVE,
        ClaimOutcome.WEAK_POSITIVE,
        ClaimOutcome.MIXED,
        ClaimOutcome.NULL,
        ClaimOutcome.OPPOSITE,
        ClaimOutcome.FEASIBILITY_REJECTION,
        ClaimOutcome.SUPPRESSED,
    )
    assert len(ClaimOutcome) == 7
    assert tuple(member.value for member in ClaimOutcome) == (
        "strong_positive",
        "weak_positive",
        "mixed",
        "null",
        "opposite",
        "feasibility_rejection",
        "suppressed",
    )


def test_absorption_band_has_exactly_four_members_with_stable_values() -> None:
    assert tuple(AbsorptionBand) == (
        AbsorptionBand.STRONGLY_USEFUL,
        AbsorptionBand.PARTIAL,
        AbsorptionBand.LARGELY_ABSORBED,
        AbsorptionBand.ALTERNATIVE_PATH,
    )
    assert len(AbsorptionBand) == 4
    assert tuple(member.value for member in AbsorptionBand) == (
        "strongly_useful",
        "partial",
        "largely_absorbed",
        "alternative_path",
    )
