from types import SimpleNamespace
from typing import cast

import polars as pl
import pytest

from datp_core.analysis.scientific_decision import ScientificDecision
from datp_core.analysis.temporal import (
    LOCKED_TEMPORAL_DECISION_PROTOCOL,
    TemporalClientTrajectory,
    TemporalRecoveryResult,
    _campaign_decision_from_counts,
    _TemporalInterpretationCounts,
    temporal_drift_js,
)
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    AvailabilityStatus,
    ClientIdentityToken,
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
    ScoreFrameColumn,
    TemporalState,
)
from datp_core.core.numeric import MetricValue, Seed, SeedCount, SeedObservationCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.scoring.models import FederatedScoreRecord


def test_temporal_state_names_do_not_claim_continuous_adaptation() -> None:
    assert all("continuous" not in state.value and "stream" not in state.value for state in TemporalState)


def test_temporal_drift_js_uses_unsmoothed_pooled_type7_quantile_bins(tmp_path) -> None:
    historical = tmp_path / "historical.parquet"
    future = tmp_path / "future.parquet"
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (0.0, 0.0, 0.0, 1.0)}).write_parquet(historical)
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (0.0, 1.0, 1.0, 1.0)}).write_parquet(future)
    client = object()

    divergence = temporal_drift_js(
        cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=historical)),
        cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=future)),
    )

    assert divergence.value == pytest.approx(0.18872187554086717)


def test_temporal_drift_js_blocks_a_collapsed_pooled_quantile_grid(tmp_path) -> None:
    historical = tmp_path / "historical.parquet"
    future = tmp_path / "future.parquet"
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (1.0, 1.0)}).write_parquet(historical)
    pl.DataFrame({ScoreFrameColumn.RECONSTRUCTION_ERROR.value: (1.0, 1.0)}).write_parquet(future)
    client = object()

    with pytest.raises(ScientificContractError, match="two nonzero-width pooled quantile bins"):
        temporal_drift_js(
            cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=historical)),
            cast(FederatedScoreRecord, SimpleNamespace(scored_client=client, path=future)),
        )


@pytest.mark.parametrize(
    ("counts", "expected"),
    (
        (
            _TemporalInterpretationCounts(
                material_recovery=SeedObservationCount(0),
                partial_or_weak_recovery=SeedObservationCount(0),
                without_recovery=SeedObservationCount(0),
                opposite=SeedObservationCount(0),
                no_degradation=SeedObservationCount(10),
                blocked=SeedObservationCount(0),
            ),
            ScientificDecision.BOUNDARY_RESULT,
        ),
        (
            _TemporalInterpretationCounts(
                material_recovery=SeedObservationCount(0),
                partial_or_weak_recovery=SeedObservationCount(0),
                without_recovery=SeedObservationCount(10),
                opposite=SeedObservationCount(0),
                no_degradation=SeedObservationCount(0),
                blocked=SeedObservationCount(0),
            ),
            ScientificDecision.BOUNDARY_RESULT,
        ),
        (
            _TemporalInterpretationCounts(
                material_recovery=SeedObservationCount(0),
                partial_or_weak_recovery=SeedObservationCount(0),
                without_recovery=SeedObservationCount(0),
                opposite=SeedObservationCount(10),
                no_degradation=SeedObservationCount(0),
                blocked=SeedObservationCount(0),
            ),
            ScientificDecision.OPPOSITE_DIRECTION,
        ),
    ),
)
def test_negative_temporal_outcomes_cannot_be_classified_as_supported(
    counts: _TemporalInterpretationCounts, expected: ScientificDecision
) -> None:
    decision, _ = _campaign_decision_from_counts(
        counts,
        total=SeedObservationCount(10),
        defined_recovery_count=SeedObservationCount(10),
        cohort_size=SeedCount(10),
    )

    assert decision is expected
    assert decision is not ScientificDecision.SUPPORTED


def test_temporal_client_trajectory_uses_locked_historical_and_future_formulae() -> None:
    trajectory = TemporalClientTrajectory(
        seed=Seed(0),
        client=ClientIdentity(
            population=PopulationId.EDGE_TEMPORAL_CLIENTS,
            client_id=ClientIdentityToken("sensor_a"),
            identity_kind=PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS,
        ),
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        eligible=True,
        exclusion_reason=None,
        threshold_static=MetricValue(0.20),
        threshold_frozen=MetricValue(0.35),
        threshold_recalibrated=MetricValue(0.25),
        fpr_static=MetricValue(0.10),
        fpr_frozen=MetricValue(0.30),
        fpr_recalibrated=MetricValue(0.15),
    )

    assert trajectory.threshold_movement_recalibrated is not None
    assert trajectory.threshold_movement_recalibrated.value == pytest.approx(0.05)
    assert trajectory.fpr_movement_frozen is not None
    assert trajectory.fpr_movement_frozen.value == pytest.approx(0.20)
    assert trajectory.fpr_recovery is not None
    assert trajectory.fpr_recovery.value == pytest.approx(0.15)


def test_eligible_temporal_client_cannot_silently_omit_a_required_fpr() -> None:
    with pytest.raises(ValueError, match="eligible temporal clients"):
        TemporalClientTrajectory(
            seed=Seed(0),
            client=ClientIdentity(
                population=PopulationId.EDGE_TEMPORAL_CLIENTS,
                client_id=ClientIdentityToken("sensor_a"),
                identity_kind=PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS,
            ),
            threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
            eligible=True,
            exclusion_reason=None,
            threshold_static=MetricValue(0.20),
            threshold_frozen=MetricValue(0.35),
            threshold_recalibrated=MetricValue(0.25),
            fpr_static=MetricValue(0.10),
            fpr_frozen=None,
            fpr_recalibrated=MetricValue(0.15),
        )


def test_temporal_recovery_uses_the_locked_drift_and_recovery_formulae() -> None:
    recovery = TemporalRecoveryResult.model_construct(
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.40),
        recalibrated_future_cv=MetricValue(0.25),
        decision_protocol=LOCKED_TEMPORAL_DECISION_PROTOCOL,
        unavailable_reason=None,
    )

    assert recovery.drift_excess.value == pytest.approx(0.30)
    assert recovery.recovered_amount.value == pytest.approx(0.15)
    assert recovery.recovery_ratio is not None
    assert recovery.recovery_ratio.value == pytest.approx(0.5)

    nonmaterial = TemporalRecoveryResult.model_construct(
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.1499),
        recalibrated_future_cv=MetricValue(0.10),
        decision_protocol=LOCKED_TEMPORAL_DECISION_PROTOCOL,
        unavailable_reason=None,
    )
    assert nonmaterial.recovery_ratio is None
    assert nonmaterial.availability is AvailabilityStatus.UNDEFINED

    # The locked claim-survival condition is `drift_excess >= 0.05`; at or above
    # the materiality threshold the recovery ratio remains defined.
    at_materiality = TemporalRecoveryResult.model_construct(
        static_reference_cv=MetricValue(0.10),
        frozen_future_cv=MetricValue(0.1501),
        recalibrated_future_cv=MetricValue(0.10),
        decision_protocol=LOCKED_TEMPORAL_DECISION_PROTOCOL,
        unavailable_reason=None,
    )
    assert at_materiality.recovery_ratio is not None
    assert at_materiality.recovery_ratio.value == pytest.approx(1.0)
