from types import SimpleNamespace
from typing import cast

import pytest
from tests.unit.thresholding.helpers import identity

from datp_core.analysis.mechanisms.equity_pareto import EquityTargetAttainmentRow, EquityUtilityParetoView
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId
from datp_core.core.numeric import MetricValue, Ratio, Seed
from datp_core.presentation.target_attainment import (
    render_confirmatory_operating_point_table,
    render_target_attainment_table,
)


def test_target_attainment_table_renders_the_reconstructable_policy_values() -> None:
    row = EquityTargetAttainmentRow(
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        seed_mean_absolute_target_errors=(MetricValue(0.1),),
        seed_worst_absolute_target_errors=(MetricValue(0.2),),
        seed_mean_absolute_calibration_generalization_gaps=(MetricValue(0.05),),
        mean_absolute_target_error=MetricValue(0.1),
        worst_absolute_target_error=MetricValue(0.2),
        mean_absolute_calibration_generalization_gap=MetricValue(0.05),
    )
    view = EquityUtilityParetoView(utility_metric=MetricId.P10_BINARY_MACRO_F1, points=(), target_attainment=(row,))

    rendered = render_target_attainment_table(view)

    assert "`shared_threshold` | 0.1 | 0.2 | 0.05 | 1" in rendered


def _confirmatory_document(seed: int, method: FederatedThresholdMethod) -> FederatedEvaluationDocument:
    diagnostic = SimpleNamespace(
        client=identity("client_0"),
        calibration_exceedance=Ratio(0.1),
        signed_calibration_target_error=MetricValue(0.05),
        signed_target_error=MetricValue(0.15),
        absolute_target_error=MetricValue(0.15),
        signed_calibration_generalization_gap=MetricValue(0.1),
    )
    return cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            threshold_method=method,
            score_coordinate=SimpleNamespace(training_seed=Seed(seed)),
            diagnostics=SimpleNamespace(held_out_operating_points=(diagnostic,)),
        ),
    )


def test_confirmatory_operating_point_table_renders_each_seed_policy_and_client() -> None:
    rendered = render_confirmatory_operating_point_table(
        (
            _confirmatory_document(2, FederatedThresholdMethod.LOCAL_THRESHOLD),
            _confirmatory_document(2, FederatedThresholdMethod.SHARED_THRESHOLD),
            _confirmatory_document(1, FederatedThresholdMethod.LOCAL_THRESHOLD),
            _confirmatory_document(1, FederatedThresholdMethod.SHARED_THRESHOLD),
        ),
        (Seed(1), Seed(2)),
    )

    assert "design-level falsification record, not a hypothesis test" in rendered
    assert "| 1 | `local_threshold` | `client_0` | 0.1 | 0.05 | 0.15 | 0.15 | 0.1 |" in rendered
    assert rendered.index("| 1 | `local_threshold`") < rendered.index("| 2 | `local_threshold`")


def test_confirmatory_operating_point_table_rejects_an_incomplete_policy_pair() -> None:
    with pytest.raises(ScientificContractError, match="requires each declared shared/local seed pair"):
        render_confirmatory_operating_point_table(
            (_confirmatory_document(1, FederatedThresholdMethod.SHARED_THRESHOLD),),
            (Seed(1),),
        )
