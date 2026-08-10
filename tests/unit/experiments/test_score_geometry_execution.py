from types import SimpleNamespace

import pytest

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.numeric import Seed
from datp_core.experiments.confirmatory import run


def test_score_geometry_blocks_when_a_required_threshold_overlay_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def load_document(_: object) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise ScientificContractError(ErrorMessage("cluster evaluation is absent"))
        return SimpleNamespace(clients=())

    monkeypatch.setattr(run, "_evaluation_path", lambda *_: object())
    monkeypatch.setattr(run, "load_evaluation_document", load_document)

    seed = Seed(202)
    with pytest.raises(ScientificContractError, match="cluster evaluation is absent"):
        run._score_geometry_threshold_overlays(seed, ())
