from pathlib import Path
from typing import cast

import polars as pl
import pytest
from pydantic import TypeAdapter
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.cohorts import EvaluationCohortManifest
from datp_core.analysis.metrics.fixed_score_construction import build_federated_evaluation_inputs
from datp_core.analysis.metrics.fixed_score_validation import (
    validate_evaluation_evidence,
    validate_fixed_score_controls,
)
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    FederatedThresholdMethod,
    PartitionRole,
    ScoreFrameColumn,
    SerializationFormat,
    StableRowId,
)
from datp_core.core.numeric import FeatureCount, RowCount, Seed
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.detector.scoring.contracts import ScoreArtifactManifest, ScoreRecord


def _score_manifest(directory: Path) -> ScoreArtifactManifest:
    coordinate = fedavg_coordinate(Seed(0))
    client = client_identity("client_a")
    calibration_path = directory / "calibration.parquet"
    evaluation_path = directory / "evaluation.parquet"
    directory.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: [str(StableRowId("calibration-0"))],
            ScoreFrameColumn.OUTCOME_LABEL.value: [PopulationOutcomeLabel.BENIGN.value],
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: [0.2],
        }
    ).write_parquet(calibration_path)
    pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: [
                str(StableRowId("evaluation-0")),
                str(StableRowId("evaluation-1")),
            ],
            ScoreFrameColumn.OUTCOME_LABEL.value: [
                PopulationOutcomeLabel.BENIGN.value,
                PopulationOutcomeLabel.ATTACK.value,
            ],
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: [0.3, 0.8],
        }
    ).write_parquet(evaluation_path)
    calibration = ScoreRecord(
        coordinate=coordinate,
        partition_role=PartitionRole.CALIBRATION,
        path=calibration_path,
        row_count=RowCount(1),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
        scored_client=client,
    )
    evaluation = ScoreRecord(
        coordinate=coordinate,
        partition_role=PartitionRole.EVALUATION,
        path=evaluation_path,
        row_count=RowCount(2),
        feature_count=FeatureCount(4),
        serialization_format=SerializationFormat.PARQUET,
        scored_client=client,
    )
    return ScoreArtifactManifest(
        coordinate=coordinate,
        scored_split_protocol=coordinate.split_protocol,
        calibration_records=(calibration,),
        evaluation_records=(evaluation,),
    )


def test_threshold_policies_receive_one_shared_terminal_score_manifest(tmp_path: Path) -> None:
    manifest = _score_manifest(tmp_path)
    methods = (
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
        FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
    )

    inputs = tuple(build_federated_evaluation_inputs(manifest, method) for method in methods)

    assert all(item.fixed_score_evidence.score_manifest is manifest for item in inputs)


def test_unparameterized_score_record_deserialization_reconstructs_domain_values(tmp_path: Path) -> None:
    record = _score_manifest(tmp_path).calibration_records[0]
    adapter = TypeAdapter(ScoreRecord)

    restored = adapter.validate_python(adapter.dump_python(record, mode="json"))

    assert restored.coordinate == record.coordinate
    assert restored.scored_client == record.scored_client


def test_fixed_score_controls_survive_serialization_reload(tmp_path: Path) -> None:
    manifest = _score_manifest(tmp_path)
    shared = build_federated_evaluation_inputs(manifest, FederatedThresholdMethod.SHARED_THRESHOLD).fixed_score_evidence
    local = build_federated_evaluation_inputs(manifest, FederatedThresholdMethod.LOCAL_THRESHOLD).fixed_score_evidence
    adapter = TypeAdapter(type(shared))
    restored_local = adapter.validate_python(adapter.dump_python(local, mode="json"))

    assert restored_local.score_manifest is not shared.score_manifest
    validate_fixed_score_controls(shared, restored_local)


def test_fixed_score_evidence_rejects_mutated_persisted_score_artifacts(tmp_path: Path) -> None:
    manifest = _score_manifest(tmp_path)
    evidence = build_federated_evaluation_inputs(
        manifest, FederatedThresholdMethod.SHARED_THRESHOLD
    ).fixed_score_evidence
    evaluation = manifest.evaluation_records[0]
    pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: ["evaluation-0", "evaluation-1"],
            ScoreFrameColumn.OUTCOME_LABEL.value: [
                PopulationOutcomeLabel.BENIGN.value,
                PopulationOutcomeLabel.ATTACK.value,
            ],
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: [0.3, 0.9],
        }
    ).write_parquet(evaluation.path)

    with pytest.raises(ScientificContractError, match="persisted score-artifact content"):
        validate_evaluation_evidence(evidence, manifest, cast(EvaluationCohortManifest, None), ())
