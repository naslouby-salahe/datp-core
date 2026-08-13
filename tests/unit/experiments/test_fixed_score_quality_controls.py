from types import SimpleNamespace
from typing import cast

import pytest

from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import MetricValue
from datp_core.experiments.heterogeneity import run


def test_fixed_score_quality_controls_require_invariance(monkeypatch: pytest.MonkeyPatch) -> None:
    shared = cast(FederatedEvaluationDocument, SimpleNamespace())
    local = cast(FederatedEvaluationDocument, SimpleNamespace())
    values = {
        (id(shared), MetricId.AUROC): MetricValue(0.9),
        (id(local), MetricId.AUROC): MetricValue(0.9),
        (id(shared), MetricId.AVERAGE_PRECISION): MetricValue(0.8),
        (id(local), MetricId.AVERAGE_PRECISION): MetricValue(0.7),
    }
    monkeypatch.setattr(run, "population_metric", lambda document, metric: values[(id(document), metric)])

    with pytest.raises(ScientificContractError, match="average_precision must be invariant"):
        run._verify_fixed_score_quality_control_invariance(shared, local)
