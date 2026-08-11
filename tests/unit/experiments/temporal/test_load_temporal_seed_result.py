from pathlib import Path

import pytest

from datp_core.core.errors import ReportEvidenceError
from datp_core.core.numeric import Seed
from datp_core.experiments.temporal import load_temporal_seed_result


def test_load_temporal_seed_result_fails_explicitly_without_persisted_evaluations(tmp_path: Path) -> None:
    with pytest.raises(ReportEvidenceError):
        load_temporal_seed_result(Seed(0), output_root=tmp_path)
