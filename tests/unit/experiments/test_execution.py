from pathlib import Path

import pytest

from datp_core.app.planning import PlanReason
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ExperimentId
from datp_core.core.numeric import Seed
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution import execute_declared_experiment_seed
from datp_core.experiments.registry import EXPERIMENTS


def _declaration(experiment_id: ExperimentId):
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    assert len(matches) == 1
    return matches[0]


def test_execute_declared_experiment_seed_raises_on_empty_campaign(tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.DITTO_ABSORPTION_STRESS_TEST)
    with pytest.raises(ScientificContractError):
        execute_declared_experiment_seed(
            declaration=declaration,
            seed_cohort=SeedCohort(values=(Seed(0),)),
            reason=PlanReason("fixture"),
            output_root=tmp_path,
            overwrite=False,
        )
