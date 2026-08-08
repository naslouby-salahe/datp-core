"""One frozen score artifact is reusable unchanged across threshold methods."""

from pathlib import Path

import numpy as np
from tests.unit.calibration.helpers import benign_score_record

from datp_core.artifacts.provenance import checksum_file
from datp_core.core.identifiers import (
    CheckpointStatus,
    DatasetId,
    EvidenceRole,
    FederatedThresholdMethod,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
)
from datp_core.core.numeric import CalibrationSize, ClientCount, Quantile
from datp_core.data.populations.contracts import CapabilityStatus, PopulationCapabilities
from datp_core.detector.scoring.contracts import FixedScoreInvariant, ScoreArtifactManifest
from datp_core.protocols.calibration import CalibrationEligibilityProtocol, CalibrationSupportRule
from datp_core.thresholds.calibration.eligibility import (
    EligibilityStatus,
    calibration_support,
    decide_eligibility,
    load_benign_calibration_references,
)
from datp_core.thresholds.dispatch import (
    ThresholdConstructionRequest,
    ThresholdConstructionResult,
    dispatch_federated_threshold,
)
from datp_core.thresholds.policies.local import LocalThresholdResult
from datp_core.thresholds.policies.shared import (
    PooledSharedQuantileResult,
    SampleWeightedSharedThresholdResult,
    SharedThresholdResult,
)
from datp_core.thresholds.quantiles import calibration_scores_from_references
from datp_core.thresholds.variants.conformal import ConformalThresholdResult

PROTOCOL = CalibrationEligibilityProtocol(minimum_support=CalibrationSize(100))
QUANTILE = Quantile(0.95)
CLIENT_IDS = ("client_a", "client_b", "client_c")


def _manifest(tmp_path: Path) -> ScoreArtifactManifest:
    generator = np.random.default_rng(0)
    calibration_records = tuple(
        benign_score_record(
            tmp_path,
            client_id,
            tuple(float(value) for value in generator.normal(size=150)),
        )
        for client_id in CLIENT_IDS
    )
    evaluation_records = tuple(
        benign_score_record(
            tmp_path,
            client_id,
            (1.0, 2.0),
            partition_role=PartitionRole.EVALUATION,
        )
        for client_id in CLIENT_IDS
    )
    return ScoreArtifactManifest(
        coordinate=calibration_records[0].coordinate,
        scored_split_protocol=calibration_records[0].coordinate.split_protocol,
        checkpoint_round=calibration_records[0].checkpoint_round,
        checkpoint_checksum=calibration_records[0].checkpoint_checksum,
        checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE,
        preprocessing_state_set_checksum=calibration_records[0].checksum,
        split_manifest_checksum=calibration_records[0].checksum,
        calibration_records=calibration_records,
        evaluation_records=evaluation_records,
    )


def _capabilities() -> PopulationCapabilities:
    return PopulationCapabilities(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
        declared_client_count=ClientCount(len(CLIENT_IDS)),
        physical_client_validity=CapabilityStatus.SUPPORTED,
        family_taxonomy=CapabilityStatus.SUPPORTED,
        chronology=CapabilityStatus.UNAVAILABLE,
        client_level_attack_assignment=CapabilityStatus.SUPPORTED,
        fpr_evaluation=CapabilityStatus.SUPPORTED,
        attack_sensitive_evaluation=CapabilityStatus.SUPPORTED,
        temporal_support=CapabilityStatus.UNAVAILABLE,
        valid_threshold_methods=tuple(FederatedThresholdMethod),
        evidentiary_role=EvidenceRole.CONFIRMATORY,
        confirmatory_eligible=True,
    )


def test_every_threshold_method_reads_the_same_frozen_score_artifact_unchanged(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    invariant = FixedScoreInvariant.from_manifest(manifest)
    checksums_before = tuple(
        (record.scored_client.client_id, checksum_file(record.path)) for record in manifest.calibration_records
    )
    eligible = tuple(_eligible_client_scores(record, manifest, invariant) for record in manifest.calibration_records)
    results = tuple(
        (
            method,
            dispatch_federated_threshold(
                ThresholdConstructionRequest(
                    method=method,
                    coordinate=manifest.coordinate,
                    quantile=QUANTILE,
                    capabilities=_capabilities(),
                    eligible=eligible,
                    family_by_client=(),
                    support_rule=CalibrationSupportRule.CANONICAL_MINIMUM_SUPPORT,
                    cluster_threshold_aggregation=None,
                )
            ),
        )
        for method in (
            FederatedThresholdMethod.SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_THRESHOLD,
            FederatedThresholdMethod.POOLED_SHARED_QUANTILE,
            FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD,
            FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD,
        )
    )
    checksums_after = tuple(
        (record.scored_client.client_id, checksum_file(record.path)) for record in manifest.calibration_records
    )
    assert checksums_before == checksums_after
    shared = _result(results, FederatedThresholdMethod.SHARED_THRESHOLD)
    assert isinstance(shared, SharedThresholdResult)
    assert all(
        item.diagnostic.score_set_checksum == invariant.calibration_score_set_checksum
        for item in shared.contributing_local_quantiles
    )
    assert isinstance(_result(results, FederatedThresholdMethod.LOCAL_THRESHOLD), LocalThresholdResult)
    pooled = _result(results, FederatedThresholdMethod.POOLED_SHARED_QUANTILE)
    assert isinstance(pooled, PooledSharedQuantileResult)
    assert pooled.diagnostic.score_set_checksum == invariant.calibration_score_set_checksum
    assert isinstance(
        _result(results, FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD),
        SampleWeightedSharedThresholdResult,
    )
    assert isinstance(_result(results, FederatedThresholdMethod.LOCAL_CONFORMAL_THRESHOLD), ConformalThresholdResult)
    assert shared.shared_threshold.value != pooled.shared_threshold.value


def _eligible_client_scores(record, manifest, invariant):
    references = load_benign_calibration_references(record)
    support = calibration_support(record, references, invariant.calibration_score_set_checksum)
    assert decide_eligibility(support, PROTOCOL).status is EligibilityStatus.ELIGIBLE
    return calibration_scores_from_references(
        record.scored_client,
        manifest.coordinate,
        references,
        invariant.calibration_score_set_checksum,
    )


def _result(
    results: tuple[tuple[FederatedThresholdMethod, ThresholdConstructionResult], ...],
    method: FederatedThresholdMethod,
) -> ThresholdConstructionResult:
    matches = tuple(result for candidate, result in results if candidate is method)
    assert len(matches) == 1
    return matches[0]
