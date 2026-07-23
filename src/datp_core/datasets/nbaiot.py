"""N-BaIoT path-derived identity and label materialization rules.

`derive_partition_seed` below delegates to the single canonical deterministic-seed-derivation
formula in `pipeline/determinism.py` (consolidating what were three independent but byte-identical
reimplementations across the pre-refactor codebase -- see that module's docstring).
"""

from __future__ import annotations

import json
import math
from io import BytesIO
from pathlib import Path
from random import Random

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
from attrs import define

from datp_core.datasets.common import SourceRow, SourceRowFailure, iter_numeric_csv_source, normalize_materialized_parquet
from datp_core.datasets.materialization import SourceInventory
from datp_core.datasets.models import (
    AdapterKind,
    DatasetMaterialization,
    DatasetSetup,
    PartitionSeedContract,
    ResolvedDataset,
    SetupClientConstructionRecord,
)
from datp_core.experiments.models import SweepConditionRecord
from datp_core.pipeline.determinism import derive_seed


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTMaterializedRow:
    """One N-BaIoT numeric row with configured identity and binary label semantics."""

    client_id: str
    attack_family: str | None
    is_attack: bool
    source_row: SourceRow


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTSplitRows:
    """Configured N-BaIoT chronological split, including intentionally excluded gaps."""

    train: tuple[NBaIoTMaterializedRow, ...]
    calibration: tuple[NBaIoTMaterializedRow, ...]
    test_benign: tuple[NBaIoTMaterializedRow, ...]
    test_attack: tuple[NBaIoTMaterializedRow, ...]
    excluded_gap_rows: tuple[NBaIoTMaterializedRow, ...]


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTChronologicalBoundaries:
    """Zero-based boundaries for one source file's configured chronological split."""

    train_end: int
    first_gap_end: int
    calibration_end: int
    second_gap_end: int
    row_count: int

    def role_for_benign_index(self, index: int) -> str:
        if not 0 <= index < self.row_count:
            raise IndexError("N-BaIoT benign source-row index is outside the configured source count")
        if index < self.train_end:
            return "train"
        if index < self.first_gap_end:
            return "excluded_gap"
        if index < self.calibration_end:
            return "calibration"
        if index < self.second_gap_end:
            return "excluded_gap"
        return "test"


def materialize_nbaiot_source_row(
    source_row: SourceRow,
    dataset_root: Path,
    benign_filename: str,
    attack_family_directories: tuple[str, ...],
) -> NBaIoTMaterializedRow:
    """Derive client and attack identity from the configured N-BaIoT source path."""
    try:
        relative_path = source_row.source_path.relative_to(dataset_root)
    except ValueError as exc:
        raise ValueError("N-BaIoT source row is outside the configured dataset root") from exc
    if len(relative_path.parts) < 2:
        raise ValueError("N-BaIoT source row has no configured device-directory identity")
    client_id = relative_path.parts[0]
    if relative_path.name == benign_filename:
        return NBaIoTMaterializedRow(
            client_id=client_id,
            attack_family=None,
            is_attack=False,
            source_row=source_row,
        )
    if len(relative_path.parts) >= 3 and relative_path.parts[1] in attack_family_directories:
        return NBaIoTMaterializedRow(
            client_id=client_id,
            attack_family=relative_path.parts[1],
            is_attack=True,
            source_row=source_row,
        )
    raise ValueError("N-BaIoT source row does not satisfy configured benign or attack path semantics")


