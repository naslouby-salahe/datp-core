from pathlib import Path

from datp_core.pipeline.dagster import DEFINITIONS


def test_dagster_definitions_are_pipeline_backed() -> None:
    assert DEFINITIONS.resolve_job_def("datp_core_plan").name == "datp_core_plan"
    assert DEFINITIONS.resolve_job_def("datp_core_confirmatory").name == "datp_core_confirmatory"


def test_orchestration_package_is_deleted() -> None:
    root = Path(__file__).resolve().parents[3] / "src" / "datp_core" / "orchestration"
    assert not root.exists()


def test_no_pass_through_asset_remains() -> None:
    asset_keys = {key.to_user_string() for key in DEFINITIONS.resolve_all_asset_keys()}
    assert asset_keys == {"deterministic_plan", "confirmatory_campaign", "confirmatory_evidence"}
