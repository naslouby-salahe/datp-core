"""N-BaIoT Dirichlet partition allocation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from datp_core.core.seeding import derive_seed
from datp_core.data.adapters.nbaiot.models import DirichletPartition
from datp_core.data.contracts.enums import ClientConstructionMethod
from datp_core.data.contracts.materialization import SetupClientConstructionRecord
from datp_core.experiments import SweepConditionAllocation, SweepConditionRecord


def derive_partition_seed(*, key: str, digest_bytes: int, partition_seed: int, condition: str, attempt: int) -> int:
    if attempt < 0:
        raise ValueError("Partition seed derivation requires a non-negative attempt")
    return derive_seed(
        key,
        digest_bytes,
        (
            ("attempt_index", attempt),
            ("partition_condition", condition),
            ("partition_seed", partition_seed),
        ),
    )


def partition_dirichlet_rows(
    rows: tuple[tuple[str, str, str, int], ...],
    *,
    condition: SweepConditionRecord,
    client_count: int,
    seed: int,
    retry_attempt: int,
) -> DirichletPartition:
    if client_count < 1:
        raise ValueError("Dirichlet partition requires a positive client count")
    domains = tuple(sorted({domain for _, domain, _, _ in rows}))
    if not domains:
        raise ValueError("Dirichlet partition requires source rows")
    generator = np.random.default_rng(seed)
    client_ids = tuple(f"synthetic_{index:02d}" for index in range(client_count))
    if condition.allocation == SweepConditionAllocation.DIRICHLET:
        if condition.dirichlet_alpha is None or condition.dirichlet_alpha <= 0.0:
            raise ValueError("Dirichlet conditions require a positive alpha")
        draws = generator.dirichlet(
            np.full(len(domains), condition.dirichlet_alpha), size=client_count)
    elif condition.allocation == SweepConditionAllocation.EQUAL_ACROSS_SOURCE_DOMAINS:
        if condition.dirichlet_alpha is not None:
            raise ValueError("IID reference conditions must not declare a Dirichlet alpha")
        draws = np.full((client_count, len(domains)), 1.0 / len(domains))
    else:
        raise ValueError(f"Unsupported partition allocation '{condition.allocation}'")
    domain_index = {domain: index for index, domain in enumerate(domains)}
    assignments: list[tuple[str, str, int, str]] = []
    splits = tuple(sorted({split for split, _, _, _ in rows}))
    counts = {client_id: dict.fromkeys(splits, 0) for client_id in client_ids}
    for split in splits:
        role_rows = sorted(
            (row for row in rows if row[0] == split), key=lambda row: (row[1], row[2], row[3]))
        remaining = [
            len(role_rows) // client_count + (index < len(role_rows) % client_count) for index in range(client_count)
        ]
        for _, domain, source_path, source_row_index in role_rows:
            candidates = [index for index, capacity in enumerate(remaining) if capacity > 0]
            winner = max(
                candidates,
                key=lambda index, domain=domain: (
                    draws[index, domain_index[domain]] / remaining[index], -index),
            )
            remaining[winner] -= 1
            client_id = client_ids[winner]
            assignments.append((source_path, domain, source_row_index, client_id))
            counts[client_id][split] += 1
    if len({(path, row_index) for path, _, row_index, _ in assignments}) != len(assignments):
        raise ValueError("Dirichlet partition assigned a source row more than once")
    return DirichletPartition(
        condition=condition.name,
        allocation=condition.allocation,
        seed=seed,
        retry_attempt=retry_attempt,
        source_domains=domains,
        proportions=tuple(
            (client_id, tuple(float(value) for value in draws[index])) for index, client_id in enumerate(client_ids)
        ),
        row_counts=tuple((client_id, tuple(counts[client_id].items())) for client_id in client_ids),
        assignments=tuple(assignments),
    )


def apply_nbaiot_dirichlet_partition(
    source_path: Path,
    target_path: Path,
    *,
    setup: SetupClientConstructionRecord,
    condition: SweepConditionRecord,
    seed_key: str,
    digest_bytes: int,
) -> DirichletPartition:
    if (
        setup.method != ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS
        or setup.client_count is None
        or setup.partition_seed is None
    ):
        raise ValueError(
            "N-BaIoT Dirichlet materialization requires complete synthetic-client configuration")
    if setup.attack_labels_used_in_partition_generation is not False:
        raise ValueError(
            "N-BaIoT Dirichlet materialization must prohibit attack labels during allocation")
    frame = pl.read_parquet(source_path)
    required = {"split", "client_id", "source_path", "source_row_index"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"N-BaIoT partition input lacks columns: {', '.join(missing)}")
    rows = tuple(
        (str(split), str(domain), str(path), int(index))
        for split, domain, path, index in frame.select(
            "split", "client_id", "source_path", "source_row_index"
        ).iter_rows()
    )
    retry_policy = setup.retry_policy or {}
    if "max_retries" not in retry_policy:
        raise ValueError("N-BaIoT Dirichlet retry policy requires an explicit max_retries entry")
    configured_max_retries = retry_policy["max_retries"]
    if not isinstance(configured_max_retries, int) or configured_max_retries < 0:
        raise ValueError(
            "N-BaIoT Dirichlet retry policy requires a non-negative integer max_retries")
    max_retries = configured_max_retries
    minimums = setup.minimum_row_counts or {}
    for attempt in range(max_retries + 1):
        seed = derive_partition_seed(
            key=seed_key,
            digest_bytes=digest_bytes,
            partition_seed=int(setup.partition_seed.value),
            condition=condition.name,
            attempt=attempt,
        )
        partition = partition_dirichlet_rows(
            rows,
            condition=condition,
            client_count=int(setup.client_count.value),
            seed=seed,
            retry_attempt=attempt,
        )
        if all(
            dict(counts).get(split, 0) >= minimum
            for _, counts in partition.row_counts
            for split, minimum in minimums.items()
        ):
            assignments = pl.DataFrame(
                {
                    "source_path": [path for path, _, _, _ in partition.assignments],
                    "source_row_index": [index for _, _, index, _ in partition.assignments],
                    "client_id": [client_id for _, _, _, client_id in partition.assignments],
                }
            )
            reassigned = frame.drop("client_id").join(
                assignments, on=("source_path", "source_row_index"), how="left", validate="1:1"
            )
            if reassigned["client_id"].null_count() != 0:
                raise ValueError("N-BaIoT partition left source rows unassigned")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            reassigned.write_parquet(target_path, compression="zstd")
            return partition
    raise ValueError(
        "N-BaIoT Dirichlet partition is infeasible after configured deterministic retries")
