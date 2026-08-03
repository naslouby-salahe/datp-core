from pathlib import Path

from tests.unit.calibration.helpers import benign_score_record

from datp_core.calibration.eligibility import (
    calibration_support,
    decide_eligibility,
    load_benign_calibration_references,
)
from datp_core.calibration.models import EligibilityStatus
from datp_core.domain.enums import (
    CapabilityStatus,
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    PublicationStatus,
)
from datp_core.domain.values import CalibrationSize, ClientCount, Quantile, SubsampleReplicateCount
from datp_core.orchestration.stages.calibrate import CalibrateRequest, calibrate_stage
from datp_core.orchestration.stages.construct_federated_thresholds import (
    ConstructFederatedThresholdsAssetName,
    ConstructFederatedThresholdsRequest,
    construct_federated_thresholds_stage,
)
from datp_core.populations.models import PopulationCapabilities
from datp_core.protocols.models import CalibrationEligibilityProtocol
from datp_core.scoring.models import FixedScoreInvariant, ScoreArtifactManifest
from datp_core.thresholding.dispatch import ThresholdConstructionRequest
from datp_core.thresholding.quantiles import calibration_scores_from_references

PROTOCOL = CalibrationEligibilityProtocol(minimum_support=CalibrationSize(100))
SIZES = (CalibrationSize(50), CalibrationSize(100))


def _manifest(tmp_path: Path) -> ScoreArtifactManifest:
    calibration_a = benign_score_record(tmp_path, "client_a", tuple(float(i) for i in range(150)))
    calibration_b = benign_score_record(tmp_path, "client_b", (0.1, 0.2, 0.3))
    evaluation_a = benign_score_record(tmp_path, "client_a", (1.0, 2.0), partition_role=PartitionRole.EVALUATION)
    evaluation_b = benign_score_record(tmp_path, "client_b", (1.0, 2.0), partition_role=PartitionRole.EVALUATION)
    return ScoreArtifactManifest(
        coordinate=calibration_a.coordinate,
        checkpoint_round=calibration_a.checkpoint_round,
        checkpoint_checksum=calibration_a.checkpoint_checksum,
        preprocessing_state_set_checksum=calibration_a.checksum,
        split_manifest_checksum=calibration_a.checksum,
        calibration_records=(calibration_a, calibration_b),
        evaluation_records=(evaluation_a, evaluation_b),
    )


def test_calibrate_stage_marks_sufficient_client_eligible_and_insufficient_client_excluded(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    result = calibrate_stage(
        CalibrateRequest(
            score_manifest=manifest,
            protocol=PROTOCOL,
            calibration_sizes=SIZES,
            replicate_count=SubsampleReplicateCount(2),
        )
    )
    statuses = {decision.client.client_id: decision.status for decision in result.eligibility}
    assert statuses["client_a"] is EligibilityStatus.ELIGIBLE
    assert statuses["client_b"] is EligibilityStatus.EXCLUDED
    assert [client.client_id for client in result.eligible_clients] == ["client_a"]
    assert len(result.replicate_manifests) == 2  # two replicates for the one eligible client


def test_calibrate_stage_produces_nested_deterministic_replicates(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    result = calibrate_stage(
        CalibrateRequest(
            score_manifest=manifest,
            protocol=PROTOCOL,
            calibration_sizes=SIZES,
            replicate_count=SubsampleReplicateCount(1),
        )
    )
    replicate = result.replicate_manifests[0]
    sizes = {subsample.size.value: subsample.stable_row_id_set for subsample in replicate.subsamples}
    assert sizes[50] <= sizes[100]


def _capabilities() -> PopulationCapabilities:
    return PopulationCapabilities(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
        declared_client_count=ClientCount(1),
        physical_client_validity=CapabilityStatus.SUPPORTED,
        family_taxonomy=CapabilityStatus.SUPPORTED,
        chronology=CapabilityStatus.UNAVAILABLE,
        client_level_attack_assignment=CapabilityStatus.SUPPORTED,
        fpr_evaluation=CapabilityStatus.SUPPORTED,
        attack_sensitive_evaluation=CapabilityStatus.SUPPORTED,
        temporal_support=CapabilityStatus.UNAVAILABLE,
        valid_threshold_methods=(FederatedThresholdMethod.SHARED_THRESHOLD,),
        evidentiary_role=EvidenceRole.CONFIRMATORY,
        confirmatory_eligible=True,
    )


def _threshold_request(tmp_path: Path, quantile: Quantile) -> ThresholdConstructionRequest:
    manifest = _manifest(tmp_path)
    invariant = FixedScoreInvariant.from_manifest(manifest)
    calibration_record = manifest.calibration_records[0]
    references = load_benign_calibration_references(calibration_record)
    support = calibration_support(calibration_record, references, invariant.calibration_score_set_checksum)
    decision = decide_eligibility(support, PROTOCOL)
    assert decision.status is EligibilityStatus.ELIGIBLE
    client_scores = calibration_scores_from_references(
        calibration_record.scored_client, manifest.coordinate, references, invariant.calibration_score_set_checksum
    )
    return ThresholdConstructionRequest(
        method=FederatedThresholdMethod.SHARED_THRESHOLD,
        coordinate=manifest.coordinate,
        quantile=quantile,
        capabilities=_capabilities(),
        eligible=(client_scores,),
        family_by_client=(),
    )


def test_construct_federated_thresholds_stage_publishes_then_reuses(tmp_path: Path) -> None:
    request = _threshold_request(tmp_path, Quantile(0.5))
    output_directory = tmp_path / "threshold_output"
    stage_request = ConstructFederatedThresholdsRequest(
        request=request, output_directory=output_directory, overwrite=False
    )

    first = construct_federated_thresholds_stage(stage_request)
    assert first.publication_status is PublicationStatus.PUBLISHED

    second = construct_federated_thresholds_stage(stage_request)
    assert second.publication_status is PublicationStatus.REUSED
    assert second.result == first.result


def test_construct_federated_thresholds_stage_rebuilds_when_result_document_is_missing(tmp_path: Path) -> None:
    request = _threshold_request(tmp_path, Quantile(0.5))
    output_directory = tmp_path / "threshold_output"
    stage_request = ConstructFederatedThresholdsRequest(
        request=request, output_directory=output_directory, overwrite=False
    )

    construct_federated_thresholds_stage(stage_request)
    (output_directory / ConstructFederatedThresholdsAssetName.RESULT).unlink()

    result = construct_federated_thresholds_stage(stage_request)
    assert result.publication_status is PublicationStatus.PUBLISHED
    assert (output_directory / ConstructFederatedThresholdsAssetName.RESULT).is_file()


def test_construct_federated_thresholds_stage_overwrite_forces_rebuild(tmp_path: Path) -> None:
    request = _threshold_request(tmp_path, Quantile(0.5))
    output_directory = tmp_path / "threshold_output"
    first_stage_request = ConstructFederatedThresholdsRequest(
        request=request, output_directory=output_directory, overwrite=False
    )
    construct_federated_thresholds_stage(first_stage_request)

    overwrite_stage_request = ConstructFederatedThresholdsRequest(
        request=request, output_directory=output_directory, overwrite=True
    )
    result = construct_federated_thresholds_stage(overwrite_stage_request)
    assert result.publication_status is PublicationStatus.PUBLISHED
