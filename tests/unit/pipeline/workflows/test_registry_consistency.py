import pytest

from datp_core.domain.enums import ExperimentId
from datp_core.domain.errors import ReportEvidenceError, ScientificContractError
from datp_core.pipeline.workflows import ANCHOR_GATED_EXPERIMENTS, REGISTERED_WORKFLOW_EXPERIMENTS, campaign
from datp_core.protocols.experiments import EXPERIMENTS

_DECLARED_BUT_UNREGISTERED_EXPERIMENT = ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY

_EXPECTED_CAMPAIGN_ORDER = (
    ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
    ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
    ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
    ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
    ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
    ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
    ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
)

_EXPECTED_ANCHOR_GATED_EXPERIMENTS = frozenset(
    (
        ExperimentId.SHARED_VS_LOCAL_CONFIRMATION,
        ExperimentId.FAMILY_AND_GROUPED_GRANULARITY,
        ExperimentId.FEDPROX_ABSORPTION_STRESS_TEST,
        ExperimentId.DITTO_ABSORPTION_STRESS_TEST,
    )
)


def test_declared_but_unregistered_fixture_is_actually_unregistered() -> None:
    assert _DECLARED_BUT_UNREGISTERED_EXPERIMENT in tuple(item.id for item in EXPERIMENTS)
    assert _DECLARED_BUT_UNREGISTERED_EXPERIMENT not in REGISTERED_WORKFLOW_EXPERIMENTS


def test_campaign_order_matches_the_locked_execution_sequence() -> None:
    assert campaign._CAMPAIGN_ORDER == _EXPECTED_CAMPAIGN_ORDER


def test_campaign_order_and_registered_workflows_cannot_drift() -> None:
    assert frozenset(campaign._CAMPAIGN_ORDER) == REGISTERED_WORKFLOW_EXPERIMENTS
    assert len(campaign._CAMPAIGN_ORDER) == len(REGISTERED_WORKFLOW_EXPERIMENTS)


def test_anchor_gated_experiments_are_locked_and_a_subset_of_registered_workflows() -> None:
    assert ANCHOR_GATED_EXPERIMENTS == _EXPECTED_ANCHOR_GATED_EXPERIMENTS
    assert ANCHOR_GATED_EXPERIMENTS <= REGISTERED_WORKFLOW_EXPERIMENTS


def test_execution_dispatch_table_covers_exactly_the_registered_workflows() -> None:
    assert frozenset(campaign._EXPERIMENT_DISPATCH_HANDLERS) == REGISTERED_WORKFLOW_EXPERIMENTS


def test_report_dispatch_table_covers_exactly_the_registered_workflows() -> None:
    assert frozenset(campaign._EXPERIMENT_REPORT_HANDLERS) == REGISTERED_WORKFLOW_EXPERIMENTS


def test_dispatch_experiment_rejects_an_unregistered_id_instead_of_silently_matching() -> None:
    with pytest.raises(ScientificContractError):
        campaign._dispatch_experiment(
            _DECLARED_BUT_UNREGISTERED_EXPERIMENT,
            seeds=(),
            output_root=campaign.OUTPUTS_ROOT,
            overwrite=False,
        )


def test_generate_experiment_report_rejects_an_unregistered_id_instead_of_silently_matching() -> None:
    with pytest.raises(ReportEvidenceError):
        campaign._generate_experiment_report(_DECLARED_BUT_UNREGISTERED_EXPERIMENT, overwrite=False)


def test_analysis_marker_present_is_callable_for_every_registered_workflow_without_raising() -> None:
    for experiment_id in REGISTERED_WORKFLOW_EXPERIMENTS:
        assert isinstance(campaign._analysis_marker_present(experiment_id), bool)


def test_analysis_marker_checks_are_declared_only_for_registered_workflows() -> None:
    assert frozenset(campaign._ANALYSIS_MARKER_CHECKS) <= REGISTERED_WORKFLOW_EXPERIMENTS
