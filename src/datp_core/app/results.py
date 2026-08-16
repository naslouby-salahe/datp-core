from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from shutil import copy2, rmtree

from datp_core.app.contracts import (
    ArtifactKind,
    ArtifactRequirement,
    ArtifactRole,
    ArtifactValidity,
    CampaignRole,
    DeliveryBundleDisposition,
    EvidenceCompletion,
)
from datp_core.app.evidence import ExperimentEvidence, inspect_experiment_evidence
from datp_core.app.layout import DeliveryArtifactName, DeliveryDirectory
from datp_core.app.recipes import EXPERIMENT_RECIPES
from datp_core.artifacts.integrity import ArtifactDigest, artifact_byte_count, artifact_digest, require_nonempty_file
from datp_core.artifacts.serializers.json import canonical_json_text, serialize_json_model
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ArtifactIntegrityError, ErrorMessage
from datp_core.core.identifiers import ExperimentId, NonEmptyString
from datp_core.core.numeric import NonNegativeIntegerValue
from datp_core.runtime.configuration import RESULTS_ROOT


class DeliveryRelativePath(NonEmptyString):
    validation_name = "delivery relative path"


class SourceRelativePath(NonEmptyString):
    validation_name = "source relative path"


class DeliveryArtifactRecord(StrictModel):
    experiment: ExperimentId
    role: ArtifactRole
    kind: ArtifactKind
    source_path: SourceRelativePath
    bundle_path: DeliveryRelativePath
    sha256: ArtifactDigest
    byte_count: NonNegativeIntegerValue


class DeliveryManifest(StrictModel):
    artifacts: tuple[DeliveryArtifactRecord, ...]


class DeliveryExperimentSummary(StrictModel):
    experiment: ExperimentId
    campaign_role: CampaignRole
    completion: EvidenceCompletion
    json_artifacts: tuple[DeliveryRelativePath, ...]
    csv_artifacts: tuple[DeliveryRelativePath, ...]
    figure_artifacts: tuple[DeliveryRelativePath, ...]
    report_artifacts: tuple[DeliveryRelativePath, ...]


