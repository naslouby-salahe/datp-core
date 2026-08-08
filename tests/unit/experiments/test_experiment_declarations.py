from datp_core.core.identifiers import EvidenceRole, ExperimentId
from datp_core.experiments.registry import EXPERIMENTS


def test_exactly_one_confirmatory_experiment_exists() -> None:
    assert tuple(item.role for item in EXPERIMENTS).count(EvidenceRole.CONFIRMATORY) == 1
    assert tuple(item.id for item in EXPERIMENTS) == tuple(ExperimentId)
