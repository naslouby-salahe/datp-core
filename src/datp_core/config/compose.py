from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from datp_core.config.documents import ConfigurationDocument, configuration_document_path
from datp_core.config.loader import ConfigurationDocumentLoader
from datp_core.config.locking import (
    ProtocolLockVerificationMode,
    ProtocolLockVerificationResult,
    canonical_json,
    verify_protocol_lock,
)
from datp_core.config.mapping.artifacts import map_artifact_config
from datp_core.config.mapping.catalog import map_profile_catalogue
from datp_core.config.mapping.execution import map_execution_profile_config
from datp_core.config.mapping.reporting import map_reporting_config
from datp_core.config.resolver import (
    ResolvedScientificCatalog,
    ResolveScientificCatalogRequest,
    resolve_scientific_catalog,
)
from datp_core.config.schemas.artifacts import ArtifactConfig
from datp_core.config.schemas.catalog import (
    DatasetCatalogConfig,
    EvaluationCatalogConfig,
    ExperimentCatalogConfig,
    ExperimentProfileReferenceConfig,
    ModelCatalogConfig,
    ProtocolCatalogConfig,
    RegimeCatalogConfig,
    TestCatalogConfig,
    ThresholdCatalogConfig,
)
from datp_core.config.schemas.execution import ExecutionProfilesConfig
from datp_core.config.schemas.reporting import ReportingConfig
from datp_core.domain.artifacts.lineage import ResolvedConfigurationIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import ConfigurationError
from datp_core.domain.experiments.protocols import ArtifactPolicy, ReportingPolicy
from datp_core.domain.experiments.specifications import ProfileCatalogueSpec
from datp_core.domain.runtime.execution_profiles import ExecutionProfileSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class ComposeRunConfigurationRequest:
    configuration_root: Path
    experiment_id: str
    execution_profile_id: str
    artifact_policy_id: str
    reporting_policy_id: str
    protocol_lock_mode: ProtocolLockVerificationMode


@dataclass(frozen=True, slots=True, kw_only=True)
class ComposeRunConfigurationResult:
    profile_catalogue: ProfileCatalogueSpec
    execution_profile: ExecutionProfileSpec
    artifact_policy: ArtifactPolicy
    reporting_policy: ReportingPolicy
    resolved_configuration_identity: ResolvedConfigurationIdentity
    protocol_lock: ProtocolLockVerificationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class ComposeTestConfigurationRequest:
    configuration_root: Path
    test_profile_id: str
    protocol_lock_mode: ProtocolLockVerificationMode


@dataclass(frozen=True, slots=True, kw_only=True)
class ComposeTestConfigurationResult:
    profile_catalogue: ProfileCatalogueSpec
    execution_profile: ExecutionProfileSpec
    resolved_configuration_identity: ResolvedConfigurationIdentity
    protocol_lock: ProtocolLockVerificationResult


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedRunReferenceCatalog:
    execution_profiles: tuple[ExecutionProfileSpec, ...]
    artifact_policy_id: str
    reporting_policy_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogueLockVerificationRequest:
    loader: ConfigurationDocumentLoader
    root: Path
    catalogue: ProfileCatalogueSpec
    execution_profiles: tuple[ExecutionProfileSpec, ...]
    mode: ProtocolLockVerificationMode


def compose_run_configuration(request: ComposeRunConfigurationRequest) -> ComposeRunConfigurationResult:
    (
        resolved,
        catalogue,
        execution_profiles,
        artifact_policy,
        reporting_policy,
        artifact_policy_id,
        reporting_policy_id,
        lock,
    ) = _compose_catalogue(
        root=request.configuration_root,
        lock_mode=request.protocol_lock_mode,
    )
    execution_profile = _require_experiment_reference(
        resolved=resolved,
        request=request,
        references=ResolvedRunReferenceCatalog(
            execution_profiles=execution_profiles,
            artifact_policy_id=artifact_policy_id,
            reporting_policy_id=reporting_policy_id,
        ),
    )
    return ComposeRunConfigurationResult(
        profile_catalogue=catalogue,
        execution_profile=execution_profile,
        artifact_policy=artifact_policy,
        reporting_policy=reporting_policy,
        resolved_configuration_identity=_catalogue_identity(catalogue=catalogue, execution_profile=execution_profile),
        protocol_lock=lock,
    )


