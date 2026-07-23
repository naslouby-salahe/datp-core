from __future__ import annotations

import base64
import json

from datp_core.reporting.freezing import freeze_result_family
from datp_core.reporting.rendering import render_frozen_report
from datp_core.bootstrap import build_application
from datp_core.pipeline.identifiers import ExperimentId
from datp_core.pipeline.models import StageJobContext, StageKind
from datp_core.experiments.planning import expand_experiment_jobs
from datp_core.experiments.identity import IdentityBuilder


def test_result_freeze_requires_every_configured_analysis_before_rendering() -> None:
    app = build_application()
    experiment = app.config.experiments.get(ExperimentId("confirmatory_threshold_scope_effect"))
    profiles = tuple(app.config.report_profiles.get(identifier) for identifier in experiment.report_ids)
    records = [
        {
            "analysis_label": analysis.label,
            "first_threshold_policy": "shared_mean_p95",
            "second_threshold_policy": "local_p95",
            "first_mean": 0.2,
            "mean_difference": 0.1,
            "confidence_interval": [0.01, 0.2],
            "sign_consistency": 0.9,
            "seed_differences": [0.1, 0.2],
            "seed": s,
        }
        for s in range(5)
        for analysis in experiment.analyses
    ]
    context = StageJobContext(experiment_id=experiment.identifier)
    payload = freeze_result_family(
        experiment=experiment,
        report_profiles=profiles,
        statistical_summary=json.dumps(records).encode("utf-8"),
        source_artifacts=(IdentityBuilder.statistical_summary_key(context),),
        scientific_fingerprint=app.config.scientific_fingerprint.value,
        execution_fingerprint=app.config.execution_fingerprint.value,
        source_revision="test",
        seed_count=5,
    )

    report = json.loads(render_frozen_report(payload))

    assert report["experiment_id"] == experiment.identifier.value
    table = next(item for item in report["rendered_artifacts"] if item["artifact_type"] == "table")
    assert "shared\\_mean\\_p95" in table["outputs"]["latex"]
    figure = next(item for item in report["rendered_artifacts"] if item["artifact_type"] == "figure")
    assert base64.b64decode(figure["outputs"]["png_base64"]).startswith(b"\x89PNG")
    assert base64.b64decode(figure["outputs"]["pdf_base64"]).startswith(b"%PDF")


def test_planning_freezes_results_before_report_generation() -> None:
    app = build_application()
    graph = expand_experiment_jobs(app.config.experiments.get(ExperimentId("centralized_pooled_reference")), app.config)
    result_freeze = next(job for job in graph.jobs if job.stage is StageKind.RESULT_FREEZE)
    report = next(job for job in graph.jobs if job.stage is StageKind.REPORT_GENERATION)

    assert result_freeze.job_id in report.dependencies
    assert result_freeze.output in report.inputs
