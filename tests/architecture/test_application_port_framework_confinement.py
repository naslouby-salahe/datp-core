from pathlib import Path

import pytest


@pytest.mark.architecture
def test_data_learning_scoring_and_thresholding_ports_are_framework_neutral() -> None:
    ports_root = Path(__file__).parents[2] / "src" / "datp_core" / "application" / "ports"
    port_files = tuple(ports_root / name for name in ("data.py", "learning.py", "scoring.py", "thresholding.py"))
    forbidden_frameworks = ("numpy", "pandas", "pyarrow", "torch", "sklearn", "flwr")

    for port_file in port_files:
        source = port_file.read_text().casefold()
        assert not any(framework in source for framework in forbidden_frameworks)
