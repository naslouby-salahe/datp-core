from datp_core.protocols.runtime import DEFAULT_RUNTIME


def test_runtime_paths_are_project_relative_and_separated() -> None:
    assert str(DEFAULT_RUNTIME.data_root) == "data"
    assert str(DEFAULT_RUNTIME.outputs_root) == "outputs"
