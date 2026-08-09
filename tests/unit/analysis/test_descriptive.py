import pytest
from tests.unit.learning.federated.helpers import client_identity

from datp_core.analysis.contrasts import MetricSeries
from datp_core.analysis.descriptive import (
    ClientEvaluationScoreSeries,
    ObservationCounts,
    QuantileRange,
    ScoreRole,
    client_score_geometry,
    count_paired_differences,
    empirical_cdf_points,
    score_geometry_from_client_vectors,
    summarize_values,
)
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import AvailabilityStatus, EvidenceRole
from datp_core.core.numeric import MetricValue, PairedObservationCount, Ratio, Seed

_DEFAULT_QUANTILES = QuantileRange(lower=Ratio(0.25), upper=Ratio(0.75))


def test_descriptive_summary_preserves_typed_counts_and_statistics() -> None:
    values: MetricSeries = (
        MetricValue(0.0),
        MetricValue(0.5),
        MetricValue(1.0),
    )
    summary = summarize_values(
        values,
        evidence_role=EvidenceRole.CONFIRMATORY,
        counts=ObservationCounts(
            unavailable=PairedObservationCount(2),
            excluded=PairedObservationCount(1),
        ),
        quantiles=_DEFAULT_QUANTILES,
    )
    assert summary.availability is AvailabilityStatus.AVAILABLE
    assert summary.statistics is not None
    assert summary.statistics.mean == MetricValue(0.5)
    assert summary.statistics.spread == MetricValue(1.0)
    assert summary.available_count == PairedObservationCount(3)
    assert summary.reason is None


def test_empty_summary_is_explicitly_unavailable() -> None:
    summary = summarize_values(
        (),
        evidence_role=EvidenceRole.SUPPORTIVE,
        counts=ObservationCounts(
            unavailable=PairedObservationCount(1),
            excluded=PairedObservationCount(0),
        ),
        quantiles=_DEFAULT_QUANTILES,
    )
    assert summary.availability is AvailabilityStatus.UNAVAILABLE
    assert summary.statistics is None
    assert summary.reason == "no available values"


def test_quantile_range_rejects_reversed_bounds() -> None:
    with pytest.raises(ValueError, match="lower quantile"):
        QuantileRange(lower=Ratio(0.75), upper=Ratio(0.25))


def test_sign_counts_preserve_zeroes_with_semantic_counts() -> None:
    result = count_paired_differences(
        (
            MetricValue(0.4),
            MetricValue(0.0),
            MetricValue(-0.2),
            MetricValue(0.1),
        )
    )
    assert (result.positive, result.zero, result.negative) == (
        PairedObservationCount(2),
        PairedObservationCount(1),
        PairedObservationCount(1),
    )
    assert result.positive_proportion == Ratio(0.5)


def test_empirical_cdf_points_expose_score_x_and_cumulative_probability_y() -> None:
    points = empirical_cdf_points((MetricValue(0.3), MetricValue(0.1), MetricValue(0.2)))
    assert tuple(point.score.value for point in points) == (0.1, 0.2, 0.3)
    assert [point.cumulative_probability.value for point in points] == pytest.approx([1 / 3, 2 / 3, 1.0])


def test_client_score_geometry_marks_empty_scores_unavailable() -> None:
    client = client_identity("device_a")
    geometry = client_score_geometry(
        client=client,
        score_role=ScoreRole.BENIGN_EVALUATION,
        scores=(),
    )
    assert geometry.unavailable_reason is not None
    assert geometry.empirical_cdf == ()


def test_score_geometry_retains_every_declared_client_without_silent_omission() -> None:
    clients = (client_identity("device_a"), client_identity("device_b"), client_identity("device_c"))
    geometry = score_geometry_from_client_vectors(
        seed=Seed(0),
        source_score_checksum=Checksum("e" * 64),
        benign_evaluation=(
            ClientEvaluationScoreSeries(client=clients[0], scores=(MetricValue(0.1), MetricValue(0.2))),
            ClientEvaluationScoreSeries(client=clients[1], scores=()),
            ClientEvaluationScoreSeries(client=clients[2], scores=(MetricValue(0.4),)),
        ),
        attack_evaluation=(
            ClientEvaluationScoreSeries(client=clients[0], scores=()),
            ClientEvaluationScoreSeries(client=clients[1], scores=(MetricValue(0.9),)),
            ClientEvaluationScoreSeries(client=clients[2], scores=()),
        ),
        threshold_overlays=(),
        attack_geometry_available=True,
    )
    benign = tuple(item for item in geometry.clients if item.score_role is ScoreRole.BENIGN_EVALUATION)
    attack = tuple(item for item in geometry.clients if item.score_role is ScoreRole.ATTACK_EVALUATION)
    assert tuple(item.client for item in benign) == clients
    assert tuple(item.client for item in attack) == clients
    assert benign[1].unavailable_reason is not None
    assert attack[0].unavailable_reason is not None
    assert attack[1].empirical_cdf[0].score == MetricValue(0.9)
    assert attack[1].empirical_cdf[0].cumulative_probability == Ratio(1.0)
