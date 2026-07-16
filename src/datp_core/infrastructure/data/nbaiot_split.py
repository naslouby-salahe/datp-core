from dataclasses import dataclass, field
from pathlib import Path

import msgspec
from blake3 import blake3

from datp_core.application.ports.data import BuildSplitManifestRequest
from datp_core.application.ports.persistence import WriteArtifactRequest
from datp_core.domain.artifacts.keys import ArtifactNamespace, DatasetArtifactKey, SerializationFormat, WriteDisposition
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import Dataset, SourceTrafficLabel
from datp_core.domain.data.splitting import (
    ClientSplitMembership,
    RegimeAStaticSplitBoundarySpec,
    SplitManifest,
    SplitManifestResult,
    SplitRole,
)
from datp_core.domain.errors import SplitError
from datp_core.domain.evaluation.alert_burden import CalibrationSampleCount
from datp_core.domain.evaluation.operating_points import (
    ClientEligibilityStatus,
    EligibleClientSet,
    IneligibleClientReason,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientRoster
from datp_core.domain.mathematics.pooled_statistics import (
    PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES,
    ProtocolEligibilitySpec,
    classify_protocol_eligibility,
)
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot_source import SOURCE_LABEL_COLUMN_NAME
from datp_core.infrastructure.data.streaming import ParquetBatchStream, update_row_order_checksum
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash


def benign_split_boundaries(
    benign_total: int, *, boundary_spec: RegimeAStaticSplitBoundarySpec
) -> tuple[int, int, int, int]:
    train_fraction = float(boundary_spec.train_fraction.value)
    gap_fraction = float(boundary_spec.gap_fraction.value)
    calibration_fraction = float(boundary_spec.calibration_fraction.value)
    train_end = int(benign_total * train_fraction)
    gap1_end = int(benign_total * (train_fraction + gap_fraction))
    calibration_end = int(benign_total * (train_fraction + gap_fraction + calibration_fraction))
    gap2_end = int(benign_total * (train_fraction + 2 * gap_fraction + calibration_fraction))
    return train_end, gap1_end, calibration_end, gap2_end


def _role_for_index(index: int, *, boundaries: tuple[int, int, int, int]) -> SplitRole | None:
    train_end, gap1_end, calibration_end, gap2_end = boundaries
    if index < train_end:
        return SplitRole.TRAIN
    if index < gap1_end:
        return None
    if index < calibration_end:
        return SplitRole.CALIBRATION
    if index < gap2_end:
        return None
    return SplitRole.TEST


def row_range_roles(
    *, batch_start: int, batch_length: int, boundaries: tuple[int, int, int, int]
) -> tuple[tuple[int, int, SplitRole | None], ...]:
    train_end, gap1_end, calibration_end, gap2_end = boundaries
    batch_end = batch_start + batch_length
    cut_points = sorted({0, train_end, gap1_end, calibration_end, gap2_end, batch_start, batch_end})
    segments: list[tuple[int, int, SplitRole | None]] = []
    for lower, upper in zip(cut_points, cut_points[1:], strict=False):
        segment_start = max(lower, batch_start)
        segment_end = min(upper, batch_end)
        if segment_end <= segment_start:
            continue
        role = _role_for_index(segment_start, boundaries=boundaries)
        segments.append((segment_start - batch_start, segment_end - segment_start, role))
    return tuple(segments)


@dataclass(slots=True)
class _RoleAccumulator:
    hasher: blake3 = field(default_factory=blake3)
    count: int = 0


def _count_benign_rows(stream: ParquetBatchStream, label_column_index: int) -> int:
    count = 0
    for batch in stream.batches():
        labels = batch.column(label_column_index).to_pylist()
        matching = sum(1 for label in labels if label == SourceTrafficLabel.BENIGN.value)
        count += matching
        if matching != batch.num_rows:
            break
    return count


def _accumulate_client_split(
    stream: ParquetBatchStream, *, boundaries: tuple[int, int, int, int]
) -> dict[SplitRole, _RoleAccumulator]:
    accumulators = {
        SplitRole.TRAIN: _RoleAccumulator(),
        SplitRole.CALIBRATION: _RoleAccumulator(),
        SplitRole.TEST: _RoleAccumulator(),
    }
    global_index = 0
    for batch in stream.batches():
        for offset, length, role in row_range_roles(
            batch_start=global_index, batch_length=batch.num_rows, boundaries=boundaries
        ):
            if role is None:
                continue
            sub_batch = batch.slice(offset, length)
            update_row_order_checksum(accumulators[role].hasher, sub_batch)
            accumulators[role].count += length
        global_index += batch.num_rows
    return accumulators


def _client_split_membership(
    *,
    client_id: ClientId,
    materialized_path: Path,
    boundary_spec: RegimeAStaticSplitBoundarySpec,
    streaming_chunk_policy: StreamingChunkPolicy,
) -> ClientSplitMembership:
    stream = ParquetBatchStream(path=materialized_path, batch_rows=streaming_chunk_policy.parquet_batch_rows)
    label_column_index = stream.schema().get_field_index(SOURCE_LABEL_COLUMN_NAME)
    if label_column_index < 0:
        raise _split_error(f"{materialized_path} is missing the {SOURCE_LABEL_COLUMN_NAME!r} column")
    benign_total = _count_benign_rows(stream, label_column_index)
    boundaries = benign_split_boundaries(benign_total, boundary_spec=boundary_spec)
    accumulators = _accumulate_client_split(stream, boundaries=boundaries)
    train, calibration, test = (
        accumulators[SplitRole.TRAIN],
        accumulators[SplitRole.CALIBRATION],
        accumulators[SplitRole.TEST],
    )
    eligibility = classify_protocol_eligibility(
        calibration_count=CalibrationSampleCount(value=calibration.count),
        specification=ProtocolEligibilitySpec(),
    )
    return ClientSplitMembership(
        client_id=client_id,
        train_row_count=train.count,
        train_row_order_checksum=train.hasher.hexdigest(),
        calibration_row_count=calibration.count,
        calibration_row_order_checksum=calibration.hasher.hexdigest(),
        test_row_count=test.count,
        test_row_order_checksum=test.hasher.hexdigest(),
        eligibility=eligibility,
    )


def _is_eligible(membership: ClientSplitMembership) -> bool:
    return membership.eligibility.status is ClientEligibilityStatus.ELIGIBLE


def _eligible_client_ids(memberships: tuple[ClientSplitMembership, ...]) -> tuple[ClientId, ...]:
    matching = (membership.client_id for membership in memberships if _is_eligible(membership))
    return tuple(sorted(matching, key=lambda client_id: client_id.value))


def _ineligible_reasons(memberships: tuple[ClientSplitMembership, ...]) -> tuple[IneligibleClientReason, ...]:
    return tuple(
        IneligibleClientReason(client_id=membership.client_id, reason=membership.eligibility.reason)
        for membership in memberships
        if not _is_eligible(membership)
    )


def _eligible_client_set_identity(
    *, eligible: tuple[ClientId, ...], ineligible: tuple[IneligibleClientReason, ...]
) -> StageFingerprint:
    eligible_values = tuple(client_id.value for client_id in eligible)
    ineligible_values = tuple((item.client_id.value, item.reason.value) for item in ineligible)
    content = msgspec.json.encode((eligible_values, ineligible_values))
    return StageFingerprint(value=blake3_bytes_content_hash(content))


def _build_eligible_client_set(
    memberships: tuple[ClientSplitMembership, ...], *, roster: ClientRoster, rule_identity: StageFingerprint
) -> EligibleClientSet:
    eligible = _eligible_client_ids(memberships)
    ineligible = _ineligible_reasons(memberships)
    return EligibleClientSet(
        roster=roster,
        protocol_eligibility_rule_identity=rule_identity,
        eligible_clients=eligible,
        ineligible_reasons=ineligible,
        identity=_eligible_client_set_identity(eligible=eligible, ineligible=ineligible),
    )


def _split_error(coverage: str) -> SplitError:
    return SplitError(dataset="n_baiot", regime="a", coverage=coverage, detail=coverage)


_PROTOCOL_ELIGIBILITY_RULE_IDENTITY = StageFingerprint(
    value=blake3_bytes_content_hash(
        f"protocol_eligibility:n_min={PROTOCOL_MINIMUM_ELIGIBLE_CALIBRATION_SAMPLES.value}".encode()
    )
)


@dataclass(frozen=True, slots=True, kw_only=True)
class RegimeAStaticSplitBuilder:
    materialized_root: Path
    artifact_store: FileArtifactStore
    boundary_spec: RegimeAStaticSplitBoundarySpec
    streaming_chunk_policy: StreamingChunkPolicy

    def build(self, request: BuildSplitManifestRequest) -> SplitManifestResult:
        roster = request.partition.client_roster
        memberships = tuple(
            _client_split_membership(
                client_id=client_id,
                materialized_path=self.materialized_root / client_id.value / "source.parquet",
                boundary_spec=self.boundary_spec,
                streaming_chunk_policy=self.streaming_chunk_policy,
            )
            for client_id in roster.client_ids
        )
        eligible_client_set = _build_eligible_client_set(
            memberships, roster=roster, rule_identity=_PROTOCOL_ELIGIBILITY_RULE_IDENTITY
        )
        manifest = SplitManifest(
            partition_identity=request.partition.partition_identity,
            split_identities=request.splits,
            client_memberships=memberships,
            eligible_client_set_identity=eligible_client_set.identity,
        )
        content = msgspec.json.encode(manifest)
        content_hash = blake3_bytes_content_hash(content)
        artifact = ArtifactRef(
            artifact_id=ArtifactId(value=f"artifact-{content_hash}"),
            artifact_type=ArtifactType.SPLIT_MANIFEST,
            content_hash=content_hash,
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.JSON,
        )
        key = DatasetArtifactKey(
            artifact_type=ArtifactType.SPLIT_MANIFEST,
            dataset=Dataset.N_BAIOT,
            stage_identity=StageFingerprint(value=content_hash),
            namespace=ArtifactNamespace.DATP_ANCHOR,
        )
        write_result = self.artifact_store.write_atomically(
            WriteArtifactRequest(
                key=key, artifact=artifact, content=content, write_disposition=WriteDisposition.CREATE_IF_ABSENT
            )
        )
        return SplitManifestResult(
            split_manifest=write_result.artifact,
            split_identities=request.splits,
            partition_identity=request.partition.partition_identity,
        )
