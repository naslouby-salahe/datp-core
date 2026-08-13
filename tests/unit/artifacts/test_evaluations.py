from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from datp_core.analysis.metrics.federated import FederatedEvaluationPublication
from datp_core.artifacts.repositories.evaluations import write_federated_evaluation
from datp_core.core.errors import ScientificContractError


def test_persisted_evaluation_requires_a_complete_execution_coordinate(tmp_path: Path) -> None:
    publication = cast(
        FederatedEvaluationPublication,
        SimpleNamespace(document=SimpleNamespace(execution_coordinate=None)),
    )

    with pytest.raises(ScientificContractError, match="requires a complete execution coordinate"):
        write_federated_evaluation(publication, tmp_path)