def compose_test_configuration(request: ComposeTestConfigurationRequest) -> ComposeTestConfigurationResult:
    resolved, catalogue, execution_profiles, _, _, _, _, lock = _compose_catalogue(
        root=request.configuration_root,
        lock_mode=request.protocol_lock_mode,
    )
    matching_profiles = tuple(
        profile for profile in resolved.tests.profiles if profile.profile_id == request.test_profile_id
    )
    if len(matching_profiles) != 1:
        raise ConfigurationError(
            detail="test configuration request references an unknown test profile",
            section="compose",
            field=request.test_profile_id,
            mode="reference_resolution",
        )
    execution_profile = _execution_profile(
        profile_id=matching_profiles[0].execution_profile_id,
        profiles=execution_profiles,
    )
    return ComposeTestConfigurationResult(
        profile_catalogue=catalogue,
        execution_profile=execution_profile,
        resolved_configuration_identity=_catalogue_identity(catalogue=catalogue, execution_profile=execution_profile),
        protocol_lock=lock,
    )


def _compose_catalogue(
    *, root: Path, lock_mode: ProtocolLockVerificationMode
) -> tuple[
    ResolvedScientificCatalog,
    ProfileCatalogueSpec,
    tuple[ExecutionProfileSpec, ...],
    ArtifactPolicy,
    ReportingPolicy,
    str,
    str,
    ProtocolLockVerificationResult,
]:
    loader = ConfigurationDocumentLoader(root=root)
    resolved = _load_resolved_catalogue(loader=loader)
    catalogue = map_profile_catalogue(resolved)
    execution_profiles = tuple(map_execution_profile_config(profile) for profile in resolved.execution.profiles)
    artifact_config, reporting_config = _load_policy_configurations(loader=loader)
    artifact_policy = map_artifact_config(artifact_config)
    reporting_policy = map_reporting_config(reporting_config)
    lock = _verify_catalogue_lock(
        CatalogueLockVerificationRequest(
            loader=loader,
            root=root,
            catalogue=catalogue,
            execution_profiles=execution_profiles,
            mode=lock_mode,
        )
    )
    return (
        resolved,
        catalogue,
        execution_profiles,
        artifact_policy,
        reporting_policy,
        artifact_config.policy_id,
        reporting_config.policy_id,
        lock,
    )


def _load_resolved_catalogue(*, loader: ConfigurationDocumentLoader) -> ResolvedScientificCatalog:
    return resolve_scientific_catalog(
        ResolveScientificCatalogRequest(
            protocol=loader.load(document=ConfigurationDocument.SCIENTIFIC_PROTOCOL, schema_type=ProtocolCatalogConfig),
            datasets=loader.load(document=ConfigurationDocument.SCIENTIFIC_DATASETS, schema_type=DatasetCatalogConfig),
            regimes=loader.load(document=ConfigurationDocument.SCIENTIFIC_REGIMES, schema_type=RegimeCatalogConfig),
            models=loader.load(document=ConfigurationDocument.SCIENTIFIC_MODELS, schema_type=ModelCatalogConfig),
            thresholds=loader.load(
                document=ConfigurationDocument.SCIENTIFIC_THRESHOLDS,
                schema_type=ThresholdCatalogConfig,
            ),
            evaluation=loader.load(
                document=ConfigurationDocument.SCIENTIFIC_EVALUATION,
                schema_type=EvaluationCatalogConfig,
            ),
            experiments=loader.load(
                document=ConfigurationDocument.SCIENTIFIC_EXPERIMENTS,
                schema_type=ExperimentCatalogConfig,
            ),
            tests=loader.load(document=ConfigurationDocument.TEST_PROFILES, schema_type=TestCatalogConfig),
            execution=loader.load(
                document=ConfigurationDocument.EXECUTION_PROFILES, schema_type=ExecutionProfilesConfig
            ),
        )
    )


def _load_policy_configurations(*, loader: ConfigurationDocumentLoader) -> tuple[ArtifactConfig, ReportingConfig]:
    return (
        loader.load(document=ConfigurationDocument.ARTIFACT_POLICY, schema_type=ArtifactConfig),
        loader.load(document=ConfigurationDocument.REPORTING_POLICY, schema_type=ReportingConfig),
    )


