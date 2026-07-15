from pathlib import Path

import pytest


@pytest.mark.architecture
def test_application_stages_do_not_touch_cuda_without_the_runtime_guard() -> None:
    stage_root = Path(__file__).parents[2] / "src" / "datp_core" / "application" / "stages"
    forbidden_fragments = ("torch", ".cuda", "cuda.")

    for stage_file in stage_root.glob("*.py"):
        source = stage_file.read_text().casefold()
        assert not any(fragment in source for fragment in forbidden_fragments), stage_file
