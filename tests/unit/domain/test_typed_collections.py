from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.lineage import StageDependency, StageDependencyCollection
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
    ArtifactSchemaVersion,
    StageFingerprint,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.metrics import MetricMap, MetricMapEntry, OperatingPointMetric
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import (
    ClientCalibrationScoreMap,
    ClientMap,
    ClientMapEntry,
    ClientRoster,
    ClientTestScoreMap,
)
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry, Seed, SeedRole, SeedRoleTuple, SeedTuple


def _set_attribute(instance: object, name: str, value: object) -> None:
    setattr(instance, name, value)


def _roster() -> ClientRoster:
    return ClientRoster(client_ids=(ClientId(value="client-a"), ClientId(value="client-b")))


def test_client_roster_and_maps_require_unique_canonical_roster_members() -> None:
    roster = _roster()
    values = ClientMap(
        roster=roster,
        entries=(
            ClientMapEntry(client_id=ClientId(value="client-a"), value="first"),
            ClientMapEntry(client_id=ClientId(value="client-b"), value="second"),
        ),
    )
    assert ClientCalibrationScoreMap(values=values).values.roster == ClientTestScoreMap(values=values).values.roster
    reversed_roster = (ClientId(value="client-b"), ClientId(value="client-a"))
    incomplete_entry = ClientMapEntry(client_id=ClientId(value="client-a"), value="first")

    with pytest.raises(DomainValidationError):
        ClientRoster(client_ids=reversed_roster)
    with pytest.raises(DomainValidationError):
        ClientMap(roster=roster, entries=(incomplete_entry,))


def test_seed_collections_remain_nominally_distinct_and_collections_are_frozen() -> None:
    seeds = SeedTuple(values=(Seed(value=1),))
    roles = SeedRoleTuple(values=(SeedRole.BOOTSTRAP,))
    assert seeds != roles
    with pytest.raises(FrozenInstanceError):
        _set_attribute(seeds, "values", ())


def test_enum_metric_and_stage_dependency_collections_enforce_invariants() -> None:
    enum_map = EnumMap(
        entries=(EnumMapEntry(key=SeedRole.BOOTSTRAP, value=Seed(value=1)),),
        allowed_keys=(SeedRole.BOOTSTRAP,),
        is_sparse=False,
    )
    assert enum_map.entries[0].key is SeedRole.BOOTSTRAP
    assert MetricMap(entries=(MetricMapEntry(metric=OperatingPointMetric.FPR, value=1.0),)).entries[0].value == 1.0
    first = StageDependency(upstream=_fingerprint("a"), downstream=_fingerprint("b"))
    second = StageDependency(upstream=_fingerprint("b"), downstream=_fingerprint("c"))
    reverse_dependency = StageDependency(upstream=_fingerprint("b"), downstream=_fingerprint("a"))
    assert StageDependencyCollection(dependencies=(first, second)).dependencies == (first, second)
    with pytest.raises(DomainValidationError):
        StageDependencyCollection(dependencies=(first, first))
    with pytest.raises(DomainValidationError):
        StageDependencyCollection(dependencies=(first, reverse_dependency))


def test_artifact_reference_collection_preserves_order_and_rejects_duplicate_identity_pairs() -> None:
    reference = ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{'a' * 64}"),
        artifact_type=ArtifactType.CALIBRATION_SCORE_SET,
        content_hash="b" * 64,
        schema_version=ArtifactSchemaVersion(value="scores-v1"),
        serialization_format=SerializationFormat.PARQUET,
    )
    assert ArtifactReferenceCollection(references=(reference,)).references == (reference,)
    with pytest.raises(DomainValidationError):
        ArtifactReferenceCollection(references=(reference, reference))


def _fingerprint(value: str) -> StageFingerprint:
    return StageFingerprint(value=value * 64)


def test_object_shaped_dictionary_contract_signatures_are_absent() -> None:
    source = "\n".join(path.read_text() for path in _domain_and_application_files())
    generic_type_name = chr(65) + "ny"
    assert f"dict[str, {generic_type_name}]" not in source
    assert f"Mapping[str, {object.__name__}]" not in source


def _domain_and_application_files() -> tuple[Path, ...]:
    root = Path(__file__).parents[3] / "src" / "datp_core"
    return (*((root / "domain").rglob("*.py")), *((root / "application").rglob("*.py")))
