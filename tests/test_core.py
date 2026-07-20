from __future__ import annotations

from pathlib import Path

import pytest

from datp_core.artifacts.domain import ArtifactKind, PendingArtifact, ReusableArtifact
from datp_core.artifacts.filesystem import FilesystemArtifactStore
from datp_core.catalogue import load_resolved_configuration
from datp_core.catalogue.config.bundle import ConfigPaths
from datp_core.catalogue.config.load import load_authored_bundle
from datp_core.datasets.adapters.edge_iiotset import EdgeIiotsetAdapter
from datp_core.datasets.domain import ReadinessStatus
from datp_core.kernel.errors import ConfigurationError
from datp_core.kernel.fingerprints import fingerprint
from datp_core.kernel.ids import ClientId, DatasetId, ExperimentId
from datp_core.kernel.values import Probability
from datp_core.orchestration.planning import plan_all, plan_experiment
from datp_core.thresholding.domain import BenignCalibrationScores, ThresholdPolicyFamily
from datp_core.thresholding.services import estimate_thresholds

ROOT = Path(__file__).parents[1]


def test_complete_catalogue_resolves_and_every_experiment_plans() -> None:
    resolved = load_resolved_configuration(ROOT)
    counts = len(resolved.study.datasets), len(resolved.study.populations), len(resolved.study.experiments)
    assert counts == (3, 7, 23)
    assert len(plan_all(resolved)) == 23
    anchor = plan_experiment(resolved, ExperimentId("anchor_reproduction"))
    assert {run.seed_plan.bootstrap_analysis_seed for run in anchor.runs} == {42}


def test_duplicate_yaml_key_is_rejected(tmp_path: Path) -> None:
    paths = ConfigPaths.under(ROOT)
    duplicate = tmp_path / "nbaiot.yaml"
    duplicate.write_text(paths.nbaiot.read_text(encoding="utf-8") + "\ndataset: duplicate\n", encoding="utf-8")
    copied = ConfigPaths(
        nbaiot=duplicate,
        ciciot2023=paths.ciciot2023,
        edge_iiotset=paths.edge_iiotset,
        experiments=paths.experiments,
        protocols=paths.protocols,
        runtime=paths.runtime,
    )
    with pytest.raises(ConfigurationError, match="duplicate YAML key"):
        load_authored_bundle(copied)


def test_artifact_commit_is_checksum_verified_and_reused(tmp_path: Path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    scientific = fingerprint({"subject": "test"})
    pending = PendingArtifact(
        kind=ArtifactKind.SCORE_SET,
        scientific_fingerprint=scientific,
        execution_fingerprint=fingerprint({"workers": 1}),
        parents=(),
        logical_scope="test",
        payload=b"verified",
        source_revision="test",
        environment=(),
    )
    first = store.commit(pending)
    second = store.commit(pending)
    assert first == second
    reuse = store.find(ArtifactKind.SCORE_SET, scientific)
    assert isinstance(reuse, ReusableArtifact)
    assert reuse.ref == first


def test_thresholding_accepts_only_benign_calibration_references() -> None:
    calibration = (
        BenignCalibrationScores(client_id=ClientId("a"), values=(0.1, 0.2, 0.3)),
        BenignCalibrationScores(client_id=ClientId("b"), values=(0.3, 0.4, 0.5)),
    )
    values = estimate_thresholds(
        ThresholdPolicyFamily.SHRINKAGE,
        calibration,
        Probability(0.95),
        shrinkage_weight=Probability(0.5),
    )
    assert len(values.values) == 2
    assert all(value.owner == "local_global" for value in values.values)


def test_edge_adapter_inspects_bounded_real_source_fixture() -> None:
    resolved = load_resolved_configuration(ROOT)
    definition = resolved.study.datasets.get(DatasetId("edge_iiotset"))
    report = EdgeIiotsetAdapter().inspect(definition, ROOT / "data/raw", max_files=2)
    assert report.status is ReadinessStatus.READY
    assert len(report.source_files) == 2
    assert report.schema is not None and report.schema.header_consistent
