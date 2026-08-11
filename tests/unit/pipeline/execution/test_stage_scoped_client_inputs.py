from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from datp_core.app.planning import PlanDisposition, PlanningEvidence, PlanReason, expand_experiment_plan
from datp_core.core.identifiers import ClientIdentityToken, ExperimentId, PopulationIdentityKind
from datp_core.core.numeric import Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.contracts import FederatedClientDataResidency
from datp_core.experiments.common.coordinates import ExperimentCoordinate
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution import workspace as workspace_module
from datp_core.experiments.execution.context import FederatedExecutionContext, training_coordinate_for
from datp_core.experiments.registry import EXPERIMENTS


def _coordinate() -> ExperimentCoordinate:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            ),
        ),
    )
    return plan.executable[0].coordinate


def _workspace(tmp_path: Path) -> workspace_module.ExperimentWorkspace:
    coordinate = _coordinate()
    client = ClientIdentity(
        coordinate.population, ClientIdentityToken("client_a"), PopulationIdentityKind.PHYSICAL_DEVICES
    )
    fixed_context = SimpleNamespace(
        preprocessing=SimpleNamespace(client_publications=()),
        clients=(client,),
        coordinate=training_coordinate_for(coordinate),
        family_by_client=(),
        training_directory=tmp_path,
        client_data_residency=FederatedClientDataResidency.STREAMING,
    )
    return workspace_module.ExperimentWorkspace(
        coordinate=coordinate,
        output_root=tmp_path,
        fixed_context=cast(FederatedExecutionContext, fixed_context),
    )


def test_training_client_inputs_are_released_once_training_completes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = _workspace(tmp_path)
    sentinel_training_inputs = ("training-inputs-sentinel",)
    fake_training_result = SimpleNamespace(training=SimpleNamespace())

    monkeypatch.setattr(workspace_module, "client_training_inputs", lambda *_args: sentinel_training_inputs)
    monkeypatch.setattr(workspace_module, "train_federated_detector", lambda _request: fake_training_result)

    assert workspace.training_client_inputs == sentinel_training_inputs
    assert "training_client_inputs" in workspace.__dict__

    result = workspace.training

    assert result is fake_training_result
    assert "training_client_inputs" not in workspace.__dict__


def test_scoring_client_inputs_are_released_once_scoring_completes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = _workspace(tmp_path)
    sentinel_scoring_inputs = ("scoring-inputs-sentinel",)
    fake_scores = SimpleNamespace()

    monkeypatch.setattr(workspace_module, "client_scoring_inputs", lambda *_args: sentinel_scoring_inputs)
    monkeypatch.setattr(workspace_module, "score_terminal_model", lambda **_kwargs: fake_scores)
    fake_fixed_training = SimpleNamespace(training=SimpleNamespace())
    workspace.fixed_training = cast(workspace_module.TrainFederatedDetectorResult, fake_fixed_training)

    assert workspace.scoring_client_inputs == sentinel_scoring_inputs
    assert "scoring_client_inputs" in workspace.__dict__

    result = workspace.scores

    assert result is fake_scores
    assert "scoring_client_inputs" not in workspace.__dict__
