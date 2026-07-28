"""Strict materialization, split, preprocessing, and client-construction contracts."""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import Field, NonNegativeInt, PositiveInt, model_validator

from datp_core.core.numbers import Probability
from datp_core.core.seeding import Seed
from datp_core.data.contracts.base import StrictFrozenModel
from datp_core.data.contracts.constants import PROBABILITY_SUM_ABSOLUTE_TOLERANCE
from datp_core.data.contracts.enums import (
    AttackAssignment,
    BoundaryRule,
    CategoricalEncodingStrategy,
    CategoryOrder,
    ChronologyRolloverPolicy,
    ClientConstructionMethod,
    ConstantFeaturePolicy,
    DeduplicationPolicy,
    DeterministicOrdering,
    EncodedFeatureNaming,
    GapHandling,
    HashAlgorithm,
    MissingCategoryPolicy,
    NormalizationFitScope,
    NormalizationStrategy,
    OutOfRangePolicy,
    ParquetCompression,
    PartitionAllocation,
    SortDirection,
    SplitLayout,
    SplitMembership,
    SplitMethod,
    SyntheticClientNamingPolicy,
    UnknownCategoryPolicy,
)
from datp_core.data.contracts.values import ClientNamePrefix


class HashConfig(StrictFrozenModel):
    algorithm: HashAlgorithm
    digest_bytes: PositiveInt

    @model_validator(mode="after")
    def validate_digest(self) -> HashConfig:
        maximum = 64 if self.algorithm is HashAlgorithm.BLAKE2B else 32
        if self.digest_bytes > maximum:
            raise ValueError(f"digest_bytes exceeds the limit for {self.algorithm.value}")
        return self


class ParquetWriteConfig(StrictFrozenModel):
    compression: ParquetCompression
    dictionary_encoding: bool
    row_group_size: PositiveInt
    data_page_size: PositiveInt


class DuckDbRuntimeConfig(StrictFrozenModel):
    threads: PositiveInt
    memory_limit: str
    preserve_insertion_order: bool

    @model_validator(mode="after")
    def validate_memory_limit(self) -> DuckDbRuntimeConfig:
        if not self.memory_limit.strip():
            raise ValueError("memory_limit must not be blank")
        return self


class DataLoadingConfig(StrictFrozenModel):
    chunk_row_count: PositiveInt
    parquet: ParquetWriteConfig
    duckdb: DuckDbRuntimeConfig
    row_digest: HashConfig


class StandardRandomRatios(StrictFrozenModel):
    layout: Literal[SplitLayout.STANDARD]
    train: Probability
    calibration: Probability
    test: Probability

    @model_validator(mode="after")
    def validate_sum(self) -> StandardRandomRatios:
        _validate_probability_sum((self.train, self.calibration, self.test))
        return self

    def ordered(self) -> tuple[tuple[SplitMembership, Probability], ...]:
        return (
            (SplitMembership.TRAIN, self.train),
            (SplitMembership.CALIBRATION, self.calibration),
            (SplitMembership.TEST, self.test),
        )


class StaticReferenceRandomRatios(StrictFrozenModel):
    layout: Literal[SplitLayout.STATIC_RECALIBRATION_REFERENCE]
    train: Probability
    calibration: Probability
    recalibration_reference: Probability
    test: Probability

    @model_validator(mode="after")
    def validate_sum(self) -> StaticReferenceRandomRatios:
        _validate_probability_sum((self.train, self.calibration, self.recalibration_reference, self.test))
        return self

    def ordered(self) -> tuple[tuple[SplitMembership, Probability], ...]:
        return (
            (SplitMembership.TRAIN, self.train),
            (SplitMembership.CALIBRATION, self.calibration),
            (SplitMembership.RECALIBRATION_REFERENCE, self.recalibration_reference),
            (SplitMembership.TEST, self.test),
        )


type RandomRatios = Annotated[
    StandardRandomRatios | StaticReferenceRandomRatios,
    Field(discriminator="layout"),
]


class RandomFractionalSplitConfig(StrictFrozenModel):
    method: Literal[SplitMethod.RANDOM_FRACTIONAL]
    seed: Seed
    ratios: RandomRatios
    attack_assignment: AttackAssignment
    deduplication: DeduplicationPolicy
    benign_ordering: DeterministicOrdering


class ChronologicalGappedRatios(StrictFrozenModel):
    train: Probability
    first_gap: Probability
    calibration: Probability
    second_gap: Probability
    test: Probability

    @model_validator(mode="after")
    def validate_sum(self) -> ChronologicalGappedRatios:
        _validate_probability_sum((self.train, self.first_gap, self.calibration, self.second_gap, self.test))
        return self


class ChronologicalGappedSplitConfig(StrictFrozenModel):
    method: Literal[SplitMethod.CHRONOLOGICAL_GAPPED]
    ratios: ChronologicalGappedRatios
    attack_assignment: AttackAssignment
    gap_handling: GapHandling
    boundary_rule: BoundaryRule
    sort_direction: SortDirection


class TemporalRatios(StrictFrozenModel):
    historical_training: Probability
    historical_calibration: Probability
    future_recalibration: Probability
    future_evaluation: Probability

    @model_validator(mode="after")
    def validate_sum(self) -> TemporalRatios:
        _validate_probability_sum(
            (
                self.historical_training,
                self.historical_calibration,
                self.future_recalibration,
                self.future_evaluation,
            )
        )
        return self


