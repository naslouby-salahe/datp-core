"""The one strict, shared manifest codec (canonical JSON via msgspec)."""

from __future__ import annotations

import msgspec

from datp_core.artifacts.errors import ManifestDecodeError, ManifestSchemaIncompatibleError
from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind, ArtifactState
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.artifacts.manifest import ArtifactManifest
from datp_core.core.hashing import Checksum, Fingerprint
from datp_core.core.identifiers import ExperimentId, PopulationId
from datp_core.core.seeding import Seed
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.node_key import StageNodeKey

CURRENT_ARTIFACT_SCHEMA_VERSION = 2


class _StageNodeKeyWire(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    experiment: str
    stage: str
    seed: int | None = None
    population: str | None = None
    kind_suffix: str | None = None
    partition_condition: str | None = None
    evaluation_label: str | None = None
    threshold_policy: str | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    federated_summary_fixed_k: float | None = None
    fingerprint_features: tuple[str, ...] | None = None
    calibration_sample_count: int | None = None
    calibration_replicate: int | None = None


class _ArtifactParentWire(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    node_experiment: str
    node_stage: str
    parent_relative_path: str
    scientific_fingerprint: str
    execution_fingerprint: str
    source_inventory_fingerprint: str | None = None
    artifact_kind: str = ""
    seed: int | None = None
    population: str | None = None
    kind_suffix: str | None = None


def _node_key_to_wire(key: StageNodeKey) -> _StageNodeKeyWire:
    return _StageNodeKeyWire(
        experiment=key.experiment.value,
        stage=key.stage.value,
        seed=key.seed,
        population=key.population.value if key.population else None,
        kind_suffix=key.kind_suffix,
        partition_condition=key.partition_condition,
        evaluation_label=key.evaluation_label,
        threshold_policy=key.threshold_policy.value if key.threshold_policy else None,
        federated_proximal_mu=key.federated_proximal_mu,
        ditto_proximal_weight=key.ditto_proximal_weight,
        threshold_quantile=key.threshold_quantile,
        shrinkage_weight=key.shrinkage_weight,
        federated_summary_fixed_k=key.federated_summary_fixed_k,
        fingerprint_features=key.fingerprint_features,
        calibration_sample_count=key.calibration_sample_count,
        calibration_replicate=key.calibration_replicate,
    )


def _node_key_from_wire(wire: _StageNodeKeyWire) -> StageNodeKey:
    return StageNodeKey(
        experiment=ExperimentId(wire.experiment),
        stage=StageKind(wire.stage),
        seed=wire.seed,
        population=PopulationId(wire.population) if wire.population else None,
        kind_suffix=wire.kind_suffix,
        partition_condition=wire.partition_condition,
        evaluation_label=wire.evaluation_label,
        threshold_policy=None,
        federated_proximal_mu=wire.federated_proximal_mu,
        ditto_proximal_weight=wire.ditto_proximal_weight,
        threshold_quantile=wire.threshold_quantile,
        shrinkage_weight=wire.shrinkage_weight,
        federated_summary_fixed_k=wire.federated_summary_fixed_k,
        fingerprint_features=wire.fingerprint_features,
        calibration_sample_count=wire.calibration_sample_count,
        calibration_replicate=wire.calibration_replicate,
    )


class _ArtifactManifestWire(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    node_key: _StageNodeKeyWire
    artifact_kind: str
    artifact_format: str
    scientific_fingerprint: str
    execution_fingerprint: str
    payload_checksum: str
    relative_path: str
    state: str
    schema_version: int
    parents: list[_ArtifactParentWire]
    creation_timestamp: float
    environment_identity: str
    experiment_id: str | None
    seed: int | None
    source_inventory_fingerprint: str | None = None


def _parent_to_wire(parent: ArtifactParent) -> _ArtifactParentWire:
    return _ArtifactParentWire(
        node_experiment=parent.parent_key.node_key.experiment.value,
        node_stage=parent.parent_key.node_key.stage.value,
        parent_relative_path=parent.parent_relative_path,
        scientific_fingerprint=parent.scientific_fingerprint.value,
        execution_fingerprint=parent.execution_fingerprint.value,
        source_inventory_fingerprint=(
            parent.source_inventory_fingerprint.value
            if parent.source_inventory_fingerprint
            else None
        ),
        artifact_kind=parent.parent_key.kind.value,
        seed=parent.parent_key.node_key.seed,
        population=parent.parent_key.node_key.population.value
        if parent.parent_key.node_key.population
        else None,
        kind_suffix=parent.parent_key.node_key.kind_suffix,
    )


def _parent_from_wire(wire: _ArtifactParentWire) -> ArtifactParent:
    return ArtifactParent(
        parent_key=ArtifactKey(
            node_key=StageNodeKey(
                experiment=ExperimentId(wire.node_experiment),
                stage=StageKind(wire.node_stage),
                seed=wire.seed,
                population=PopulationId(wire.population) if wire.population else None,
                kind_suffix=wire.kind_suffix,
            ),
            kind=ArtifactKind(wire.artifact_kind),
        ),
        parent_relative_path=wire.parent_relative_path,
        scientific_fingerprint=Fingerprint(wire.scientific_fingerprint),
        execution_fingerprint=Fingerprint(wire.execution_fingerprint),
        source_inventory_fingerprint=(
            Checksum(wire.source_inventory_fingerprint)
            if wire.source_inventory_fingerprint is not None
            else None
        ),
    )


def encode_manifest(manifest: ArtifactManifest) -> bytes:
    """Canonical manifest JSON payload shared by every atomic commit transaction."""
    wire = _ArtifactManifestWire(
        node_key=_node_key_to_wire(manifest.artifact_key.node_key),
        artifact_kind=manifest.artifact_key.kind.value,
        artifact_format=manifest.artifact_format.value,
        scientific_fingerprint=manifest.scientific_fingerprint.value,
        execution_fingerprint=manifest.execution_fingerprint.value,
        payload_checksum=manifest.payload_checksum.value,
        relative_path=manifest.relative_path,
        state=manifest.state.value,
        schema_version=manifest.schema_version,
        parents=[_parent_to_wire(parent) for parent in manifest.parents],
        creation_timestamp=manifest.creation_timestamp,
        environment_identity=manifest.environment_identity,
        experiment_id=manifest.experiment_id.value if manifest.experiment_id else None,
        seed=manifest.seed.value if manifest.seed else None,
        source_inventory_fingerprint=(
            manifest.source_inventory_fingerprint.value if manifest.source_inventory_fingerprint else None
        ),
    )
    return msgspec.json.encode(wire)


def decode_manifest(payload: bytes) -> ArtifactManifest:
    """Strictly decode manifest JSON bytes, rejecting unknown fields and invalid enum values.

    Raises ``ManifestSchemaIncompatibleError`` when the schema version does not match the
    current codec, and ``ManifestDecodeError`` for every other malformed-manifest condition.
    """
    try:
        wire = msgspec.json.decode(payload, type=_ArtifactManifestWire, strict=True)
    except (msgspec.DecodeError, msgspec.ValidationError) as exc:
        raise ManifestDecodeError(f"Manifest failed strict decoding: {exc}") from exc

    if wire.schema_version != CURRENT_ARTIFACT_SCHEMA_VERSION:
        raise ManifestSchemaIncompatibleError(
            f"Manifest schema_version {wire.schema_version} is incompatible with "
            f"codec version {CURRENT_ARTIFACT_SCHEMA_VERSION}"
        )

    try:
        artifact_format = ArtifactFormat(wire.artifact_format)
        artifact_kind = ArtifactKind(wire.artifact_kind)
        state = ArtifactState(wire.state)
        node_key = _node_key_from_wire(wire.node_key)
        parents = tuple(_parent_from_wire(parent) for parent in wire.parents)
        return ArtifactManifest(
            artifact_key=ArtifactKey(node_key=node_key, kind=artifact_kind),
            artifact_format=artifact_format,
            state=state,
            relative_path=wire.relative_path,
            scientific_fingerprint=Fingerprint(wire.scientific_fingerprint),
            execution_fingerprint=Fingerprint(wire.execution_fingerprint),
            payload_checksum=Checksum(wire.payload_checksum),
            schema_version=wire.schema_version,
            parents=parents,
            creation_timestamp=wire.creation_timestamp,
            environment_identity=wire.environment_identity,
            experiment_id=ExperimentId(wire.experiment_id) if wire.experiment_id is not None else None,
            seed=Seed(wire.seed) if wire.seed is not None else None,
            source_inventory_fingerprint=(
                Checksum(wire.source_inventory_fingerprint) if wire.source_inventory_fingerprint is not None else None
            ),
        )
    except ValueError as exc:
        raise ManifestDecodeError(f"Manifest contains an invalid value: {exc}") from exc


__all__ = [
    "CURRENT_ARTIFACT_SCHEMA_VERSION",
    "decode_manifest",
    "encode_manifest",
]
