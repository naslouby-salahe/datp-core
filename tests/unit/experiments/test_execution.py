from pathlib import Path

import pytest

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ExperimentId, FederatedThresholdMethod
from datp_core.core.numeric import Seed
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.execution.models import ExistingExperimentState
from datp_core.protocols.experiments import EXPERIMENTS


def _declaration(experiment_id: ExperimentId):
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    assert len(matches) == 1
    return matches[0]


class _AlwaysCompleteOutputStore:
    def state(self, coordinate, output_root, provenance=None) -> ExistingExperimentState:
        del coordinate, output_root, provenance
        return ExistingExperimentState.COMPLETE_VALID

    def delete(self, coordinate, output_root) -> None:
        raise AssertionError("a reused-complete coordinate must never be deleted")


def test_execute_declared_experiment_seed_returns_completed_threshold_methods(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "datp_core.experiments.execution.CompletionRecordOutputStore",
        _AlwaysCompleteOutputStore,
    )
    declaration = _declaration(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)

    result = execute_declared_experiment_seed(
        declaration=declaration,
        seed_cohort=SeedCohort(values=(Seed(0),)),
        reason="unit test exercises the shared execution primitive",
        output_root=tmp_path,
        overwrite=False,
    )

    assert result.completed_threshold_methods == (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
    )


def test_execute_declared_experiment_seed_raises_on_empty_campaign(tmp_path: Path) -> None:
    """DITTO uses joint publication, so the single-coordinate campaign is intentionally empty."""
    declaration = _declaration(ExperimentId.DITTO_ABSORPTION_STRESS_TEST)

    with pytest.raises(ScientificContractError):
        execute_declared_experiment_seed(
            declaration=declaration,
            seed_cohort=SeedCohort(values=(Seed(0),)),
            reason="unit test exercises the empty-campaign failure path",
            output_root=tmp_path,
            overwrite=False,
        )
