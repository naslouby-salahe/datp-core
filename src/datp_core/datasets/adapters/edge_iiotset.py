"""Bounded, deterministic inspection for the Edge-IIoTset source contract."""

from __future__ import annotations

import csv
from hashlib import blake2b
from pathlib import Path

from ...catalogue.domain import DatasetDefinition
from ...kernel.fingerprints import Fingerprint, fingerprint
from ...kernel.ids import DatasetId
from ...kernel.values import StructuredValue
from ..domain import (
    DatasetReadinessReport,
    ReadinessStatus,
    SchemaSummary,
    SourceFileManifest,
    SourceFinding,
)


def _strings(value: StructuredValue | None) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        return ()
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return ()
        strings.append(item)
    return tuple(strings)


class EdgeIiotsetAdapter:
    dataset_id = DatasetId("edge_iiotset")

    def inspect(
        self, definition: DatasetDefinition, raw_root: Path, *, max_files: int | None = None
    ) -> DatasetReadinessReport:
        layout = definition.source_layout
        schema = definition.field_schema
        root_value = layout.get("root")
        normal_value = layout.get("normal_traffic_root")
        attack_value = layout.get("attack_traffic_root")
        if not isinstance(root_value, str) or not isinstance(normal_value, str) or not isinstance(attack_value, str):
            return _blocked(definition.identifier, "source_layout_invalid", "Edge source layout is incomplete")
        resolved_raw = _resolved_raw(raw_root)
        if resolved_raw is None:
            return _blocked(definition.identifier, "raw_root_invalid", "raw root is not a readable resolved directory")
        root = _under(resolved_raw, root_value)
        normal_root = _under(resolved_raw, normal_value)
        attack_root = _under(resolved_raw, attack_value)
        if (
            root is None
            or normal_root is None
            or attack_root is None
            or not normal_root.is_dir()
            or not attack_root.is_dir()
        ):
            return _blocked(definition.identifier, "source_missing", "configured Edge source roots are unavailable")
        groups = _strings(layout.get("normal_group_folders"))
        attacks = _strings(layout.get("attack_files"))
        files: list[tuple[Path, str]] = []
        for group in groups:
            candidates = sorted((normal_root / group).glob("*.csv"))
            if len(candidates) != 1:
                return _blocked(definition.identifier, "normal_group_contract", f"{group} must contain exactly one CSV")
            files.append((candidates[0], "normal"))
        for name in attacks:
            candidate = attack_root / name
            if not candidate.is_file():
                return _blocked(definition.identifier, "attack_file_missing", f"missing configured attack file: {name}")
            files.append((candidate, "attack"))
        selected = tuple(files if max_files is None else files[:max_files])
        expected_count = schema.get("source_column_count")
        columns = _strings(schema.get("source_columns"))
        if not isinstance(expected_count, int) or len(columns) != expected_count:
            return _blocked(
                definition.identifier,
                "schema_contract_invalid",
                "Edge schema count and header contract disagree",
            )
        manifests: list[SourceFileManifest] = []
        findings: list[SourceFinding] = []
        for path, role in selected:
            inspected = _inspect_csv(path, resolved_raw, role)
            if isinstance(inspected, SourceFinding):
                findings.append(inspected)
                continue
            manifests.append(inspected)
            if inspected.field_count != expected_count:
                findings.append(
                    SourceFinding(
                        code="field_count_mismatch",
                        message=f"{inspected.relative_path} has {inspected.field_count} columns",
                    )
                )
            elif inspected.header != columns:
                findings.append(
                    SourceFinding(
                        code="header_mismatch",
                        message=f"{inspected.relative_path} header differs from configured schema",
                    )
                )
        headers = tuple(manifest.header for manifest in manifests)
        schema_summary = SchemaSummary(
            expected_field_count=expected_count,
            observed_headers=headers,
            header_consistent=bool(headers) and len(set(headers)) == 1 and headers[0] == columns,
        )
        status = ReadinessStatus.READY if not findings and len(manifests) == len(selected) else ReadinessStatus.BLOCKED
        source_files = tuple(manifests)
        return DatasetReadinessReport(
            dataset_id=definition.identifier,
            source_fingerprint=fingerprint(
                tuple((item.relative_path, item.checksum.hexadecimal) for item in source_files)
            ),
            files=tuple(item.relative_path for item in source_files),
            findings=tuple(findings),
            status=status,
            source_files=source_files,
            schema=schema_summary,
        )


def _resolved_raw(raw_root: Path) -> Path | None:
    try:
        resolved = raw_root.resolve(strict=True)
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def _under(root: Path, relative: str) -> Path | None:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _inspect_csv(path: Path, raw_root: Path, role: str) -> SourceFileManifest | SourceFinding:
    try:
        resolved = path.resolve(strict=True)
        relative = resolved.relative_to(raw_root).as_posix()
        digest = blake2b(digest_size=32)
        with resolved.open("rb") as source:
            while chunk := source.read(65_536):
                digest.update(chunk)
        with resolved.open(newline="", encoding="utf-8") as source:
            header = next(csv.reader(source), None)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        return SourceFinding(code="source_unreadable", message=f"{path.name}: {error}")
    if header is None:
        return SourceFinding(code="empty_source", message=f"{path.name} has no header")
    return SourceFileManifest(
        relative_path=relative,
        source_role=role,
        byte_count=resolved.stat().st_size,
        checksum=Fingerprint(algorithm="blake2b-256", hexadecimal=digest.hexdigest()),
        header=tuple(header),
        field_count=len(header),
    )


def _blocked(dataset_id: DatasetId, code: str, message: str) -> DatasetReadinessReport:
    return DatasetReadinessReport(
        dataset_id=dataset_id,
        source_fingerprint=fingerprint({"dataset": dataset_id.value, "reason": code}),
        files=(),
        findings=(SourceFinding(code=code, message=message),),
        status=ReadinessStatus.BLOCKED,
    )