class DeliverySummary(StrictModel):
    experiments: tuple[DeliveryExperimentSummary, ...]
    passed_count: NonNegativeIntegerValue
    omitted_optional: tuple[ExperimentId, ...]
    omitted_incomplete: tuple[ExperimentId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class DeliveryBundleResult:
    disposition: DeliveryBundleDisposition
    root: Path
    manifest: DeliveryManifest
    summary: DeliverySummary


def generate_delivery_bundle(
    *,
    overwrite: bool,
    output_root: Path,
    results_root: Path = RESULTS_ROOT,
) -> DeliveryBundleResult:
    if overwrite and results_root.exists():
        rmtree(results_root)
    collected = tuple(_collect_passed(output_root))
    expected = DeliveryManifest(artifacts=tuple(record for _evidence, artifacts in collected for record in artifacts))
    summary = _summary(collected)
    if _bundle_is_current(results_root, expected, summary):
        return DeliveryBundleResult(
            disposition=DeliveryBundleDisposition.ALREADY_CURRENT,
            root=results_root,
            manifest=expected,
            summary=summary,
        )
    if results_root.exists():
        rmtree(results_root)
    _materialize(results_root, collected)
    serialize_json_model(expected, results_root / DeliveryArtifactName.MANIFEST)
    serialize_json_model(summary, results_root / DeliveryArtifactName.SUMMARY)
    _validate_bundle(results_root, expected)
    return DeliveryBundleResult(
        disposition=DeliveryBundleDisposition.GENERATED,
        root=results_root,
        manifest=expected,
        summary=summary,
    )


def _collect_passed(output_root: Path) -> tuple[tuple[ExperimentEvidence, tuple[DeliveryArtifactRecord, ...]], ...]:
    collected: list[tuple[ExperimentEvidence, tuple[DeliveryArtifactRecord, ...]]] = []
    for recipe in EXPERIMENT_RECIPES:
        evidence = inspect_experiment_evidence(recipe.experiment, output_root=output_root)
        if not evidence.passed:
            continue
        artifacts = tuple(_bundle_records(evidence))
        if not any(item.role is ArtifactRole.RESULT_JSON for item in artifacts):
            raise ArtifactIntegrityError(
                ErrorMessage(f"passed experiment is missing JSON evidence: {recipe.experiment.value}"),
                subject=recipe.experiment,
            )
        collected.append((evidence, artifacts))
    return tuple(collected)


def _bundle_records(evidence: ExperimentEvidence) -> tuple[DeliveryArtifactRecord, ...]:
    records: list[DeliveryArtifactRecord] = []
    seen: set[DeliveryRelativePath] = set()
    for item in evidence.artifacts:
        if item.spec.requirement is ArtifactRequirement.MANDATORY and item.validity is not ArtifactValidity.VALID:
            raise ArtifactIntegrityError(
                ErrorMessage(f"passed experiment has invalid mandatory artifact: {item.path}"),
                subject=evidence.experiment,
            )
        if item.validity is not ArtifactValidity.VALID or not item.path.is_file():
            continue
        bundle_name = DeliveryRelativePath(
            f"{_kind_directory(item.spec.kind).value}/{evidence.experiment.value}__{item.path.name}"
        )
        if bundle_name in seen:
            kind_dir = _kind_directory(item.spec.kind).value
            parent_name = item.path.parent.name
            bundle_name = DeliveryRelativePath(
                f"{kind_dir}/{evidence.experiment.value}__{parent_name}__{item.path.name}"
            )
        if bundle_name in seen:
            raise ArtifactIntegrityError(
                ErrorMessage(f"delivery filename collision for {evidence.experiment.value}: {bundle_name}"),
                subject=evidence.experiment,
            )
        seen.add(bundle_name)
        records.append(
            DeliveryArtifactRecord(
                experiment=evidence.experiment,
                role=item.spec.role,
                kind=item.spec.kind,
                source_path=SourceRelativePath(item.path.as_posix()),
                bundle_path=bundle_name,
                sha256=artifact_digest(item.path),
                byte_count=NonNegativeIntegerValue(artifact_byte_count(item.path)),
            )
        )
    return tuple(records)


def _kind_directory(kind: ArtifactKind) -> DeliveryDirectory:
    if kind is ArtifactKind.JSON:
        return DeliveryDirectory.JSON
    if kind is ArtifactKind.CSV:
        return DeliveryDirectory.CSV
    if kind is ArtifactKind.FIGURE:
        return DeliveryDirectory.FIGURES
    return DeliveryDirectory.REPORTS


def _summary(
    collected: tuple[tuple[ExperimentEvidence, tuple[DeliveryArtifactRecord, ...]], ...],
) -> DeliverySummary:
    passed_ids = frozenset(evidence.experiment for evidence, _ in collected)
    omitted_optional: list[ExperimentId] = []
    omitted_incomplete: list[ExperimentId] = []
    for recipe in EXPERIMENT_RECIPES:
        if recipe.experiment in passed_ids:
            continue
        if recipe.campaign_role is CampaignRole.OPTIONAL:
            omitted_optional.append(recipe.experiment)
        else:
            omitted_incomplete.append(recipe.experiment)
    experiments = tuple(
        DeliveryExperimentSummary(
            experiment=evidence.experiment,
            campaign_role=next(
                recipe.campaign_role for recipe in EXPERIMENT_RECIPES if recipe.experiment is evidence.experiment
            ),
            completion=evidence.completion,
            json_artifacts=tuple(item.bundle_path for item in artifacts if item.kind is ArtifactKind.JSON),
            csv_artifacts=tuple(item.bundle_path for item in artifacts if item.kind is ArtifactKind.CSV),
            figure_artifacts=tuple(item.bundle_path for item in artifacts if item.kind is ArtifactKind.FIGURE),
            report_artifacts=tuple(item.bundle_path for item in artifacts if item.kind is ArtifactKind.REPORT),
        )
        for evidence, artifacts in collected
    )
    return DeliverySummary(
        experiments=experiments,
        passed_count=NonNegativeIntegerValue(len(experiments)),
        omitted_optional=tuple(omitted_optional),
        omitted_incomplete=tuple(omitted_incomplete),
    )


def _bundle_is_current(results_root: Path, manifest: DeliveryManifest, summary: DeliverySummary) -> bool:
    manifest_path = results_root / DeliveryArtifactName.MANIFEST
    summary_path = results_root / DeliveryArtifactName.SUMMARY
    if not manifest_path.is_file() or not summary_path.is_file():
        return False
    try:
        existing_manifest = DeliveryManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        existing_summary = DeliverySummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False
    if canonical_json_text(existing_manifest) != canonical_json_text(manifest):
        return False
    if canonical_json_text(existing_summary) != canonical_json_text(summary):
        return False
    try:
        _validate_bundle(results_root, manifest)
    except ArtifactIntegrityError:
        return False
    return True


def _materialize(
    results_root: Path,
    collected: tuple[tuple[ExperimentEvidence, tuple[DeliveryArtifactRecord, ...]], ...],
) -> None:
    for directory in DeliveryDirectory:
        (results_root / directory.value).mkdir(parents=True, exist_ok=True)
    for _evidence, artifacts in collected:
        for record in artifacts:
            destination = results_root / record.bundle_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            copy2(Path(record.source_path), destination)


def _validate_bundle(results_root: Path, manifest: DeliveryManifest) -> None:
    if not manifest.artifacts:
        return
    seen = frozenset(item.bundle_path for item in manifest.artifacts)
    if len(seen) != len(manifest.artifacts):
        raise ArtifactIntegrityError(ErrorMessage("delivery manifest contains duplicate bundle paths"))
    for record in manifest.artifacts:
        path = results_root / record.bundle_path
        require_nonempty_file(path)
        digest = artifact_digest(path)
        if digest != record.sha256:
            raise ArtifactIntegrityError(
                ErrorMessage(f"delivery artifact digest mismatch: {record.bundle_path}"),
                subject=record.experiment,
            )
        if artifact_byte_count(path) != record.byte_count.value:
            raise ArtifactIntegrityError(
                ErrorMessage(f"delivery artifact size mismatch: {record.bundle_path}"),
                subject=record.experiment,
            )