def split_nbaiot_chronological_gapped_rows(
    rows: tuple[NBaIoTMaterializedRow, ...],
    train_fraction: float,
    first_gap_fraction: float,
    calibration_fraction: float,
    second_gap_fraction: float,
    test_fraction: float,
) -> NBaIoTSplitRows:
    """Apply configured per-client chronological fractions without shuffling or leakage."""
    fractions = (train_fraction, first_gap_fraction, calibration_fraction, second_gap_fraction, test_fraction)
    if any(not 0.0 <= fraction <= 1.0 for fraction in fractions) or not math.isclose(
        sum(fractions), 1.0, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError("N-BaIoT chronological split fractions must be probabilities summing exactly to one")
    benign = tuple(row for row in rows if not row.is_attack)
    attack = tuple(row for row in rows if row.is_attack)
    if tuple(sorted(benign, key=lambda row: row.source_row.source_row_index)) != benign:
        raise ValueError("N-BaIoT benign rows must be supplied in ascending source-row order")
    row_count = len(benign)
    train_end = int(train_fraction * row_count)
    first_gap_end = train_end + int(first_gap_fraction * row_count)
    calibration_end = first_gap_end + int(calibration_fraction * row_count)
    second_gap_end = calibration_end + int(second_gap_fraction * row_count)
    return NBaIoTSplitRows(
        train=benign[:train_end],
        calibration=benign[first_gap_end:calibration_end],
        test_benign=benign[second_gap_end:],
        test_attack=attack,
        excluded_gap_rows=benign[train_end:first_gap_end] + benign[calibration_end:second_gap_end],
    )


def calculate_nbaiot_chronological_boundaries(
    row_count: int, materialization: DatasetMaterialization
) -> NBaIoTChronologicalBoundaries:
    """Calculate the authored N-BaIoT source-file boundaries before streaming a second pass."""
    if row_count < 0:
        raise ValueError("N-BaIoT source row count cannot be negative")
    if materialization.split_method != "chronological_gapped":
        raise ValueError("N-BaIoT chronological materialization requires the configured chronological_gapped method")
    train_end = int(float(materialization.ratio("train")) * row_count)
    first_gap_end = train_end + int(float(materialization.ratio("gap_1")) * row_count)
    calibration_end = first_gap_end + int(float(materialization.ratio("calibration")) * row_count)
    second_gap_end = calibration_end + int(float(materialization.ratio("gap_2")) * row_count)
    return NBaIoTChronologicalBoundaries(
        train_end=train_end,
        first_gap_end=first_gap_end,
        calibration_end=calibration_end,
        second_gap_end=second_gap_end,
        row_count=row_count,
    )


def random_fractional_roles(
    row_count: int, materialization: DatasetMaterialization, source_path: Path
) -> tuple[str, ...]:
    """Assign exact configured random-fractional benign roles deterministically per source."""
    if materialization.split_method != "random_fractional" or materialization.split_seed is None:
        raise ValueError("N-BaIoT random materialization requires a configured random_fractional split and seed")
    if row_count < 0 or not math.isclose(
        sum(float(materialization.ratio(role)) for role in ("train", "calibration", "test")),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("N-BaIoT random split ratios must sum exactly to one")
    indices = list(range(row_count))
    Random(f"{materialization.split_seed.value}:{source_path.as_posix()}").shuffle(indices)
    train_count = int(float(materialization.ratio("train")) * row_count)
    calibration_count = int(float(materialization.ratio("calibration")) * row_count)
    roles = ["test"] * row_count
    for index in indices[:train_count]:
        roles[index] = "train"
    for index in indices[train_count : train_count + calibration_count]:
        roles[index] = "calibration"
    return tuple(roles)


@define(frozen=True, slots=True, kw_only=True)
class DirichletPartition:
    condition: str
    allocation: str
    seed: int
    retry_attempt: int
    source_domains: tuple[str, ...]
    proportions: tuple[tuple[str, tuple[float, ...]], ...]
    row_counts: tuple[tuple[str, tuple[tuple[str, int], ...]], ...]
    assignments: tuple[tuple[str, str, int, str], ...]

    def encode(self) -> bytes:
        payload = {
            "allocation": self.allocation,
            "assignments": [
                {"client_id": client_id, "source_domain": domain, "source_path": source_path, "source_row_index": index}
                for source_path, domain, index, client_id in self.assignments
            ],
            "client_count": len(self.proportions),
            "feasibility_status": "feasible",
            "partition_condition": self.condition,
            "partition_seed": self.seed,
            "per_client_row_counts": [
                {"client_id": client_id, "split_counts": dict(counts)} for client_id, counts in self.row_counts
            ],
            "per_client_source_domain_proportions": [
                {"client_id": client_id, "proportions": dict(zip(self.source_domains, proportions, strict=True))}
                for client_id, proportions in self.proportions
            ],
            "retry_attempts_used": self.retry_attempt,
            "source_domains": list(self.source_domains),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def derive_partition_seed(*, key: str, digest_bytes: int, partition_seed: int, condition: str, attempt: int) -> int:
    """Derive a deterministic partition retry seed from the configured seed namespace."""
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
    """Allocate split-preserving source rows to synthetic clients with locked capacity scoring."""
    if client_count < 1:
        raise ValueError("Dirichlet partition requires a positive client count")
    domains = tuple(sorted({domain for _, domain, _, _ in rows}))
    if not domains:
        raise ValueError("Dirichlet partition requires source rows")
    generator = np.random.default_rng(seed)
    client_ids = tuple(f"synthetic_{index:02d}" for index in range(client_count))
    if condition.allocation == "dirichlet":
        if condition.dirichlet_alpha is None or condition.dirichlet_alpha <= 0.0:
            raise ValueError("Dirichlet conditions require a positive alpha")
        draws = generator.dirichlet(np.full(len(domains), condition.dirichlet_alpha), size=client_count)
    elif condition.allocation == "equal_across_source_domains":
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
        role_rows = sorted((row for row in rows if row[0] == split), key=lambda row: (row[1], row[2], row[3]))
        remaining = [
            len(role_rows) // client_count + (index < len(role_rows) % client_count) for index in range(client_count)
        ]
        for _, domain, source_path, source_row_index in role_rows:
            candidates = [index for index, capacity in enumerate(remaining) if capacity > 0]
            winner = max(
                candidates,
                key=lambda index, domain=domain: (draws[index, domain_index[domain]] / remaining[index], -index),
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
    """Reassign split-preserved N-BaIoT rows to configured synthetic clients and write the result."""
    if setup.method != "dirichlet_partitioned_clients" or setup.client_count is None or setup.partition_seed is None:
        raise ValueError("N-BaIoT Dirichlet materialization requires complete synthetic-client configuration")
    if setup.attack_labels_used_in_partition_generation is not False:
        raise ValueError("N-BaIoT Dirichlet materialization must prohibit attack labels during allocation")
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
    configured_max_retries = retry_policy.get("max_retries", 0)
    if not isinstance(configured_max_retries, int) or configured_max_retries < 0:
        raise ValueError("N-BaIoT Dirichlet retry policy requires a non-negative integer max_retries")
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
    raise ValueError("N-BaIoT Dirichlet partition is infeasible after configured deterministic retries")


def write_nbaiot_source_parquet(
    source_path: Path,
    target_path: Path,
    dataset_root: Path,
    feature_headers: tuple[str, ...],
    benign_filename: str,
    attack_family_directories: tuple[str, ...],
    materialization: DatasetMaterialization,
    batch_size: int,
) -> int:
    """Validate/count a source then stream its configured split to a Parquet file."""
    if batch_size <= 0:
        raise ValueError("N-BaIoT Parquet batch size must be positive")
    valid_benign_count = 0
    for result in iter_numeric_csv_source(source_path, feature_headers):
        if isinstance(result, SourceRowFailure):
            raise ValueError(f"N-BaIoT source validation rejected row {result.source_row_index} in {source_path}")
        if not materialize_nbaiot_source_row(
            result, dataset_root, benign_filename, attack_family_directories
        ).is_attack:
            valid_benign_count += 1
    random_roles = (
        random_fractional_roles(valid_benign_count, materialization, source_path)
        if materialization.split_method == "random_fractional"
        else None
    )
    boundaries = (
        calculate_nbaiot_chronological_boundaries(valid_benign_count, materialization) if random_roles is None else None
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    schema = pa.schema(
        [
            ("split", pa.string()),
            ("client_id", pa.string()),
            ("is_attack", pa.bool_()),
            ("attack_family", pa.string()),
            ("source_path", pa.string()),
            ("source_row_index", pa.int64()),
            *((header, pa.float64()) for header in feature_headers),
        ]
    )
    benign_index = 0
    written = 0
    records: dict[str, list[object]] = {field.name: [] for field in schema}
    with pq.ParquetWriter(target_path, schema, compression="zstd", use_dictionary=False) as writer:
        for result in iter_numeric_csv_source(source_path, feature_headers):
            if isinstance(result, SourceRowFailure):
                raise ValueError(f"N-BaIoT source changed between validation and write: {source_path}")
            row = materialize_nbaiot_source_row(result, dataset_root, benign_filename, attack_family_directories)
            if row.is_attack:
                role = "test"
            elif random_roles is not None:
                role = random_roles[benign_index]
            else:
                assert boundaries is not None
                role = boundaries.role_for_benign_index(benign_index)
            benign_index += not row.is_attack
            if role == "excluded_gap":
                continue
            records["split"].append(role)
            records["client_id"].append(row.client_id)
            records["is_attack"].append(row.is_attack)
            records["attack_family"].append(row.attack_family)
            records["source_path"].append(row.source_row.source_path.as_posix())
            records["source_row_index"].append(row.source_row.source_row_index)
            for header, value in zip(feature_headers, row.source_row.values, strict=True):
                records[header].append(value)
            if len(records["split"]) == batch_size:
                writer.write_table(pa.table(records, schema=schema))
                written += len(records["split"])
                records = {field.name: [] for field in schema}
        if records["split"]:
            writer.write_table(pa.table(records, schema=schema))
            written += len(records["split"])
    return written


def consolidate_nbaiot_parquet_sources(source_paths: tuple[Path, ...], target_path: Path, batch_size: int) -> int:
    """Consolidate staged source Parquet files through bounded Arrow record batches."""
    if not source_paths:
        raise ValueError("N-BaIoT consolidation requires at least one staged source file")
    if batch_size <= 0:
        raise ValueError("N-BaIoT consolidation batch size must be positive")
    first_file = pq.ParquetFile(source_paths[0])
    target_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with pq.ParquetWriter(target_path, first_file.schema_arrow, compression="zstd", use_dictionary=False) as writer:
        for source_path in source_paths:
            parquet_file = pq.ParquetFile(source_path)
            if parquet_file.schema_arrow != first_file.schema_arrow:
                raise ValueError("N-BaIoT staged Parquet schema mismatch")
            for batch in parquet_file.iter_batches(batch_size=batch_size):
                writer.write_batch(batch)
                written += batch.num_rows
    return written


def split_nbaiot_using_resolved_materialization(
    rows: tuple[NBaIoTMaterializedRow, ...], materialization: DatasetMaterialization
) -> NBaIoTSplitRows:
    """Apply the exact resolved authored N-BaIoT chronological split contract."""
    if materialization.split_method != "chronological_gapped":
        raise ValueError("N-BaIoT chronological materialization requires the configured chronological_gapped method")
    return split_nbaiot_chronological_gapped_rows(
        rows,
        float(materialization.ratio("train")),
        float(materialization.ratio("gap_1")),
        float(materialization.ratio("calibration")),
        float(materialization.ratio("gap_2")),
        float(materialization.ratio("test")),
    )


def encode_nbaiot_split_as_parquet(split: NBaIoTSplitRows, feature_headers: tuple[str, ...]) -> bytes:
    """Encode a complete typed N-BaIoT split as deterministic Parquet payload bytes."""
    ordered_rows = (
        *(("train", row) for row in split.train),
        *(("calibration", row) for row in split.calibration),
        *(("test", row) for row in split.test_benign),
        *(("test", row) for row in split.test_attack),
    )
    records: dict[str, list[object]] = {
        "split": [],
        "client_id": [],
        "is_attack": [],
        "attack_family": [],
        "source_path": [],
        "source_row_index": [],
    }
    records.update({header: [] for header in feature_headers})
    for split_name, materialized_row in ordered_rows:
        values = materialized_row.source_row.values
        if len(values) != len(feature_headers):
            raise ValueError("N-BaIoT source row width does not match the resolved feature schema")
        records["split"].append(split_name)
        records["client_id"].append(materialized_row.client_id)
        records["is_attack"].append(materialized_row.is_attack)
        records["attack_family"].append(materialized_row.attack_family)
        records["source_path"].append(materialized_row.source_row.source_path.as_posix())
        records["source_row_index"].append(materialized_row.source_row.source_row_index)
        for header, value in zip(feature_headers, values, strict=True):
            records[header].append(value)
    table = pa.table(records)
    payload = BytesIO()
    pq.write_table(table, payload, compression="zstd", use_dictionary=False)
    return payload.getvalue()


@define(frozen=True, slots=True, kw_only=True)
class NBaIoTMaterializationPayload:
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    partition_evidence: bytes | None = None


class NBaIoTAdapter:
    """N-BaIoT dataset materializer: path-derived identity, chronological split, Parquet output."""

    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.NBAIOT

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
        partition_condition: SweepConditionRecord | None,
        partition_seed_contract: PartitionSeedContract | None,
    ) -> NBaIoTMaterializationPayload:
        inspection = dataset.inspection_contract
        if inspection.benign_filename is None:
            raise ValueError("N-BaIoT configured benign filename is absent")

        primary_tree = inspection.source_trees[0]
        feature_headers = primary_tree.required_headers
        attack_family_directories = inspection.attack_family_directories
        dataset_root = dataset.paths.raw_root.resolve()
        chunk_row_count = 100_000

        staged_files: list[Path] = []
        for source_index, entry in enumerate(inventory.entries):
            staged_file = staging_root / f"source_{source_index:04d}.parquet"
            write_nbaiot_source_parquet(
                entry.source_path,
                staged_file,
                dataset_root,
                feature_headers,
                inspection.benign_filename,
                attack_family_directories,
                materialization,
                chunk_row_count,
            )
            staged_files.append(staged_file)

        unprocessed_payload = staging_root / "unprocessed.parquet"
        total_rows = consolidate_nbaiot_parquet_sources(tuple(staged_files), unprocessed_payload, chunk_row_count)
        partition_evidence = None
        partitioned_payload = unprocessed_payload
        if setup.client_construction.method == "dirichlet_partitioned_clients":
            if partition_condition is None:
                raise ValueError("Dirichlet materialization requires a resolved partition condition")
            if partition_seed_contract is None:
                raise ValueError("Dirichlet materialization requires the resolved partition seed contract")
            partitioned_payload = staging_root / "partitioned.parquet"
            partition = apply_nbaiot_dirichlet_partition(
                unprocessed_payload,
                partitioned_payload,
                setup=setup.client_construction,
                condition=partition_condition,
                seed_key=partition_seed_contract.key,
                digest_bytes=int(partition_seed_contract.digest_bytes.value),
            )
            partition_evidence = partition.encode()
        elif partition_condition is not None or partition_seed_contract is not None:
            raise ValueError("Physical-device N-BaIoT materialization cannot use a partition condition")
        payload_file = staging_root / "materialized.parquet"
        feature_columns = dataset.field_schema.model_features
        if feature_columns is None:
            raise ValueError("N-BaIoT materialization requires configured model features")
        normalization = normalize_materialized_parquet(
            partitioned_payload,
            payload_file,
            feature_columns=feature_columns.order,
            strategy=materialization.normalization_strategy,
            scope=materialization.normalization_scope,
        )

        return NBaIoTMaterializationPayload(
            staged_path=payload_file,
            row_count=total_rows,
            preprocessing_evidence=normalization.encode(),
            partition_evidence=partition_evidence,
        )
