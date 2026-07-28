from datp_core.protocols.models import DATA_ROOT, OUTPUTS_ROOT, RESULTS_ROOT
from datp_core.protocols.runtime import DEFAULT_RUNTIME


def test_runtime_paths_are_project_relative_and_separated() -> None:
    assert DEFAULT_RUNTIME.data_root == DATA_ROOT
    assert DEFAULT_RUNTIME.outputs_root == OUTPUTS_ROOT
    assert DEFAULT_RUNTIME.results_root == RESULTS_ROOT
