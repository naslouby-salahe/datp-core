from pathlib import Path

from datp_core.orchestration.definitions import DEFINITIONS


def test_dagster_definitions_are_pipeline_backed() -> None:
    assert DEFINITIONS.get_job_def("datp_core_plan").name == "datp_core_plan"
    assert DEFINITIONS.get_job_def("datp_core_confirmatory").name == "datp_core_confirmatory"


def test_legacy_orchestration_spines_are_deleted() -> None:
    root = Path(__file__).resolve().parents[3] / "src" / "datp_core" / "orchestration"
    assert not (root / "commands").exists()
    assert not (root / "stages").exists()
