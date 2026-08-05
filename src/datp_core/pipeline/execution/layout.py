"""Typed filesystem layout for coordinate-bound execution artifacts."""

from enum import StrEnum
from pathlib import Path

from datp_core.domain.values import Seed
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.pipeline.planning import CoordinateIdentitySegment
from datp_core.protocols.experiments import ExternalTemporalExecutionIdentity


class ExecutionArtifactDirectory(StrEnum):
    CANONICAL_DATA = "canonical"
    POPULATION = "population"
    SPLIT = "split"
    TRAINING = "training"
    SCORES = "scores"


class ExecutionRootDirectory(StrEnum):
    FEDERATED = "federated"
    BOUNDED_EVIDENCE = "bounded_evidence"


class EvaluationRunAssetDirectory(StrEnum):
    THRESHOLD = "threshold"
    EVALUATION = "evaluation"
    ANCHOR = "anchor"


def federated_training_directory(coordinate: FederatedTrainingCoordinate, output_root: Path) -> Path:
    coefficient = (
        str(coordinate.model_coefficient.value)
        if coordinate.model_coefficient is not None
        else CoordinateIdentitySegment.NO_MODEL_COEFFICIENT.value
    )
    return (
        output_root
        / ExecutionRootDirectory.FEDERATED
        / coordinate.population.value
        / str(coordinate.training_seed.value)
        / coordinate.split_protocol.value
        / coordinate.preprocessing_identity.value
        / coordinate.model.value
        / coefficient
    )


def bounded_evidence_seed_directory(
    execution_identity: ExternalTemporalExecutionIdentity,
    partition_seed: Seed,
    output_root: Path,
) -> Path:
    temporal = (
        execution_identity.temporal_state.value
        if execution_identity.temporal_state is not None
        else CoordinateIdentitySegment.NON_TEMPORAL.value
    )
    return (
        output_root
        / ExecutionRootDirectory.BOUNDED_EVIDENCE
        / execution_identity.experiment.value
        / execution_identity.population.value
        / execution_identity.evidence_role.value
        / str(partition_seed.value)
        / temporal
    )
