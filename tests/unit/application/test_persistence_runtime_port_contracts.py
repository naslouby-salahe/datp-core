from dataclasses import fields, is_dataclass
from inspect import getsource, signature
from pathlib import Path
from typing import get_type_hints

from datp_core.application.ports import persistence, runtime
from datp_core.domain.artifacts.provenance import ProvenanceRecord
from datp_core.domain.runtime.policies import (
    GpuAssignment,
    HardwareInventory,
    ResourcePressureRequest,
    ResourcePressureSnapshot,
)


def test_persistence_protocol_methods_match_the_architecture_contract() -> None:
    assert tuple(name for name in persistence.ArtifactStore.__dict__ if not name.startswith("_")) == (
        "lookup",
        "write_atomically",
        "commit_bundle",
        "validate_integrity",
    )
    assert tuple(name for name in persistence.CheckpointStore.__dict__ if not name.startswith("_")) == (
        "find_compatible",
        "save",
        "save_recovery",
        "load_recovery",
    )


def test_checkpoint_scientific_and_recovery_contracts_are_distinct() -> None:
    assert signature(persistence.CheckpointStore.save).return_annotation is persistence.CheckpointWriteResult
    assert signature(persistence.CheckpointStore.save_recovery).return_annotation is persistence.RecoveryWriteResult
    assert signature(persistence.CheckpointStore.load_recovery).return_annotation is persistence.RecoveryLookupResult
    assert persistence.SaveScientificCheckpointRequest is not persistence.SaveRecoveryStateRequest
    assert persistence.CheckpointWriteResult is not persistence.RecoveryWriteResult


def test_every_port_request_and_result_is_a_frozen_slotted_dataclass() -> None:
    contracts = (
        persistence.ArtifactLookupRequest,
        persistence.ArtifactLookupResult,
        persistence.WriteArtifactRequest,
        persistence.ArtifactWriteResult,
        persistence.CommitArtifactBundleRequest,
        persistence.ArtifactBundleCommitResult,
        persistence.ValidateArtifactRequest,
        persistence.ArtifactValidationResult,
        persistence.FindCheckpointRequest,
        persistence.CheckpointLookupResult,
        persistence.SaveScientificCheckpointRequest,
        persistence.CheckpointWriteResult,
        persistence.SaveRecoveryStateRequest,
        persistence.RecoveryWriteResult,
        persistence.LoadRecoveryStateRequest,
        persistence.RecoveryLookupResult,
        ProvenanceRecord,
        persistence.AcquireArtifactLockRequest,
        HardwareInventory,
        GpuAssignment,
        ResourcePressureRequest,
        ResourcePressureSnapshot,
    )
    for contract in contracts:
        assert is_dataclass(contract)
        assert "frozen=True, slots=True, kw_only=True" in getsource(contract)
        assert hasattr(contract, "__slots__")
        assert all(field.kw_only for field in fields(contract))


def test_provenance_record_preserves_the_complete_architecture_shape() -> None:
    assert tuple(field.name for field in fields(ProvenanceRecord)) == (
        "artifact",
        "produced_by",
        "stage_fingerprint",
        "inputs",
        "consumed_by",
        "code_state",
        "dependency_lock_state",
        "environment",
        "timestamp",
    )


def test_port_signatures_do_not_expose_paths_or_raw_mappings() -> None:
    for module in (persistence, runtime):
        for value in vars(module).values():
            if not is_dataclass(value) or value.__module__ != module.__name__:
                continue
            assert all(annotation is not Path for annotation in get_type_hints(value).values())
            assert all("dict" not in str(annotation).lower() for annotation in get_type_hints(value).values())


def test_lock_lease_is_explicitly_a_context_manager() -> None:
    lease_methods = ("__enter__", "__exit__", "release", "renew")
    assert tuple(name for name in lease_methods if hasattr(persistence.ArtifactLockLease, name)) == (
        "__enter__",
        "__exit__",
        "release",
        "renew",
    )
