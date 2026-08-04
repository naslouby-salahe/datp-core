"""Stage: compose external and temporal population split publication."""

from datp_core.orchestration.commands.populations import (
    SplitRequest as _SplitRequest,
    SplitResult as _SplitResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.populations.splitting import (
    PopulationSplitRequest,
    SplitPublicationAsset,
    load_reused_population_split,
    population_split_is_reusable,
    prepare_population_split,
    rebase_population_split,
    write_population_split,
)


def split_stage(request: _SplitRequest) -> _SplitResult:
    prepared = prepare_population_split(
        PopulationSplitRequest(
            population=request.population,
            execution_identity=request.execution_identity,
            population_manifest=request.population_manifest,
            membership=request.membership,
            partition_seed=request.partition_seed,
            matched_static_reference_manifest=request.matched_static_reference_manifest,
            matched_static_reference_membership=request.matched_static_reference_membership,
        )
    )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=write_population_split,
                validator=population_split_is_reusable,
                loader=load_reused_population_split,
                rebaser=rebase_population_split,
            ),
            overwrite=request.overwrite,
            complete_marker=SplitPublicationAsset.COMPLETE,
        )
    )
    artifacts = publication.value
    return _SplitResult(
        publication_status=publication.status,
        assignments=artifacts.assignments,
        manifest=artifacts.manifest,
        matched_static_reference_assignments=artifacts.matched_static_reference_assignments,
        matched_static_reference_manifest=artifacts.matched_static_reference_manifest,
        complete_digest=publication.complete_digest,
    )
