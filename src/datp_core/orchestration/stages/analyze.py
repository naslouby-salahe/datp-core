"""Stage: compose confirmatory, supplementary, and temporal analysis publication."""

from pathlib import Path

from datp_core.analysis.decisions import (
    AnalysisAssetName,
    AnalysisPublication,
    ConfirmatoryAnalysisRequest,
    ExternalAnalysisRequest,
    TemporalAnalysisRequest,
    analysis_publication_is_reusable,
    load_reused_analysis_publication,
    prepare_confirmatory_analysis,
    prepare_external_analysis,
    prepare_temporal_analysis,
    rebase_analysis_publication,
    write_analysis_publication,
)
from datp_core.orchestration.commands.analysis import (
    AnalyzeRequest as _AnalyzeRequest,
    AnalyzeResult as _AnalyzeResult,
    ExternalAnalyzeRequest as _ExternalAnalyzeRequest,
    ExternalAnalyzeResult as _ExternalAnalyzeResult,
    TemporalAnalyzeRequest as _TemporalAnalyzeRequest,
    TemporalAnalyzeResult as _TemporalAnalyzeResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    ArtifactPublicationResult,
    FunctionalArtifactCodec,
    publish_artifact,
)


def analyze_stage(request: _AnalyzeRequest) -> _AnalyzeResult:
    prepared = prepare_confirmatory_analysis(
        ConfirmatoryAnalysisRequest(
            contrasts=request.contrasts,
            inference_protocol=request.inference_protocol,
            analysis_seed=request.analysis_seed,
            multiplicity_plan=request.multiplicity_plan,
            mechanisms=request.mechanisms,
        )
    )
    publication = _publish(request.output_directory, request.overwrite, prepared)
    return _AnalyzeResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


def analyze_external_stage(request: _ExternalAnalyzeRequest) -> _ExternalAnalyzeResult:
    prepared = prepare_external_analysis(
        ExternalAnalysisRequest(
            execution_identity=request.execution_identity,
            contrasts=request.contrasts,
            plan=request.plan,
            analysis_seed=request.analysis_seed,
        )
    )
    publication = _publish(request.output_directory, request.overwrite, prepared)
    return _ExternalAnalyzeResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


def analyze_temporal_stage(request: _TemporalAnalyzeRequest) -> _TemporalAnalyzeResult:
    prepared = prepare_temporal_analysis(
        TemporalAnalysisRequest(
            static_reference_identity=request.static_reference_identity,
            frozen_identity=request.frozen_identity,
            recalibrated_identity=request.recalibrated_identity,
            static_reference_provenance=request.static_reference_provenance,
            frozen_provenance=request.frozen_provenance,
            recalibrated_provenance=request.recalibrated_provenance,
            records=request.records,
        )
    )
    publication = _publish(request.output_directory, request.overwrite, prepared)
    return _TemporalAnalyzeResult(
        publication_status=publication.status,
        document=publication.value,
        complete_digest=publication.complete_digest,
    )


def _publish[DocumentT](
    output_directory: Path,
    overwrite: bool,
    prepared: AnalysisPublication[DocumentT],
) -> ArtifactPublicationResult[DocumentT]:
    return publish_artifact(
        ArtifactPublication(
            target=output_directory,
            request=prepared,
            codec=FunctionalArtifactCodec(
                writer=write_analysis_publication,
                validator=analysis_publication_is_reusable,
                loader=load_reused_analysis_publication,
                rebaser=rebase_analysis_publication,
            ),
            overwrite=overwrite,
            complete_marker=AnalysisAssetName.COMPLETE,
        )
    )