def _verify_catalogue_lock(request: CatalogueLockVerificationRequest) -> ProtocolLockVerificationResult:
    documents = (
        ConfigurationDocument.SCIENTIFIC_PROTOCOL,
        ConfigurationDocument.SCIENTIFIC_DATASETS,
        ConfigurationDocument.SCIENTIFIC_REGIMES,
        ConfigurationDocument.SCIENTIFIC_MODELS,
        ConfigurationDocument.SCIENTIFIC_THRESHOLDS,
        ConfigurationDocument.SCIENTIFIC_EVALUATION,
        ConfigurationDocument.SCIENTIFIC_EXPERIMENTS,
        ConfigurationDocument.EXECUTION_PROFILES,
    )
    return verify_protocol_lock(
        manifest_path=configuration_document_path(root=request.root, document=ConfigurationDocument.PROTOCOL_LOCK),
        source_documents=tuple(
            (document.value, request.loader.raw_content(document=document)) for document in documents
        ),
        resolved_profiles=(
            ("profile_catalogue", request.catalogue),
            ("execution_profiles", request.execution_profiles),
        ),
        mode=request.mode,
    )


def _require_experiment_reference(
    *,
    resolved: ResolvedScientificCatalog,
    request: ComposeRunConfigurationRequest,
    references: ResolvedRunReferenceCatalog,
) -> ExecutionProfileSpec:
    matching = tuple(
        profile for profile in resolved.experiments.profiles if profile.experiment_id == request.experiment_id
    )
    if len(matching) != 1:
        raise ConfigurationError(
            detail="run configuration request must resolve exactly one experiment profile",
            section="compose",
            field=request.experiment_id,
            mode="reference_resolution",
        )
    profile = matching[0]
    _validate_requested_profile_references(profile=profile, request=request)
    _validate_configured_policy_references(request=request, references=references)
    return _execution_profile(profile_id=request.execution_profile_id, profiles=references.execution_profiles)


def _validate_requested_profile_references(
    *, profile: ExperimentProfileReferenceConfig, request: ComposeRunConfigurationRequest
) -> None:
    if profile.execution_profile_id != request.execution_profile_id:
        raise ConfigurationError(
            detail="run request execution profile must match the experiment's resolved execution profile",
            section="compose",
            field=request.execution_profile_id,
            mode="reference_resolution",
        )
    if (
        request.artifact_policy_id != profile.artifact_policy_id
        or request.reporting_policy_id != profile.reporting_policy_id
    ):
        raise ConfigurationError(
            detail="run request policies must match the resolved experiment policy references",
            section="compose",
            field="policy_id",
            mode="reference_resolution",
        )


def _validate_configured_policy_references(
    *, request: ComposeRunConfigurationRequest, references: ResolvedRunReferenceCatalog
) -> None:
    if request.artifact_policy_id != references.artifact_policy_id:
        _raise_unknown_policy_reference(kind="artifact", policy_id=request.artifact_policy_id)
    if request.reporting_policy_id != references.reporting_policy_id:
        _raise_unknown_policy_reference(kind="reporting", policy_id=request.reporting_policy_id)


def _raise_unknown_policy_reference(*, kind: str, policy_id: str) -> None:
    raise ConfigurationError(
        detail=f"experiment {kind} policy reference must resolve to the configured {kind} policy",
        section="compose",
        field=policy_id,
        mode="reference_resolution",
    )


def _execution_profile(*, profile_id: str, profiles: tuple[ExecutionProfileSpec, ...]) -> ExecutionProfileSpec:
    matches = tuple(profile for profile in profiles if profile.profile_id == profile_id)
    if len(matches) != 1:
        raise ConfigurationError(
            detail="execution profile resolution must produce exactly one profile",
            section="compose",
            field=profile_id,
            mode="reference_resolution",
        )
    return matches[0]


def _catalogue_identity(
    *, catalogue: ProfileCatalogueSpec, execution_profile: ExecutionProfileSpec
) -> ResolvedConfigurationIdentity:
    digest = sha256(canonical_json((catalogue, execution_profile)).encode("utf-8")).hexdigest()
    return ResolvedConfigurationIdentity(value=StageFingerprint(value=digest))
