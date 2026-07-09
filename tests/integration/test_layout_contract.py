from datp_core.utils.layout import validate_repo_layout
from datp_core.utils.paths import resolve_paths


def test_real_repo_resolves_and_satisfies_the_layout_contract():
    paths = resolve_paths()
    for name in ("configs", "data", "checkpoints", "outputs", "results"):
        assert (paths.repo_root / name).is_dir()

    result = validate_repo_layout(paths)
    assert result.passed, result.failures
    assert result.checks  # every check ran, not just an empty pass


def test_data_raw_is_a_symlink_never_committed_raw_content():
    paths = resolve_paths()
    assert paths.data_raw.is_symlink()
