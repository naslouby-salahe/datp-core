"""Bounded, streaming N-BaIoT source inspection.

The N-BaIoT corpus is a directory tree, not a table with a device column.  This
adapter deliberately derives labels and client provenance only from that locked
tree shape.  It never infers a client from a filename or joins independent
sources by row position.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from hashlib import blake2b
from math import isfinite
from pathlib import Path

from ...catalogue.domain import DatasetDefinition
from ...kernel.fingerprints import Fingerprint, fingerprint
from ...kernel.ids import DatasetId
from ...kernel.values import StructuredValue
from ..domain import DatasetReadinessReport, ReadinessStatus, SchemaSummary, SourceFileManifest, SourceFinding

_DATASET_ID = DatasetId("nbaiot")
_CHECKSUM_ALGORITHM = "blake2b-256"


class NBaIoTAdapter:
    """Inspect configured N-BaIoT source files in deterministic path order."""

    dataset_id = _DATASET_ID

    def inspect(
        self, definition: DatasetDefinition, raw_root: Path, *, max_files: int | None = None
    ) -> DatasetReadinessReport:
        """Return a source-evidenced readiness report without materializing rows.

        Files are parsed one at a time and CSV rows are never accumulated.  A
        positive ``max_files`` is useful for fixture probes; a truncated probe
        is intentionally blocked because it cannot establish whole-corpus
        readiness.
        """
        if definition.identifier != self.dataset_id:
            return _blocked_for_wrong_definition(definition.identifier)
        if max_files is not None and max_files < 1:
            return _blocked_invalid_limit(max_files)

        layout = definition.source_layout
        schema = definition.field_schema
        source_root_name = _required_string(layout, "root")
        device_dirs = _required_strings(layout, "device_dirs")
        benign_name = _required_string(layout, "benign_file")
        attack_families = _required_strings(layout, "attack_family_dirs")
        attack_pattern = _required_string(layout, "attack_file_pattern")
        benign_required = _required_bool(layout, "benign_file_required_per_device")
        ignored_suffixes = _required_strings(layout, "ignored_source_suffixes")
        ignored_root_entries = _required_strings(layout, "ignored_root_entries")
        expected_header = _model_feature_order(schema)
        expected_field_count = _required_positive_integer(schema, "source_column_count")

        findings: list[SourceFinding] = []
        source_root = raw_root / source_root_name
        if not source_root.is_dir():
            findings.append(_finding("source_missing", f"source root does not exist: {source_root_name}"))
            return _report(definition.identifier, (), (), expected_field_count, findings)
        _validate_root_entries(source_root, device_dirs, ignored_root_entries, frozenset(ignored_suffixes), findings)
        candidates = _discover_files(
            source_root=source_root,
            device_dirs=device_dirs,
            benign_name=benign_name,
            attack_families=attack_families,
            attack_pattern=attack_pattern,
            benign_required=benign_required,
            ignored_suffixes=frozenset(ignored_suffixes),
            findings=findings,
        )
        selected = candidates if max_files is None else candidates[:max_files]
        if max_files is not None and len(candidates) > len(selected):
            findings.append(
                _finding(
                    "inspection_truncated",
                    (
                        f"inspected {len(selected)} of {len(candidates)} source files; "
                        "whole-corpus readiness is unresolved"
                    ),
                )
            )

        manifests: list[SourceFileManifest] = []
        observed_headers: list[tuple[str, ...]] = []
        for path, role in selected:
            manifest, file_findings = _inspect_file(path, raw_root, role, expected_header, expected_field_count)
            findings.extend(file_findings)
            if manifest is not None:
                manifests.append(manifest)
                observed_headers.append(manifest.header)

        return _report(definition.identifier, manifests, observed_headers, expected_field_count, findings)


def _discover_files(
    *,
    source_root: Path,
    device_dirs: tuple[str, ...],
    benign_name: str,
    attack_families: tuple[str, ...],
    attack_pattern: str,
    benign_required: bool,
    ignored_suffixes: frozenset[str],
    findings: list[SourceFinding],
) -> tuple[tuple[Path, str], ...]:
    discovered: list[tuple[Path, str]] = []
    for device in device_dirs:
        device_path = source_root / device
        if not device_path.is_dir():
            findings.append(_finding("device_directory_missing", f"configured device directory is missing: {device}"))
            continue
        if device_path.is_symlink():
            findings.append(_finding("source_symlink_forbidden", f"device directory is a symlink: {device}"))
            continue
        _validate_device_entries(device_path, benign_name, attack_families, ignored_suffixes, findings)

        benign = device_path / benign_name
        if not benign.is_file():
            if benign_required:
                findings.append(
                    _finding("benign_file_missing", f"required benign file is missing: {device}/{benign_name}")
                )
        else:
            discovered.append((benign, f"benign;client={device};label=benign_traffic"))

        for family in attack_families:
            family_path = device_path / family
            if not family_path.exists():
                continue
            if not family_path.is_dir():
                findings.append(
                    _finding("attack_family_not_directory", f"attack family is not a directory: {device}/{family}")
                )
                continue
            if family_path.is_symlink():
                findings.append(_finding("source_symlink_forbidden", f"attack family is a symlink: {device}/{family}"))
                continue
            for attack_file in sorted(family_path.rglob(attack_pattern), key=lambda item: item.as_posix()):
                if attack_file.suffix in ignored_suffixes:
                    continue
                if not attack_file.is_file():
                    continue
                relative_attack = attack_file.relative_to(family_path).as_posix()
                discovered.append(
                    (
                        attack_file,
                        f"attack;client={device};family={family};attack_file={relative_attack};label={family.removesuffix('_attacks')}",
                    )
                )

    # A sorted relative path is a locked source-ordering input, regardless of
    # the configured device list's presentation order.
    return tuple(sorted(discovered, key=lambda item: item[0].relative_to(source_root).as_posix()))


def _validate_root_entries(
    source_root: Path,
    device_dirs: tuple[str, ...],
    ignored_entries: tuple[str, ...],
    ignored_suffixes: frozenset[str],
    findings: list[SourceFinding],
) -> None:
    allowed = frozenset(device_dirs) | frozenset(ignored_entries)
    try:
        entries = tuple(sorted(source_root.iterdir(), key=lambda path: path.name))
    except OSError as error:
        findings.append(_finding("source_root_unreadable", f"cannot enumerate N-BaIoT source root: {error}"))
        return
    for entry in entries:
        if entry.name not in allowed and entry.suffix not in ignored_suffixes:
            findings.append(_finding("unexpected_root_entry", f"unconfigured source-root entry: {entry.name}"))


def _validate_device_entries(
    device_path: Path,
    benign_name: str,
    attack_families: tuple[str, ...],
    ignored_suffixes: frozenset[str],
    findings: list[SourceFinding],
) -> None:
    allowed = frozenset((benign_name, *attack_families))
    try:
        entries = tuple(sorted(device_path.iterdir(), key=lambda path: path.name))
    except OSError as error:
        findings.append(_finding("device_directory_unreadable", f"cannot enumerate {device_path.name}: {error}"))
        return
    for entry in entries:
        if entry.name not in allowed and entry.suffix not in ignored_suffixes:
            findings.append(
                _finding("unexpected_device_entry", f"unconfigured entry for device {device_path.name}: {entry.name}")
            )


def _inspect_file(
    path: Path,
    raw_root: Path,
    role: str,
    expected_header: tuple[str, ...],
    expected_field_count: int,
) -> tuple[SourceFileManifest | None, tuple[SourceFinding, ...]]:
    relative_path = path.relative_to(raw_root).as_posix()
    findings: list[SourceFinding] = []
    if path.is_symlink():
        return None, (_finding("source_symlink_forbidden", f"source file is a symlink: {relative_path}"),)
    try:
        byte_count = path.stat().st_size
        checksum = _checksum(path)
    except OSError as error:
        return None, (_finding("source_unreadable", f"cannot read {relative_path}: {error}"),)

    header: tuple[str, ...] = ()
    parse_completed = True
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            header = tuple(next(reader))
            if len(header) != expected_field_count:
                findings.append(
                    _finding(
                        "header_field_count_mismatch",
                        f"{relative_path} header has {len(header)} fields; expected {expected_field_count}",
                    )
                )
            if header != expected_header:
                findings.append(
                    _finding("header_mismatch", f"{relative_path} header differs from configured model feature order")
                )
            for row_index, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    findings.append(
                        _finding(
                            "row_field_count_mismatch",
                            f"{relative_path} row {row_index} has {len(row)} fields; expected {len(header)}",
                        )
                    )
                    continue
                for column_index, value in enumerate(row):
                    try:
                        number = float(value)
                    except ValueError:
                        findings.append(
                            _finding(
                                "non_numeric_feature",
                                f"{relative_path} row {row_index} column {column_index + 1} is not numeric",
                            )
                        )
                        continue
                    if not isfinite(number):
                        findings.append(
                            _finding(
                                "non_finite_feature",
                                f"{relative_path} row {row_index} column {column_index + 1} is not finite",
                            )
                        )
    except StopIteration:
        parse_completed = False
        findings.append(_finding("header_missing", f"{relative_path} is empty and has no header"))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        parse_completed = False
        findings.append(_finding("csv_unreadable", f"cannot parse {relative_path}: {error}"))

    if not parse_completed:
        return None, tuple(findings)
    return (
        SourceFileManifest(
            relative_path=relative_path,
            source_role=role,
            byte_count=byte_count,
            checksum=checksum,
            header=header,
            field_count=len(header),
        ),
        tuple(findings),
    )


def _checksum(path: Path) -> Fingerprint:
    digest = blake2b(digest_size=32)
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return Fingerprint(algorithm=_CHECKSUM_ALGORITHM, hexadecimal=digest.hexdigest())


def _report(
    dataset_id: DatasetId,
    manifests: tuple[SourceFileManifest, ...] | list[SourceFileManifest],
    observed_headers: tuple[tuple[str, ...], ...] | list[tuple[str, ...]],
    expected_field_count: int,
    findings: list[SourceFinding],
) -> DatasetReadinessReport:
    immutable_manifests = tuple(manifests)
    immutable_headers = tuple(observed_headers)
    header_consistent = len(set(immutable_headers)) <= 1
    if not header_consistent:
        findings.append(_finding("headers_not_identical", "source headers are not identical across inspected files"))
    if not immutable_manifests and not findings:
        findings.append(_finding("no_source_files", "no N-BaIoT source files were discovered"))
    ordered_findings = tuple(findings)
    return DatasetReadinessReport(
        dataset_id=dataset_id,
        source_fingerprint=fingerprint(
            tuple(
                (manifest.relative_path, manifest.checksum.hexadecimal, manifest.byte_count)
                for manifest in immutable_manifests
            )
        ),
        files=tuple(manifest.relative_path for manifest in immutable_manifests),
        findings=ordered_findings,
        status=ReadinessStatus.BLOCKED if ordered_findings else ReadinessStatus.READY,
        source_files=immutable_manifests,
        schema=SchemaSummary(
            expected_field_count=expected_field_count,
            observed_headers=immutable_headers,
            header_consistent=header_consistent,
        ),
    )


def _blocked_for_wrong_definition(dataset_id: DatasetId) -> DatasetReadinessReport:
    finding = _finding("wrong_dataset_definition", f"N-BaIoT adapter cannot inspect dataset {dataset_id}")
    return _report(dataset_id, (), (), 0, [finding])


def _blocked_invalid_limit(max_files: int) -> DatasetReadinessReport:
    finding = _finding("invalid_max_files", f"max_files must be positive when supplied, got {max_files}")
    return _report(_DATASET_ID, (), (), 0, [finding])


def _finding(code: str, message: str) -> SourceFinding:
    return SourceFinding(code=code, message=message)


def _required_string(values: Mapping[str, StructuredValue], key: str) -> str:
    value = values[key]
    if not isinstance(value, str):
        raise ValueError(f"N-BaIoT configuration {key} must be a string")
    return value


def _required_strings(values: Mapping[str, StructuredValue], key: str) -> tuple[str, ...]:
    value = values[key]
    if not isinstance(value, tuple):
        raise ValueError(f"N-BaIoT configuration {key} must be a sequence of strings")
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"N-BaIoT configuration {key} must be a sequence of strings")
        strings.append(item)
    return tuple(strings)


def _required_positive_integer(values: Mapping[str, StructuredValue], key: str) -> int:
    value = values[key]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"N-BaIoT configuration {key} must be a positive integer")
    return value


def _required_bool(values: Mapping[str, StructuredValue], key: str) -> bool:
    value = values[key]
    if not isinstance(value, bool):
        raise ValueError(f"N-BaIoT configuration {key} must be a boolean")
    return value


def _model_feature_order(values: Mapping[str, StructuredValue]) -> tuple[str, ...]:
    model_features = values["model_features"]
    if not isinstance(model_features, Mapping):
        raise ValueError("N-BaIoT model_features must be a mapping")
    return _required_strings(model_features, "order")
