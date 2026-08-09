"""Shared canonical materialization lifecycle for every audited dataset adapter."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.data.canonical_cache import CanonicalReuseRequest, reuse_published_canonical
from datp_core.data.contracts import CanonicalSchema, MaterializedDataset, ModelInputEligibilityPolicy
from datp_core.data.materialization import CanonicalPublication, publish_canonical


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalMaterializationRequest[AssetRoleT: StrEnum, EligibilityReasonT: StrEnum]:
    canonical_root: Path
    schema: CanonicalSchema
    canonicalization_contract: str  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    source_paths: tuple[Path, ...]
    source_path_resolver: Callable[[Path], Path]
    asset_role_type: type[AssetRoleT]
    prepare_publication: Callable[[], CanonicalPublication[AssetRoleT, EligibilityReasonT]]
    eligibility_policy: ModelInputEligibilityPolicy[EligibilityReasonT] | None = None

    def __post_init__(self) -> None:
        if not self.canonicalization_contract.strip():
            raise ValueError("canonical materialization requires a named canonicalization contract")
        if not self.source_paths:
            raise ValueError("canonical materialization requires accepted source paths")
        if self.source_paths != tuple(sorted(self.source_paths)):
            raise ValueError("canonical materialization source paths must be deterministically ordered")
        if len(self.source_paths) != len(frozenset(self.source_paths)):
            raise ValueError("canonical materialization source paths must be unique")


def materialize_canonical[
    AssetRoleT: StrEnum,
    EligibilityReasonT: StrEnum,
](
    request: CanonicalMaterializationRequest[AssetRoleT, EligibilityReasonT],
) -> MaterializedDataset[AssetRoleT, EligibilityReasonT]:
    """Reuse a complete publication or atomically execute one dataset-specific plan."""
    reusable = reuse_published_canonical(
        CanonicalReuseRequest(
            canonical_root=request.canonical_root,
            schema=request.schema,
            canonicalization_contract=request.canonicalization_contract,
            source_paths=request.source_paths,
            source_path_resolver=request.source_path_resolver,
            asset_role_type=request.asset_role_type,
            eligibility_policy=request.eligibility_policy,
        )
    )
    if reusable is not None:
        return reusable
    publication = request.prepare_publication()
    if publication.canonical_root != request.canonical_root:
        raise ValueError("prepared canonical publication changed its requested root")
    if publication.schema != request.schema:
        raise ValueError("prepared canonical publication changed its requested schema")
    if publication.canonicalization_contract != request.canonicalization_contract:
        raise ValueError("prepared canonical publication changed its canonicalization contract")
    if publication.source_paths != request.source_paths:
        raise ValueError("prepared canonical publication changed its audited source set")
    return publish_canonical(publication)
