"""Out-of-core deterministic N-BaIoT synthetic-client partitioning."""

from __future__ import annotations

import hashlib

import duckdb
import msgspec
import numpy as np
import pyarrow as pa

from datp_core.core.seeding import derive_seed
from datp_core.data.contracts.enums import (
    ArtifactSchemaVersion,
    DataFailureCode,
    FeasibilityStatus,
    HashAlgorithm,
    MaterializedColumn,
    PartitionAllocation,
    SplitMembership,
    SyntheticClientNamingPolicy,
)
from datp_core.data.materialization.database import insert_record_batch, quote_identifier
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.models import NBaIoTDirichletMaterializationPlan


class ClientDomainProportions(msgspec.Struct, frozen=True):
    client_id: str
    proportions: tuple[float, ...]


class ClientRoleCount(msgspec.Struct, frozen=True):
    membership: str
    row_count: int


class ClientPartitionCounts(msgspec.Struct, frozen=True):
    client_id: str
    counts: tuple[ClientRoleCount, ...]


class PartitionEvidence(msgspec.Struct, frozen=True):
    schema_version: str
    condition: str
    allocation: str
    seed: int
    retry_attempt: int
    source_domains: tuple[str, ...]
    proportions: tuple[ClientDomainProportions, ...]
    row_counts: tuple[ClientPartitionCounts, ...]
    assignment_count: int
    assignment_checksum: str
    feasibility: str


def apply_dirichlet_partition(
    connection: duckdb.DuckDBPyConnection,
    plan: NBaIoTDirichletMaterializationPlan,
) -> PartitionEvidence:
    domains = tuple(
        str(row[0])
        for row in connection.execute(
            "SELECT DISTINCT source_domain FROM materialized_rows ORDER BY source_domain"
        ).fetchall()
    )
    memberships = tuple(
        SplitMembership(str(row[0]))
        for row in connection.execute(
            f"SELECT DISTINCT {quote_identifier(MaterializedColumn.SPLIT.value)} "
            f"FROM materialized_rows ORDER BY {quote_identifier(MaterializedColumn.SPLIT.value)}"
        ).fetchall()
    )
    if not domains or not memberships:
        raise DataFailure(
            DataFailureCode.PARTITION,
            "synthetic partitioning requires source domains and split memberships",
            source_path=None,
            source_row_index=None,
        )
    client_ids = _client_ids(plan)
    for attempt in range(int(plan.client_construction.maximum_retries) + 1):
        seed = _derive_partition_seed(plan, attempt)
        proportions = _draw_proportions(plan, domains, seed)
        connection.execute("DROP TABLE IF EXISTS partition_assignments")
        connection.execute(
            "CREATE TABLE partition_assignments ("
            f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)} VARCHAR NOT NULL, "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} BIGINT NOT NULL, "
            f"{quote_identifier(MaterializedColumn.CLIENT_ID.value)} VARCHAR NOT NULL, "
            f"PRIMARY KEY ({quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}))"
        )
        counts = tuple([0 for _ in memberships] for _ in client_ids)
        assignment_count, assignment_checksum = _allocate(
            connection,
            plan,
            domains,
            memberships,
            client_ids,
            proportions,
            counts,
        )
        if _minimums_satisfied(plan, memberships, counts):
            return PartitionEvidence(
                schema_version=ArtifactSchemaVersion.PARTITION_V1.value,
                condition=plan.partition_condition.name,
                allocation=plan.partition_condition.allocation.value,
                seed=seed,
                retry_attempt=attempt,
                source_domains=domains,
                proportions=tuple(
                    ClientDomainProportions(
                        client_id=client_id,
                        proportions=tuple(float(value) for value in proportions[index]),
                    )
                    for index, client_id in enumerate(client_ids)
                ),
                row_counts=tuple(
                    ClientPartitionCounts(
                        client_id=client_id,
                        counts=tuple(
                            ClientRoleCount(membership=membership.value, row_count=counts[index][role_index])
                            for role_index, membership in enumerate(memberships)
                        ),
                    )
                    for index, client_id in enumerate(client_ids)
                ),
                assignment_count=assignment_count,
                assignment_checksum=assignment_checksum,
                feasibility=FeasibilityStatus.FEASIBLE.value,
            )
    raise DataFailure(
        DataFailureCode.PARTITION,
        "N-BaIoT synthetic partition is infeasible after configured deterministic retries",
        source_path=None,
        source_row_index=None,
    )


def encode_partition_evidence(evidence: PartitionEvidence) -> bytes:
    return msgspec.json.encode(evidence)


def _client_ids(plan: NBaIoTDirichletMaterializationPlan) -> tuple[str, ...]:
    naming = plan.client_construction.naming
    if naming.policy is not SyntheticClientNamingPolicy.PREFIXED_ZERO_PADDED_INDEX:
        raise DataFailure(
            DataFailureCode.CONFIGURATION,
            f"unsupported synthetic client naming policy '{naming.policy.value}'",
            source_path=None,
            source_row_index=None,
        )
    return tuple(
        f"{naming.prefix.value}{index:0{int(naming.width)}d}"
        for index in range(
            int(naming.first_index),
            int(naming.first_index) + int(plan.client_construction.client_count),
        )
    )


