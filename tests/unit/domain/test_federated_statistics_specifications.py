from decimal import Decimal

from datp_core.domain.mathematics.dispersion import ClientMoment
from datp_core.domain.thresholding.federated_statistics import (
    FedStatsBenignThresholdSpec,
    FedStatsCandidateExceedance,
    FedStatsK,
)
from datp_core.domain.thresholding.policies import FprTarget, ThresholdConstructionKind


def test_fedstats_full_pooled_variance_includes_between_client_mean_shift() -> None:
    specification = FedStatsBenignThresholdSpec(kind=ThresholdConstructionKind.FED_STATS_BENIGN)

    evidence = specification.pooled_evidence(
        client_moments=(
            ClientMoment(sample_count=2, mean=1.0, variance=1.0),
            ClientMoment(sample_count=2, mean=5.0, variance=1.0),
        )
    )

    assert evidence.within_term == 1.0
    assert evidence.between_term == 4.0
    assert evidence.global_variance == 5.0
    assert evidence.global_variance > evidence.within_term
    assert evidence.between_ratio == 0.8


def test_fedstats_matched_exceedance_tie_selects_larger_k() -> None:
    specification = FedStatsBenignThresholdSpec(kind=ThresholdConstructionKind.FED_STATS_BENIGN)
    evidence = specification.pooled_evidence(
        client_moments=(
            ClientMoment(sample_count=50, mean=5.0, variance=1.0),
            ClientMoment(sample_count=50, mean=5.0, variance=1.0),
        )
    )
    candidate_exceedances = tuple(
        FedStatsCandidateExceedance(
            multiplier=multiplier,
            benign_exceedance_count=20 if multiplier.value in {Decimal("2.00"), Decimal("2.50")} else 0,
        )
        for multiplier in specification.candidate_grid
    )

    selected = specification.select_matched_exceedance(
        pooled_evidence=evidence,
        candidate_exceedances=candidate_exceedances,
        target_exceedance_rate=FprTarget(value="0.20"),
    )

    assert selected.multiplier == FedStatsK(value=Decimal("2.50"))
    assert selected.benign_exceedance_count == 20
