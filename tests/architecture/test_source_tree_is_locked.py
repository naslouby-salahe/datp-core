from pathlib import Path, PurePosixPath

import pytest

APPROVED_SOURCE_FILES = frozenset(
    """
__init__.py
analysis/__init__.py
analysis/decision_rules.py
analysis/descriptive.py
analysis/divergence.py
analysis/inference.py
analysis/mechanisms.py
analysis/temporal.py
anchor/__init__.py
anchor/comparison.py
anchor/gate.py
anchor/models.py
anchor/reproduction.py
artifacts/__init__.py
artifacts/completion.py
artifacts/coordinates.py
artifacts/layout.py
artifacts/manifest.py
artifacts/reload_validation.py
artifacts/serialization.py
artifacts/store.py
calibration/__init__.py
calibration/eligibility.py
calibration/models.py
calibration/sampling.py
centralized_reference/__init__.py
centralized_reference/checkpointing.py
centralized_reference/evaluation.py
centralized_reference/preprocessing.py
centralized_reference/scoring.py
centralized_reference/thresholding.py
centralized_reference/training.py
cli.py
datasets/__init__.py
datasets/capabilities.py
datasets/catalogue.py
datasets/ciciot2023/__init__.py
datasets/ciciot2023/capabilities.py
datasets/ciciot2023/materialize.py
datasets/ciciot2023/reader.py
datasets/ciciot2023/schema.py
datasets/edge_iiotset/__init__.py
datasets/edge_iiotset/capabilities.py
datasets/edge_iiotset/chronology.py
datasets/edge_iiotset/materialize.py
datasets/edge_iiotset/reader.py
datasets/edge_iiotset/schema.py
datasets/models.py
datasets/nbaiot/__init__.py
datasets/nbaiot/capabilities.py
datasets/nbaiot/materialize.py
datasets/nbaiot/reader.py
datasets/nbaiot/schema.py
domain/__init__.py
domain/contracts.py
domain/enums.py
domain/errors.py
domain/provenance.py
domain/values.py
evaluation/__init__.py
evaluation/client_metrics.py
evaluation/cohorts.py
evaluation/communication.py
evaluation/conformal_coverage.py
evaluation/confusion.py
evaluation/controls.py
evaluation/metric_semantics.py
evaluation/models.py
evaluation/operational.py
evaluation/population_metrics.py
evaluation/threshold_estimation.py
evaluation/traffic_rates.py
experiments/__init__.py
experiments/feasibility.py
experiments/models.py
experiments/planner.py
learning/__init__.py
learning/autoencoder.py
learning/federated/__init__.py
learning/federated/checkpointing.py
learning/federated/ditto.py
learning/federated/fedavg.py
learning/federated/fedprox.py
learning/federated/models.py
learning/federated/training.py
orchestration/__init__.py
orchestration/campaign.py
orchestration/definitions.py
orchestration/hooks.py
orchestration/resources.py
orchestration/stages/__init__.py
orchestration/stages/analyze.py
orchestration/stages/calibrate.py
orchestration/stages/construct_centralized_reference_threshold.py
orchestration/stages/construct_federated_thresholds.py
orchestration/stages/construct_population.py
orchestration/stages/evaluate_centralized_reference.py
orchestration/stages/evaluate_federated.py
orchestration/stages/finalize.py
orchestration/stages/materialize.py
orchestration/stages/preflight.py
orchestration/stages/preprocess_centralized_reference.py
orchestration/stages/preprocess_federated.py
orchestration/stages/report.py
orchestration/stages/score_centralized_reference.py
orchestration/stages/score_federated.py
orchestration/stages/select_centralized_reference_checkpoint.py
orchestration/stages/select_federated_checkpoint.py
orchestration/stages/split.py
orchestration/stages/train_centralized_reference.py
orchestration/stages/train_federated.py
orchestration/stages/verify_anchor.py
populations/__init__.py
populations/capabilities.py
populations/catalogue.py
populations/ciciot_file_clients.py
populations/edge_sensor_groups.py
populations/edge_temporal_groups.py
populations/integrity.py
populations/models.py
populations/nbaiot_dirichlet_clients.py
populations/nbaiot_natural_devices.py
populations/splits.py
preprocessing/__init__.py
preprocessing/federated.py
preprocessing/models.py
preprocessing/validation.py
protocols/__init__.py
protocols/anchor.py
protocols/calibration.py
protocols/experiments.py
protocols/metrics.py
protocols/models.py
protocols/populations.py
protocols/runtime.py
protocols/seeds.py
protocols/splits.py
protocols/statistics.py
protocols/traffic_rates.py
protocols/training.py
protocols/validation.py
reporting/__init__.py
reporting/export.py
reporting/figures.py
reporting/tables.py
reporting/validation.py
runtime/__init__.py
runtime/compute.py
runtime/determinism.py
runtime/logging.py
scoring/__init__.py
scoring/generation.py
scoring/models.py
scoring/reconstruction.py
thresholding/__init__.py
thresholding/conformal.py
thresholding/dispatch.py
thresholding/family.py
thresholding/federated_benign_statistics.py
thresholding/grouped.py
thresholding/local.py
thresholding/models.py
thresholding/quantiles.py
thresholding/shared.py
thresholding/shrinkage.py
""".split()
)
APPROVED_SOURCE_DIRECTORIES = frozenset(path.parent.as_posix() for path in map(PurePosixPath, APPROVED_SOURCE_FILES))


def source_tree_snapshot(source_root: Path) -> tuple[frozenset[str], frozenset[str]]:
    source_files = frozenset(path.relative_to(source_root).as_posix() for path in source_root.rglob("*.py"))
    source_directories = frozenset(
        path.relative_to(source_root).as_posix()
        for path in source_root.rglob("*")
        if path.is_dir() and path.name != "__pycache__"
    ) | frozenset((".",))
    return source_files, source_directories


def assert_source_tree_is_locked(source_files: frozenset[str], source_directories: frozenset[str]) -> None:
    assert source_files == APPROVED_SOURCE_FILES
    assert source_directories == APPROVED_SOURCE_DIRECTORIES


def test_approved_source_tree_is_locked() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    assert_source_tree_is_locked(*source_tree_snapshot(source_root))


@pytest.mark.parametrize(
    ("source_files", "source_directories"),
    (
        (
            APPROVED_SOURCE_FILES | frozenset(("domain/new_identity.py",)),
            APPROVED_SOURCE_DIRECTORIES,
        ),
        (
            APPROVED_SOURCE_FILES - frozenset(("domain/enums.py",)),
            APPROVED_SOURCE_DIRECTORIES,
        ),
        (
            APPROVED_SOURCE_FILES - frozenset(("domain/enums.py",)) | frozenset(("enums.py",)),
            APPROVED_SOURCE_DIRECTORIES | frozenset(("moved",)),
        ),
        (
            APPROVED_SOURCE_FILES - frozenset(("domain/enums.py",)) | frozenset(("domain/enums_renamed.py",)),
            APPROVED_SOURCE_DIRECTORIES,
        ),
        (APPROVED_SOURCE_FILES, APPROVED_SOURCE_DIRECTORIES | frozenset(("unexpected",))),
    ),
)
def test_source_tree_lock_rejects_added_missing_moved_or_renamed_files(
    source_files: frozenset[str], source_directories: frozenset[str]
) -> None:
    with pytest.raises(AssertionError):
        assert_source_tree_is_locked(source_files, source_directories)