def _derive_partition_seed(plan: NBaIoTDirichletMaterializationPlan, attempt: int) -> int:
    config = plan.client_construction
    return derive_seed(
        config.seed_key,
        int(config.seed_hash.digest_bytes),
        (
            ("attempt_index", attempt),
            ("partition_condition", plan.partition_condition.name),
            ("partition_seed", int(config.partition_seed.value)),
        ),
    )


def _draw_proportions(
    plan: NBaIoTDirichletMaterializationPlan,
    domains: tuple[str, ...],
    seed: int,
) -> np.ndarray:
    client_count = int(plan.client_construction.client_count)
    generator = np.random.default_rng(seed)
    condition = plan.partition_condition
    if condition.allocation is PartitionAllocation.DIRICHLET:
        if condition.dirichlet_alpha is None:
            raise DataFailure(
                DataFailureCode.PARTITION,
                "Dirichlet allocation is missing alpha",
                source_path=None,
                source_row_index=None,
            )
        return generator.dirichlet(
            np.full(len(domains), condition.dirichlet_alpha),
            size=client_count,
        )
    if condition.allocation is PartitionAllocation.EQUAL_ACROSS_SOURCE_DOMAINS:
        return np.full((client_count, len(domains)), 1.0 / len(domains))
    raise DataFailure(
        DataFailureCode.PARTITION,
        f"unsupported partition allocation '{condition.allocation.value}'",
        source_path=None,
        source_row_index=None,
    )


def _allocate(
    connection: duckdb.DuckDBPyConnection,
    plan: NBaIoTDirichletMaterializationPlan,
    domains: tuple[str, ...],
    memberships: tuple[SplitMembership, ...],
    client_ids: tuple[str, ...],
    proportions: np.ndarray,
    counts: tuple[list[int], ...],
) -> tuple[int, str]:
    digest = _new_digest(plan)
    assignment_count = 0
    for membership_index, membership in enumerate(memberships):
        role_count = int(
            connection.execute(
                f"SELECT count(*) FROM materialized_rows WHERE "
                f"{quote_identifier(MaterializedColumn.SPLIT.value)} = ?",
                (membership.value,),
            ).fetchone()[0]
        )
        remaining = [
            role_count // len(client_ids) + int(index < role_count % len(client_ids))
            for index in range(len(client_ids))
        ]
        reader = connection.execute(
            "SELECT source_domain, "
            f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)} "
            "FROM materialized_rows WHERE "
            f"{quote_identifier(MaterializedColumn.SPLIT.value)} = ? "
            "ORDER BY source_domain, "
            f"{quote_identifier(MaterializedColumn.SOURCE_PATH.value)}, "
            f"{quote_identifier(MaterializedColumn.SOURCE_ROW_INDEX.value)}",
            (membership.value,),
        ).fetch_record_batch(rows_per_batch=int(plan.runtime.chunk_row_count))
        for batch in reader:
            source_paths: list[str] = []
            source_indices: list[int] = []
            assigned_clients: list[str] = []
            for row_index in range(batch.num_rows):
                domain = str(batch.column(0)[row_index].as_py())
                domain_index = domains.index(domain)
                candidates = tuple(index for index, capacity in enumerate(remaining) if capacity > 0)
                winner = max(
                    candidates,
                    key=lambda index: (proportions[index, domain_index] / remaining[index], -index),
                )
                remaining[winner] -= 1
                counts[winner][membership_index] += 1
                source_path = str(batch.column(1)[row_index].as_py())
                source_row_index = int(batch.column(2)[row_index].as_py())
                client_id = client_ids[winner]
                source_paths.append(source_path)
                source_indices.append(source_row_index)
                assigned_clients.append(client_id)
                digest.update(
                    f"{source_path}\0{source_row_index}\0{client_id}\0{membership.value}\n".encode("utf-8")
                )
                assignment_count += 1
            assignment_batch = pa.RecordBatch.from_arrays(
                (
                    pa.array(source_paths, type=pa.string()),
                    pa.array(source_indices, type=pa.int64()),
                    pa.array(assigned_clients, type=pa.string()),
                ),
                (
                    MaterializedColumn.SOURCE_PATH.value,
                    MaterializedColumn.SOURCE_ROW_INDEX.value,
                    MaterializedColumn.CLIENT_ID.value,
                ),
            )
            insert_record_batch(
                connection,
                "partition_assignments",
                assignment_batch,
                "SELECT * FROM __datp_batch",
                (),
            )
    return assignment_count, digest.hexdigest()


def _minimums_satisfied(
    plan: NBaIoTDirichletMaterializationPlan,
    memberships: tuple[SplitMembership, ...],
    counts: tuple[list[int], ...],
) -> bool:
    for client_counts in counts:
        for membership_index, membership in enumerate(memberships):
            if membership in (SplitMembership.TRAIN, SplitMembership.CALIBRATION, SplitMembership.TEST):
                if client_counts[membership_index] < plan.client_construction.minimums.for_membership(membership):
                    return False
    return True


def _new_digest(plan: NBaIoTDirichletMaterializationPlan):
    config = plan.client_construction.seed_hash
    if config.algorithm is HashAlgorithm.BLAKE2B:
        return hashlib.blake2b(digest_size=int(config.digest_bytes))
    return hashlib.sha256()
