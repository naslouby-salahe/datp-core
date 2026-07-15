from dataclasses import dataclass
from enum import Enum, StrEnum
from hashlib import sha256

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.runtime.admissibility import WorkerCount


class SeedRole(StrEnum):
    TRAINING_INIT = "training_init"
    DATA_PARTITION = "data_partition"
    DATALOADER_SHUFFLE = "dataloader_shuffle"
    DATALOADER_WORKER = "dataloader_worker"
    SAMPLER = "sampler"
    CLIENT_ORDERING = "client_ordering"
    CLUSTERING = "clustering"
    BOOTSTRAP = "bootstrap"
    PERSONALIZATION = "personalization"
    COMPARATOR = "comparator"


@dataclass(frozen=True, slots=True, kw_only=True)
class EnumMapEntry[EnumKey: Enum, EnumValue]:
    key: EnumKey
    value: EnumValue


@dataclass(frozen=True, slots=True, kw_only=True)
class EnumMap[EnumKey: Enum, EnumValue]:
    entries: tuple[EnumMapEntry[EnumKey, EnumValue], ...]
    allowed_keys: tuple[EnumKey, ...]
    is_sparse: bool

    def __post_init__(self) -> None:
        entry_keys = tuple(entry.key for entry in self.entries)
        _validated_unique_enum_keys(entry_keys, name="enum map")
        _validated_unique_enum_keys(self.allowed_keys, name="allowed enum")
        _validated_declared_enum_keys(entry_keys=entry_keys, allowed_keys=self.allowed_keys)
        _validated_enum_map_coverage(entry_keys=entry_keys, allowed_keys=self.allowed_keys, is_sparse=self.is_sparse)


def _validated_unique_enum_keys(keys: tuple[Enum, ...], *, name: str) -> None:
    if len(set(keys)) != len(keys):
        raise DomainValidationError(
            detail=f"{name} keys must be unique", value=repr(keys), constraint="unique enum keys"
        )


def _validated_declared_enum_keys(*, entry_keys: tuple[Enum, ...], allowed_keys: tuple[Enum, ...]) -> None:
    if any(key not in allowed_keys for key in entry_keys):
        raise DomainValidationError(
            detail="enum map contains a foreign key",
            value=repr(entry_keys),
            constraint="keys must be declared enum members",
        )


def _validated_enum_map_coverage(
    *, entry_keys: tuple[Enum, ...], allowed_keys: tuple[Enum, ...], is_sparse: bool
) -> None:
    if not is_sparse and set(entry_keys) != set(allowed_keys):
        raise DomainValidationError(
            detail="non-sparse enum map must be exhaustive",
            value=repr(entry_keys),
            constraint="all declared enum members",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Seed:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or self.value < 0:
            raise DomainValidationError(
                detail="seed must be a non-negative integer",
                value=repr(self.value),
                constraint="seed >= 0",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RoundNumber:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or self.value < 1:
            raise DomainValidationError(
                detail="round number must be a positive integer",
                value=repr(self.value),
                constraint="round number >= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedTuple:
    values: tuple[Seed, ...]

    def __post_init__(self) -> None:
        if len({seed.value for seed in self.values}) != len(self.values):
            raise DomainValidationError(
                detail="seed tuple must contain unique seeds",
                value=repr(self.values),
                constraint="unique ordered seeds",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedRoleTuple:
    values: tuple[SeedRole, ...]

    def __post_init__(self) -> None:
        if len(set(self.values)) != len(self.values):
            raise DomainValidationError(
                detail="seed role tuple must contain unique roles",
                value=repr(self.values),
                constraint="unique ordered seed roles",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedMapEntry[SeedMapValue]:
    seed: Seed
    value: SeedMapValue


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedMap[SeedMapValue]:
    cohort: SeedTuple
    entries: tuple[SeedMapEntry[SeedMapValue], ...]

    def __post_init__(self) -> None:
        cohort_values = {seed.value for seed in self.cohort.values}
        entry_values = {entry.seed.value for entry in self.entries}
        if cohort_values != entry_values or len(self.entries) != len(entry_values):
            raise DomainValidationError(
                detail="seed map entries must match the declared cohort exactly once",
                value=repr(self.entries),
                constraint="one entry for every cohort seed",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmatorySeedCohort:
    b1_seeds: SeedTuple
    b2_seeds: SeedTuple

    def __post_init__(self) -> None:
        if len(self.b1_seeds.values) != 10 or len(self.b2_seeds.values) != 10:
            raise DomainValidationError(
                detail="confirmatory seed cohort requires exactly ten paired seeds",
                value=f"{len(self.b1_seeds.values)}/{len(self.b2_seeds.values)}",
                constraint="ten paired B1/B2 seeds",
            )
        if self.b1_seeds != self.b2_seeds:
            raise DomainValidationError(
                detail="confirmatory B1 and B2 seed cohorts must be identically paired",
                value=repr((self.b1_seeds, self.b2_seeds)),
                constraint="paired B1/B2 seed membership and order",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class DataLoaderSeedPlan:
    shuffle_seed: Seed
    sampler_seed: Seed
    worker_seed: Seed
    client_seed: Seed
    epoch_seed: Seed
    round_seed: Seed
    worker_count: WorkerCount

    def worker_seed_for(self, worker_index: int) -> Seed:
        if type(worker_index) is not int or not 0 <= worker_index < self.worker_count.value:
            raise DomainValidationError(
                detail="data-loader worker index must belong to the frozen worker count",
                value=repr(worker_index),
                constraint=f"0 <= worker index < {self.worker_count.value}",
            )
        seed_material = f"datp-core/dataloader-worker/v1\0{self.worker_seed.value}\0{worker_index}".encode()
        derived_value = int.from_bytes(sha256(seed_material).digest()[:8], byteorder="big") & ((1 << 63) - 1)
        return Seed(value=derived_value)


@dataclass(frozen=True, slots=True, kw_only=True)
class SeedPlan:
    experiment_seed: Seed
    derived: EnumMap[SeedRole, Seed]
    dataloader: DataLoaderSeedPlan


def derive_seed(*, experiment_seed: Seed, role: SeedRole, stage_fingerprint: StageFingerprint) -> Seed:
    seed_material = f"datp-core/seed/v1\0{experiment_seed.value}\0{role.value}\0{stage_fingerprint.value}".encode()
    derived_value = int.from_bytes(sha256(seed_material).digest()[:8], byteorder="big") & ((1 << 63) - 1)
    return Seed(value=derived_value)
