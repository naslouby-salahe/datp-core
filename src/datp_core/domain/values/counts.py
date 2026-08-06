"""Validated integer counts and indices."""

from typing import ClassVar

from datp_core.domain.values.base import NonNegativeIntegerValue, PositiveIntegerValue


class Seed(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "seed"


class CalibrationSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "calibration size"
    comparison_family: ClassVar[str | None] = "row_count"


class ClientCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "client count"
    comparison_family: ClassVar[str | None] = "population_cardinality"


class SeedCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "seed count"


class RoundNumber(PositiveIntegerValue):
    validation_name: ClassVar[str] = "round number"


class LocalEpochCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "local epoch count"


class BatchSize(PositiveIntegerValue):
    validation_name: ClassVar[str] = "batch size"


class BootstrapReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "bootstrap replicate count"


class SubsampleReplicateCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "subsample replicate count"


class GroupCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "group count"
    comparison_family: ClassVar[str | None] = "population_cardinality"


class ReplicateIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "replicate index"


class ConformalRankIndex(PositiveIntegerValue):
    validation_name: ClassVar[str] = "conformal rank index"


class ClusterIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "cluster index"


class KMeansInitializationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means initialization count"


class KMeansMaximumIterationCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "k-means maximum iteration count"


class ByteCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "byte count"


class SourceFileCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "source file count"


class CanonicalColumnPosition(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "canonical column position"


class SourceRowIndex(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "source row index"


class ValidationIssueCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "validation issue count"


class PairedObservationCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "paired observation count"


class LogicalElementCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "logical element count"


class CudaDeviceCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "CUDA device count"


class ClientPublicationCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "client publication count"


class DataLoaderWorkerCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "data loader worker count"


class WorkerCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "worker count"


class FeatureCount(PositiveIntegerValue):
    validation_name: ClassVar[str] = "feature count"


class RowCount(NonNegativeIntegerValue):
    validation_name: ClassVar[str] = "row count"
    comparison_family: ClassVar[str | None] = "row_count"


class ManifestSchemaVersion(PositiveIntegerValue):
    validation_name: ClassVar[str] = "manifest schema version"
