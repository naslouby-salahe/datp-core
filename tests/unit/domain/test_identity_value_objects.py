from dataclasses import FrozenInstanceError

import pytest

from datp_core.domain.artifacts.references import (
    ArtifactId,
    CheckpointId,
    ExecutionAttemptId,
    RunIdentity,
    StageFingerprint,
    StageRunIdentity,
)
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.identities import ArchitectureCatalogueId, CellId, ExperimentId
from datp_core.domain.runtime.admissibility import WorkerCount
from datp_core.domain.runtime.policies import PipelineStage
from datp_core.domain.runtime.seeds import (
    ConfirmatorySeedCohort,
    DataLoaderSeedPlan,
    RoundNumber,
    Seed,
    SeedMap,
    SeedMapEntry,
    SeedRole,
    SeedRoleTuple,
    SeedTuple,
    derive_seed,
)


def _seed_tuple(count: int, *, start: int = 0) -> SeedTuple:
    return SeedTuple(values=tuple(Seed(value=index) for index in range(start, start + count)))


def _set_attribute(instance: object, name: str, value: str) -> None:
    setattr(instance, name, value)


def test_identity_value_objects_accept_canonical_formats() -> None:
    fingerprint = StageFingerprint(value="a" * 64)
    run_identity = RunIdentity(value=f"run-{'b' * 64}")
    attempt_identity = ExecutionAttemptId(value="attempt-123e4567-e89b-42d3-a456-426614174000")

    assert ExperimentId(value="E-C1").value == "E-C1"
    assert ArchitectureCatalogueId(value="B_A_APPLICABILITY_BOUNDARY").value == "B_A_APPLICABILITY_BOUNDARY"
    assert CellId(value="E-C1#0123456789abcdef").value == "E-C1#0123456789abcdef"
    assert ArtifactId(value=f"artifact-{'c' * 64}").value == f"artifact-{'c' * 64}"
    assert CheckpointId(value=f"checkpoint-{'d' * 64}").value == f"checkpoint-{'d' * 64}"
    assert (
        StageRunIdentity(
            run_identity=run_identity,
            execution_attempt_id=attempt_identity,
            stage=PipelineStage.TRAIN,
            stage_fingerprint=fingerprint,
        ).stage
        is PipelineStage.TRAIN
    )


@pytest.mark.parametrize(
    ("constructor", "value"),
    [
        (ExperimentId, "e-c1"),
        (ArchitectureCatalogueId, "E-C1"),
        (CellId, "E-C1#0123456789ABCDEf"),
        (ArtifactId, "artifact-not-a-digest"),
        (RunIdentity, "run-not-a-digest"),
        (CheckpointId, "checkpoint-not-a-digest"),
        (StageFingerprint, "A" * 64),
        (ExecutionAttemptId, "attempt-123e4567-e89b-12d3-a456-426614174000"),
    ],
)
def test_identity_value_objects_reject_noncanonical_formats(
    constructor: type[ExperimentId]
    | type[ArchitectureCatalogueId]
    | type[CellId]
    | type[ArtifactId]
    | type[RunIdentity]
    | type[CheckpointId]
    | type[StageFingerprint]
    | type[ExecutionAttemptId],
    value: str,
) -> None:
    with pytest.raises(DomainValidationError):
        constructor(value=value)


def test_scientific_identity_construction_is_deterministic_and_distinct_from_attempts() -> None:
    artifact_id = f"artifact-{'a' * 64}"
    run_id = f"run-{'a' * 64}"

    assert ArtifactId(value=artifact_id) == ArtifactId(value=artifact_id)
    assert RunIdentity(value=run_id) != ExecutionAttemptId(value="attempt-123e4567-e89b-42d3-a456-426614174000")
    with pytest.raises(FrozenInstanceError):
        _set_attribute(RunIdentity(value=run_id), "value", run_id)


def test_seed_and_round_value_objects_enforce_nonnegative_and_positive_ranges() -> None:
    assert Seed(value=0).value == 0
    assert RoundNumber(value=1).value == 1
    for invalid_seed in (-1, True):
        with pytest.raises(DomainValidationError):
            Seed(value=invalid_seed)
    for invalid_round in (0, -1, True):
        with pytest.raises(DomainValidationError):
            RoundNumber(value=invalid_round)


def test_seed_collections_preserve_order_and_validate_membership() -> None:
    cohort = _seed_tuple(2)
    roles = SeedRoleTuple(values=(SeedRole.TRAINING_INIT, SeedRole.BOOTSTRAP))
    seed_map = SeedMap(
        cohort=cohort,
        entries=(
            SeedMapEntry(seed=Seed(value=0), value="first"),
            SeedMapEntry(seed=Seed(value=1), value="second"),
        ),
    )

    assert cohort.values[0] == Seed(value=0)
    assert roles.values[-1] is SeedRole.BOOTSTRAP
    assert seed_map.entries[-1].value == "second"
    with pytest.raises(DomainValidationError):
        SeedTuple(values=(Seed(value=0), Seed(value=0)))
    with pytest.raises(DomainValidationError):
        SeedMap(cohort=cohort, entries=(SeedMapEntry(seed=Seed(value=0), value="only"),))


def test_confirmatory_seed_cohort_requires_exactly_ten_identically_paired_seeds() -> None:
    paired = _seed_tuple(10)

    assert ConfirmatorySeedCohort(b1_seeds=paired, b2_seeds=paired).b1_seeds == paired
    for invalid_count in (9, 11):
        invalid = _seed_tuple(invalid_count)
        with pytest.raises(DomainValidationError):
            ConfirmatorySeedCohort(b1_seeds=invalid, b2_seeds=invalid)
    with pytest.raises(DomainValidationError):
        ConfirmatorySeedCohort(b1_seeds=paired, b2_seeds=_seed_tuple(10, start=1))


def test_seed_derivation_is_deterministic_and_role_and_stage_specific() -> None:
    experiment_seed = Seed(value=42)
    first_stage = StageFingerprint(value="a" * 64)
    second_stage = StageFingerprint(value="b" * 64)

    derived = derive_seed(
        experiment_seed=experiment_seed,
        role=SeedRole.TRAINING_INIT,
        stage_fingerprint=first_stage,
    )

    assert derived == derive_seed(
        experiment_seed=experiment_seed,
        role=SeedRole.TRAINING_INIT,
        stage_fingerprint=first_stage,
    )
    assert derived != derive_seed(
        experiment_seed=experiment_seed,
        role=SeedRole.BOOTSTRAP,
        stage_fingerprint=first_stage,
    )
    assert derived != derive_seed(
        experiment_seed=experiment_seed,
        role=SeedRole.TRAINING_INIT,
        stage_fingerprint=second_stage,
    )


def test_data_loader_seed_plan_derives_bounded_stable_worker_seeds() -> None:
    seed_plan = DataLoaderSeedPlan(
        shuffle_seed=Seed(value=1),
        sampler_seed=Seed(value=2),
        worker_seed=Seed(value=3),
        client_seed=Seed(value=4),
        epoch_seed=Seed(value=5),
        round_seed=Seed(value=6),
        worker_count=WorkerCount(value=2),
    )

    assert seed_plan.worker_seed_for(0) == seed_plan.worker_seed_for(0)
    assert seed_plan.worker_seed_for(0) != seed_plan.worker_seed_for(1)
    for invalid_worker_index in (-1, 2, True):
        with pytest.raises(DomainValidationError):
            seed_plan.worker_seed_for(invalid_worker_index)
