from pathlib import Path

from datp_core.pipeline.dagster import DEFINITIONS


def test_dagster_definitions_are_pipeline_backed() -> None:
    assert DEFINITIONS.resolve_job_def("datp_core_plan").name == "datp_core_plan"
    assert DEFINITIONS.resolve_job_def("datp_core_confirmatory").name == "datp_core_confirmatory"
    assert DEFINITIONS.resolve_job_def("datp_core_training_stress").name == "datp_core_training_stress"
    assert DEFINITIONS.resolve_job_def("datp_core_external_temporal").name == "datp_core_external_temporal"


def test_orchestration_package_is_deleted() -> None:
    root = Path(__file__).resolve().parents[3] / "src" / "datp_core" / "orchestration"
    assert not root.exists()


def test_dagster_assets_cover_workflow_surface() -> None:
    asset_keys = {key.to_user_string() for key in DEFINITIONS.resolve_all_asset_keys()}
    assert {
        "deterministic_plan",
        "confirmatory_campaign",
        "confirmatory_evidence",
        "centralized_reference_seed",
        "ditto_stress_campaign",
        "ditto_absorption_evidence",
        "fedprox_stress_campaign",
        "fedprox_absorption_evidence",
        "temporal_evidence_campaign",
        "edge_benign_equity_seed",
        "edge_benign_equity_analysis",
        "ciciot_boundary_seed",
        "ciciot_boundary_analysis",
    } == asset_keys


def test_pipeline_paths_resource_is_registered() -> None:
    from datp_core.pipeline.dagster import PIPELINE_PATHS

    assert PIPELINE_PATHS.data_root
    assert PIPELINE_PATHS.outputs_root