class TemporalRoleMinimums(StrictFrozenModel):
    historical_training: PositiveInt
    historical_calibration: PositiveInt
    future_recalibration: PositiveInt
    future_evaluation: PositiveInt


class WithinClientChronologicalSplitConfig(StrictFrozenModel):
    method: Literal[SplitMethod.WITHIN_CLIENT_CHRONOLOGICAL]
    ratios: TemporalRatios
    minimums: TemporalRoleMinimums
    attack_assignment: AttackAssignment
    sort_direction: SortDirection
    rollover_policy: ChronologyRolloverPolicy
    rollover_period_seconds: PositiveInt
    boundary_rule: BoundaryRule


type SplitConfig = Annotated[
    RandomFractionalSplitConfig | ChronologicalGappedSplitConfig | WithinClientChronologicalSplitConfig,
    Field(discriminator="method"),
]


class MinMaxNormalizationConfig(StrictFrozenModel):
    strategy: Literal[NormalizationStrategy.MIN_MAX]
    fit_scope: NormalizationFitScope
    constant_feature_policy: ConstantFeaturePolicy
    out_of_range_policy: OutOfRangePolicy


class StandardNormalizationConfig(StrictFrozenModel):
    strategy: Literal[NormalizationStrategy.STANDARD]
    fit_scope: NormalizationFitScope
    standard_deviation_ddof: NonNegativeInt
    constant_feature_policy: ConstantFeaturePolicy
    out_of_range_policy: OutOfRangePolicy

    @model_validator(mode="after")
    def validate_ddof(self) -> StandardNormalizationConfig:
        if self.standard_deviation_ddof not in (0, 1):
            raise ValueError("standard_deviation_ddof must be 0 or 1")
        if self.out_of_range_policy is not OutOfRangePolicy.PRESERVE:
            raise ValueError("standard normalization requires preserve out-of-range policy")
        return self


type NormalizationConfig = Annotated[
    MinMaxNormalizationConfig | StandardNormalizationConfig,
    Field(discriminator="strategy"),
]


class OneHotEncodingConfig(StrictFrozenModel):
    strategy: Literal[CategoricalEncodingStrategy.ONE_HOT]
    vocabulary_fit_membership: SplitMembership
    category_order: CategoryOrder
    missing_category_policy: MissingCategoryPolicy
    unknown_category_policy: UnknownCategoryPolicy
    unknown_indicator_distinct_from_missing_indicator: bool
    encoded_feature_naming: EncodedFeatureNaming

    @model_validator(mode="after")
    def validate_indicators(self) -> OneHotEncodingConfig:
        if not self.unknown_indicator_distinct_from_missing_indicator:
            raise ValueError("unknown and missing indicators must be distinct")
        return self


class DatasetFileClientConfig(StrictFrozenModel):
    method: Literal[ClientConstructionMethod.DATASET_FILE_PSEUDO_CLIENTS]


class PhysicalDeviceClientConfig(StrictFrozenModel):
    method: Literal[ClientConstructionMethod.PHYSICAL_DEVICE_CLIENTS]


class SensorGroupClientConfig(StrictFrozenModel):
    method: Literal[ClientConstructionMethod.SENSOR_GROUP_CLIENTS]


class StandardRoleMinimums(StrictFrozenModel):
    train: PositiveInt
    calibration: PositiveInt
    test: PositiveInt

    def for_membership(self, membership: SplitMembership) -> int:
        if membership is SplitMembership.TRAIN:
            return int(self.train)
        if membership is SplitMembership.CALIBRATION:
            return int(self.calibration)
        if membership is SplitMembership.TEST:
            return int(self.test)
        raise ValueError(f"unsupported standard membership: {membership.value}")


class SyntheticClientNamingConfig(StrictFrozenModel):
    policy: SyntheticClientNamingPolicy
    prefix: ClientNamePrefix
    first_index: NonNegativeInt
    width: PositiveInt


class DirichletClientConfig(StrictFrozenModel):
    method: Literal[ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS]
    client_count: PositiveInt
    partition_seed: Seed
    seed_key: str
    seed_hash: HashConfig
    maximum_retries: NonNegativeInt
    minimums: StandardRoleMinimums
    attack_labels_used_in_partition_generation: Literal[False]
    naming: SyntheticClientNamingConfig


type ClientConstructionConfig = Annotated[
    DatasetFileClientConfig | PhysicalDeviceClientConfig | SensorGroupClientConfig | DirichletClientConfig,
    Field(discriminator="method"),
]


class PartitionCondition(StrictFrozenModel):
    name: str
    allocation: PartitionAllocation
    dirichlet_alpha: float | None

    @model_validator(mode="after")
    def validate_allocation(self) -> PartitionCondition:
        if not self.name.strip():
            raise ValueError("partition condition name must not be blank")
        if self.allocation is PartitionAllocation.DIRICHLET:
            if self.dirichlet_alpha is None or not math.isfinite(self.dirichlet_alpha) or self.dirichlet_alpha <= 0.0:
                raise ValueError("Dirichlet allocation requires a finite positive alpha")
        elif self.dirichlet_alpha is not None:
            raise ValueError("equal allocation must not define a Dirichlet alpha")
        return self


def _validate_probability_sum(values: tuple[Probability, ...]) -> None:
    if not math.isclose(
        sum(float(value) for value in values),
        1.0,
        rel_tol=0.0,
        abs_tol=PROBABILITY_SUM_ABSOLUTE_TOLERANCE,
    ):
        raise ValueError("split probabilities must sum exactly to one")
