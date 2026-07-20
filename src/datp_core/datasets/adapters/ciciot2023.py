"""Bounded, streaming source inspection for the CICIoT2023 file-pseudo-client regime.

The merged files are the only executable source.  Per-class files are inspected
only for layout and schema evidence; this module deliberately has no operation
which could join those trees.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import blake2b
from math import isfinite
from pathlib import Path

from ...catalogue.domain import DatasetDefinition
from ...kernel.fingerprints import Fingerprint, fingerprint
from ...kernel.ids import DatasetId
from ...kernel.values import StructuredValue
from ..domain import DatasetReadinessReport, ReadinessStatus, SchemaSummary, SourceFileManifest, SourceFinding

_CHUNK_BYTES = 1024 * 1024
_EXECUTABLE_ROLE = "executable"
_REFERENCE_ROLE = "reference_only"


@dataclass(frozen=True, slots=True)
class _SourceSpec:
    name: str
    role: str
    relative_root: str
    file_pattern: str
    expected_field_count: int


@dataclass(frozen=True, slots=True)
class _FileInspection:
    manifest: SourceFileManifest
    findings: tuple[SourceFinding, ...]
    blocked: bool


class Ciciot2023Adapter:
    """Inspect CICIoT2023 without inferring physical-device identity."""

    dataset_id = DatasetId("ciciot2023")

    def inspect(
        self, definition: DatasetDefinition, raw_root: Path, *, max_files: int | None = None
    ) -> DatasetReadinessReport:
        findings: list[SourceFinding] = []
        if definition.identifier != self.dataset_id:
            return _blocked_report(
                definition.identifier,
                "dataset_mismatch",
                f"CICIoT2023 adapter cannot inspect dataset {definition.identifier}",
            )
        if max_files is not None and max_files <= 0:
            return _blocked_report(
                self.dataset_id,
                "invalid_max_files",
                "max_files must be positive when supplied",
            )

        try:
            specifications, model_features = _source_specs(definition)
        except ValueError as error:
            return _blocked_report(self.dataset_id, "invalid_ciciot_contract", str(error))

        discoveries: list[tuple[_SourceSpec, Path, str]] = []
        blocked = False
        for specification in specifications:
            source_root = raw_root / specification.relative_root
            try:
                resolved_root = source_root.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                code = "broken_symlink" if source_root.is_symlink() else "source_missing"
                findings.append(
                    SourceFinding(code=code, message=f"{specification.name} source root is unreadable: {error}")
                )
                blocked = True
                continue
            if not resolved_root.is_dir():
                findings.append(
                    SourceFinding(
                        code="source_not_directory",
                        message=f"{specification.name} source root is not a directory: {specification.relative_root}",
                    )
                )
                blocked = True
                continue
            try:
                matches = tuple(
                    sorted(resolved_root.glob(specification.file_pattern), key=lambda path: path.as_posix())
                )
            except OSError as error:
                findings.append(
                    SourceFinding(
                        code="source_discovery_failed",
                        message=f"{specification.name} discovery failed: {error}",
                    )
                )
                blocked = True
                continue
            files = tuple(path for path in matches if path.is_file() or path.is_symlink())
            if not files:
                findings.append(
                    SourceFinding(
                        code="no_matching_files",
                        message=f"{specification.name} has no files matching {specification.file_pattern}",
                    )
                )
                blocked = True
                continue
            selected_files = files if max_files is None else files[:max_files]
            if len(selected_files) != len(files):
                findings.append(
                    SourceFinding(
                        code="inspection_bounded",
                        message=(
                            f"{specification.name}: inspected {len(selected_files)} deterministically selected "
                            f"files of {len(files)} discovered files"
                        ),
                    )
                )
            for path in selected_files:
                try:
                    relative_path = path.relative_to(raw_root).as_posix()
                except ValueError:
                    # A permitted source-root symlink may point to a mounted raw corpus.
                    relative_path = specification.relative_root.rstrip("/") + "/" + path.name
                discoveries.append((specification, path, relative_path))

        discoveries.sort(key=lambda item: (item[2], item[0].name))
        inspections: list[_FileInspection] = []
        for specification, path, relative_path in discoveries:
            inspection = _inspect_file(specification, path, relative_path, model_features)
            inspections.append(inspection)
            findings.extend(inspection.findings)
            blocked = blocked or inspection.blocked

        manifests = tuple(inspection.manifest for inspection in inspections)
        headers_by_role = _headers_by_role(specifications, manifests)
        header_consistent = _headers_are_consistent(headers_by_role, model_features)
        if not header_consistent:
            findings.append(
                SourceFinding(
                    code="header_inconsistent",
                    message="CICIoT2023 headers do not satisfy the merged/per-class schema relationship",
                )
            )
            blocked = True
        if not blocked:
            findings.extend(
                (
                    SourceFinding(
                        code="pseudo_client_identity",
                        message="merged file names define pseudo-clients; physical-device identity is unavailable",
                    ),
                    SourceFinding(
                        code="reference_source_schema_only",
                        message=(
                            "per-class files were inspected only for layout/schema evidence and were not joined "
                            "to merged rows"
                        ),
                    ),
                    SourceFinding(
                        code="row_identity_provenance",
                        message="executable row identity is (merged source file path, source row index)",
                    ),
                    SourceFinding(
                        code="source_columns_classified",
                        message=(
                            "all merged source columns are classified as configured numeric model features or "
                            "the final Label field"
                        ),
                    ),
                )
            )

        observed_headers = tuple(sorted({manifest.header for manifest in manifests}))
        source_fingerprint = fingerprint(
            tuple(
                (manifest.relative_path, manifest.source_role, manifest.byte_count, manifest.checksum.hexadecimal)
                for manifest in manifests
            )
        )
        return DatasetReadinessReport(
            dataset_id=self.dataset_id,
            source_fingerprint=source_fingerprint,
            files=tuple(manifest.relative_path for manifest in manifests),
            findings=tuple(findings),
            status=ReadinessStatus.BLOCKED if blocked else ReadinessStatus.READY,
            source_files=manifests,
            schema=SchemaSummary(
                expected_field_count=next(
                    spec.expected_field_count for spec in specifications if spec.role == _EXECUTABLE_ROLE
                ),
                observed_headers=observed_headers,
                header_consistent=header_consistent,
            ),
        )


def _source_specs(definition: DatasetDefinition) -> tuple[tuple[_SourceSpec, ...], tuple[str, ...]]:
    source_layout = _require_mapping(definition.source_layout.get("sources"), "source_layout.sources")
    field_counts = _require_mapping(
        definition.field_schema.get("source_column_count"), "field_schema.source_column_count"
    )
    model_feature_definition = _require_mapping(
        definition.field_schema.get("model_features"), "field_schema.model_features"
    )
    model_features = _require_string_tuple(model_feature_definition.get("order"), "field_schema.model_features.order")
    if len(model_features) != _require_int(field_counts.get("per_class"), "source_column_count.per_class"):
        raise ValueError("per-class model feature count does not match its declared source column count")

    specifications: list[_SourceSpec] = []
    for name in ("merged", "per_class"):
        source = _require_mapping(source_layout.get(name), f"source_layout.sources.{name}")
        role = _require_string(source.get("role"), f"source_layout.sources.{name}.role")
        if role not in {_EXECUTABLE_ROLE, _REFERENCE_ROLE}:
            raise ValueError(f"source_layout.sources.{name}.role is not a CICIoT2023 source role")
        expected_field_count = _require_int(field_counts.get(name), f"source_column_count.{name}")
        specifications.append(
            _SourceSpec(
                name=name,
                role=role,
                relative_root=_require_relative_path(source.get("root"), f"source_layout.sources.{name}.root"),
                file_pattern=_require_string(source.get("file_pattern"), f"source_layout.sources.{name}.file_pattern"),
                expected_field_count=expected_field_count,
            )
        )
    if sum(spec.role == _EXECUTABLE_ROLE for spec in specifications) != 1:
        raise ValueError("CICIoT2023 must have exactly one executable source")
    return tuple(specifications), model_features


def _inspect_file(
    specification: _SourceSpec, path: Path, relative_path: str, model_features: tuple[str, ...]
) -> _FileInspection:
    findings: list[SourceFinding] = []
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        return _unreadable_file(specification, relative_path, error)
    if not resolved.is_file():
        return _unreadable_file(specification, relative_path, OSError("not a regular file"))
    try:
        checksum, byte_count = _checksum(resolved)
        with resolved.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = tuple(next(reader))
            expected_header = model_features + (("Label",) if specification.role == _EXECUTABLE_ROLE else ())
            blocked = False
            if len(header) != specification.expected_field_count:
                findings.append(
                    SourceFinding(
                        code="header_field_count_mismatch",
                        message=(
                            f"{relative_path} header has {len(header)} fields; expected "
                            f"{specification.expected_field_count}"
                        ),
                    )
                )
                blocked = True
            if header != expected_header:
                findings.append(
                    SourceFinding(
                        code="header_mismatch",
                        message=f"{relative_path} header does not match the configured {specification.name} schema",
                    )
                )
                blocked = True
            malformed_rows = 0
            empty_labels = 0
            invalid_numeric_rows = 0
            for _source_row_index, row in enumerate(reader, start=1):
                if len(row) != specification.expected_field_count:
                    malformed_rows += 1
                    continue
                if specification.role == _EXECUTABLE_ROLE:
                    if not row[-1].strip():
                        empty_labels += 1
                        continue
                    if not _numeric_features_are_finite(row[:-1]):
                        invalid_numeric_rows += 1
            if malformed_rows:
                findings.append(
                    SourceFinding(
                        code="malformed_rows_excluded",
                        message=f"{relative_path}: {malformed_rows} rows have an invalid field count and are excluded",
                    )
                )
            if empty_labels:
                findings.append(
                    SourceFinding(
                        code="empty_label_rows_excluded",
                        message=f"{relative_path}: {empty_labels} merged rows have a blank label and are excluded",
                    )
                )
            if invalid_numeric_rows:
                findings.append(
                    SourceFinding(
                        code="unparseable_numeric_feature",
                        message=(
                            f"{relative_path}: {invalid_numeric_rows} executable rows contain non-finite "
                            "numeric features"
                        ),
                    )
                )
                blocked = True
    except (OSError, UnicodeError, csv.Error, StopIteration) as error:
        return _unreadable_file(specification, relative_path, error)
    manifest = SourceFileManifest(
        relative_path=relative_path,
        source_role=specification.role,
        byte_count=byte_count,
        checksum=checksum,
        header=header,
        field_count=len(header),
    )
    return _FileInspection(manifest=manifest, findings=tuple(findings), blocked=blocked)


def _headers_by_role(
    specifications: tuple[_SourceSpec, ...], manifests: tuple[SourceFileManifest, ...]
) -> Mapping[str, tuple[tuple[str, ...], ...]]:
    roles = {specification.role for specification in specifications}
    return {role: tuple(manifest.header for manifest in manifests if manifest.source_role == role) for role in roles}


def _headers_are_consistent(
    headers_by_role: Mapping[str, tuple[tuple[str, ...], ...]], model_features: tuple[str, ...]
) -> bool:
    merged_headers = headers_by_role.get(_EXECUTABLE_ROLE, ())
    reference_headers = headers_by_role.get(_REFERENCE_ROLE, ())
    expected_merged = model_features + ("Label",)
    return (
        bool(merged_headers)
        and bool(reference_headers)
        and all(header == expected_merged for header in merged_headers)
        and all(header == model_features for header in reference_headers)
    )


def _checksum(path: Path) -> tuple[Fingerprint, int]:
    digest = blake2b(digest_size=32)
    byte_count = 0
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_BYTES):
            digest.update(chunk)
            byte_count += len(chunk)
    return Fingerprint(algorithm="blake2b-256", hexadecimal=digest.hexdigest()), byte_count


def _numeric_features_are_finite(values: list[str]) -> bool:
    try:
        return all(isfinite(float(value)) for value in values)
    except ValueError:
        return False


def _unreadable_file(specification: _SourceSpec, relative_path: str, error: Exception) -> _FileInspection:
    manifest = SourceFileManifest(
        relative_path=relative_path,
        source_role=specification.role,
        byte_count=0,
        checksum=fingerprint({"unreadable": relative_path}),
        header=(),
        field_count=specification.expected_field_count,
    )
    return _FileInspection(
        manifest=manifest,
        findings=(SourceFinding(code="source_file_unreadable", message=f"{relative_path}: {error}"),),
        blocked=True,
    )


def _blocked_report(dataset_id: DatasetId, code: str, message: str) -> DatasetReadinessReport:
    return DatasetReadinessReport(
        dataset_id=dataset_id,
        source_fingerprint=fingerprint({"blocked": code}),
        files=(),
        findings=(SourceFinding(code=code, message=message),),
        status=ReadinessStatus.BLOCKED,
    )


def _require_mapping(value: StructuredValue | None, location: str) -> Mapping[str, StructuredValue]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{location} must be a mapping")
    return value


def _require_string(value: StructuredValue | None, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{location} must be a non-empty string")
    return value


def _require_int(value: StructuredValue | None, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{location} must be a positive integer")
    return value


def _require_string_tuple(value: StructuredValue | None, location: str) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not value:
        raise ValueError(f"{location} must be a non-empty string sequence")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError(f"{location} must be a non-empty string sequence")
        items.append(item)
    return tuple(items)


def _require_relative_path(value: StructuredValue | None, location: str) -> str:
    path = _require_string(value, location)
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{location} must be a relative path without traversal")
    return path
