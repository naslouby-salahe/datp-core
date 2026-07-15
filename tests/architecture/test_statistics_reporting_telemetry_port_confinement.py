from pathlib import Path

import pytest


@pytest.mark.architecture
def test_statistics_reporting_and_telemetry_ports_are_framework_neutral() -> None:
    ports_root = Path(__file__).parents[2] / "src" / "datp_core" / "application" / "ports"
    port_files = tuple(ports_root / name for name in ("statistics.py", "reporting.py", "telemetry.py"))
    forbidden_fragments = (
        "scipy",
        "matplotlib",
        "plotly",
        "seaborn",
        "reportlab",
        "weasyprint",
        "infrastructure",
    )

    for port_file in port_files:
        source = port_file.read_text().casefold()
        assert not any(fragment in source for fragment in forbidden_fragments)
