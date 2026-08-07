"""Full-programme smoke must surface an anchor gate failure instead of hiding it.

``run_smoke`` reports ``anchor_failure`` for both failure shapes: an anchor
command that raises, and one that returns a non-pass gate status without
raising. Experiments still run so smoke remains a per-experiment execution
check; the blocked prerequisite is surfaced, not absorbed.
"""

from pathlib import Path

import pytest

from datp_core.anchor.models import AnchorGateStatus
from datp_core.domain.enums import ExperimentId, ExperimentReadiness
from datp_core.domain.errors import AnchorReproductionError
from datp_core.domain.values.counts import Seed
from datp_core.pipeline.workflows import campaign


def _passed() -> campaign.AnchorCommandResult:
    return campaign.AnchorCommandResult(
        gate_status=AnchorGateStatus.PASS,
        dependent_readiness=ExperimentReadiness.DECLARED,
        detail="stub",
    )


def _blocked(detail: str = "gate blocked") -> campaign.AnchorCommandResult:
    return campaign.AnchorCommandResult(
        gate_status=AnchorGateStatus.BLOCKED,
        dependent_readiness=ExperimentReadiness.BLOCKED,
        detail=detail,
    )


def _stub_experiment(experiment_id: ExperimentId) -> campaign.ExperimentRunResult:
    return campaign.ExperimentRunResult(
        experiment=experiment_id,
        seeds=(Seed(0),),
        smoke=True,
        output_root=Path("."),
        detail="stub",
        method_outcomes=(),
    )


def _stub_reproduce_passed(*, overwrite: bool, smoke: bool) -> campaign.AnchorCommandResult:
    del overwrite, smoke
    return _passed()


def _stub_reproduce_blocked(*, overwrite: bool, smoke: bool) -> campaign.AnchorCommandResult:
    del overwrite, smoke
    return _blocked()


def _stub_verify(*, smoke: bool) -> campaign.AnchorCommandResult:
    del smoke
    return _passed()


def _stub_publish(results) -> None:
    del results


def _stub_run_experiment(experiment_id: ExperimentId, *, overwrite: bool, smoke: bool) -> campaign.ExperimentRunResult:
    del overwrite, smoke
    return _stub_experiment(experiment_id)


def _isolate_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(campaign, "_publish_smoke_summary", _stub_publish)
    monkeypatch.setattr(campaign, "run_experiment", _stub_run_experiment)


def test_smoke_surfaces_an_anchor_failure_raised_by_reproduction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing(*, overwrite: bool, smoke: bool) -> campaign.AnchorCommandResult:
        del overwrite, smoke
        raise AnchorReproductionError("independent reproduction failed")

    _isolate_smoke(monkeypatch)
    monkeypatch.setattr(campaign, "reproduce_anchor", failing)
    monkeypatch.setattr(campaign, "verify_anchor_programme", _stub_verify)

    result = campaign.run_smoke(overwrite=False)

    assert result.anchor_failure == "independent reproduction failed"
    assert len(result.experiments) == len(campaign._CAMPAIGN_ORDER)


def test_smoke_surfaces_a_blocked_gate_returned_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_smoke(monkeypatch)
    monkeypatch.setattr(campaign, "reproduce_anchor", _stub_reproduce_blocked)
    monkeypatch.setattr(campaign, "verify_anchor_programme", _stub_verify)

    result = campaign.run_smoke(overwrite=False)

    assert result.anchor_failure == "anchor gate blocked"


def test_smoke_reports_no_anchor_failure_when_the_gate_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_smoke(monkeypatch)
    monkeypatch.setattr(campaign, "reproduce_anchor", _stub_reproduce_passed)
    monkeypatch.setattr(campaign, "verify_anchor_programme", _stub_verify)

    result = campaign.run_smoke(overwrite=False)

    assert result.anchor_failure is None
