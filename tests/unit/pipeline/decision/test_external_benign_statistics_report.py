"""Edge benign-only federated-statistics report consumer contract (WL-05)."""

from datp_core.core.identifiers import ClientIdentityToken, EvidenceRole, ExperimentId, PopulationId
from datp_core.core.numeric import (
    AbsoluteThresholdError,
    ByteCount,
    MetricValue,
    Ratio,
    RowCount,
    ScoreMoment,
    ScoreVariance,
    Seed,
    ThresholdValue,
)
from datp_core.experiments.external.run import (
    ExternalBenignStatisticsClient,
    ExternalBenignStatisticsReport,
    ExternalBenignStatisticsSummary,
    _external_benign_statistics_markdown,
)


def _summary(seed_value: int, cv_fpr: float | None) -> ExternalBenignStatisticsSummary:
    return ExternalBenignStatisticsSummary(
        seed=Seed(seed_value),
        matched_threshold=ThresholdValue(0.5),
        pooled_quantile_threshold=ThresholdValue(0.45),
        global_mean=ScoreMoment(0.3),
        within_client_variance=ScoreVariance(0.02),
        between_client_variance=ScoreVariance(0.005),
        full_pooled_variance=ScoreVariance(0.025),
        between_ratio=Ratio(0.2),
        absolute_threshold_error=AbsoluteThresholdError(0.05),
        achieved_benign_exceedance=Ratio(0.095),
        estimated_communication_bytes=ByteCount(160),
        clients=(
            ExternalBenignStatisticsClient(
                client_id=ClientIdentityToken("client_a"),
                count=RowCount(10),
                mean=ScoreMoment(0.3),
                variance=ScoreVariance(0.02),
                benign_exceedance_count=RowCount(1),
                disclosed_bytes=ByteCount(32),
            ),
        ),
        cv_fpr=None if cv_fpr is None else MetricValue(cv_fpr),
        worst_client_fpr=None if cv_fpr is None else MetricValue(cv_fpr * 2),
    )


def _report() -> ExternalBenignStatisticsReport:
    return ExternalBenignStatisticsReport(
        experiment=ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
        population=PopulationId.EDGE_SENSOR_GROUPS,
        evidence_role=EvidenceRole.EXTERNAL_VALIDATION,
        rows=(_summary(0, 0.25), _summary(1, None)),
    )


def test_external_benign_statistics_markdown_publishes_estimator_variance_and_communication() -> None:
    report = _report()
    markdown = _external_benign_statistics_markdown(report)

    assert "Matched threshold (estimator)" in markdown
    assert "Between-client variance ratio" in markdown
    assert "Estimated communication bytes" in markdown
    assert "Achieved benign exceedance" in markdown
    assert "Absolute threshold error" in markdown
    assert "Seed 0" in markdown
    assert "Seed 1" in markdown
    assert "Disclosed per-client benign summary" in markdown
    assert "| client_a | 10 |" in markdown
    assert "| 1 |" in markdown  # per-client benign exceedance count
    assert "| 32 |" in markdown  # per-client disclosed bytes


def test_external_benign_statistics_markdown_types_unavailable_attack_outcome() -> None:
    markdown = _external_benign_statistics_markdown(_report())

    assert "| 0.250 |" in markdown  # available CV(FPR) rendered for seed 0
    assert "unavailable" in markdown  # seed 1 CV(FPR) is a typed unavailable attack outcome
    assert "Attack outcomes are typed unavailable" in markdown


def test_external_benign_statistics_report_round_trips_typed_summary() -> None:
    report = _report()
    payload = report.model_dump_json()
    loaded = ExternalBenignStatisticsReport.model_validate_json(payload)

    assert loaded.experiment is ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION
    assert loaded.population is PopulationId.EDGE_SENSOR_GROUPS
    assert loaded.rows[0].cv_fpr == MetricValue(0.25)
    assert loaded.rows[1].cv_fpr is None
    assert loaded.rows[1].worst_client_fpr is None
    assert loaded.rows[0].between_ratio == Ratio(0.2)
    assert loaded.rows[0].clients[0].benign_exceedance_count == RowCount(1)
    assert loaded.rows[0].clients[0].disclosed_bytes == ByteCount(32)
