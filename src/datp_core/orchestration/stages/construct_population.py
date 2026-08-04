"""Stage: compose external and temporal population publication."""

from datp_core.orchestration.commands.populations import (
    ConstructPopulationRequest as _ConstructPopulationRequest,
)
from datp_core.orchestration.commands.populations import (
    ConstructPopulationResult as _ConstructPopulationResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.populations.membership import (
    PopulationMembershipRequest,
    PopulationPublicationAsset,
    load_reused_population_membership,
    population_membership_is_reusable,
    prepare_population_membership,
    rebase_population_membership,
    write_population_membership,
)


def construct_population_stage(
    request: _ConstructPopulationRequest,
) -> _ConstructPopulationResult:
    prepared = prepare_population_membership(
        PopulationMembershipRequest(
            canonical_root=request.canonical_root,
            population=request.population,
            execution_identity=request.execution_identity,
            partition_seed=request.partition_seed,
            split_protocol=request.split_protocol,
        )
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=write_population_membership,
                validator=population_membership_is_reusable,
                loader=load_reused_population_membership,
                rebaser=rebase_population_membership,
            ),
            overwrite=request.overwrite,
            complete_marker=PopulationPublicationAsset.COMPLETE,
        )
    )
    artifacts = publication.value
    return _ConstructPopulationResult(
        publication_status=publication.status,
        population_manifest=artifacts.population_manifest,
        membership=artifacts.membership,
        chronology=artifacts.chronology,
        matched_static_reference_manifest=artifacts.matched_static_reference_manifest,
        matched_static_reference_membership=artifacts.matched_static_reference_membership,
        complete_digest=publication.complete_digest,
        ciciot_excluded_rows=artifacts.ciciot_excluded_rows,
        ciciot_client_eligibility=artifacts.ciciot_client_eligibility,
    )
