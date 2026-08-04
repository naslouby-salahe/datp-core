"""Stage: compose pooled scoring with shared publication infrastructure."""

from pathlib import Path

from datp_core.centralized_reference.scoring import (
    CentralizedScoreAssetName,
    CentralizedScoringRequest,
    centralized_scoring_is_reusable,
    load_reused_centralized_scoring,
    rebase_centralized_scoring,
    write_centralized_scoring,
)
from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import checksum_file
from datp_core.orchestration.commands.scoring import (
    ScoreCentralizedReferenceRequest as _ScoreCentralizedReferenceRequest,
    ScoreCentralizedReferenceResult as _ScoreCentralizedReferenceResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)


def score_centralized_reference_stage(
    request: _ScoreCentralizedReferenceRequest,
) -> _ScoreCentralizedReferenceResult:
    if request.checkpoint.coordinate != request.coordinate:
        raise ScientificContractError(
            "score stage checkpoint coordinate mismatch",
            subject=ContractSubject.COORDINATE,
        )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=FunctionalArtifactCodec(
                writer=lambda stage_request, directory: write_centralized_scoring(
                    _scoring_request(stage_request, directory),
                    directory,
                ),
                validator=lambda stage_request, directory: centralized_scoring_is_reusable(
                    _scoring_request(stage_request, directory),
                    directory,
                ),
                loader=lambda stage_request, directory: load_reused_centralized_scoring(
                    _scoring_request(stage_request, directory),
                    directory,
                ),
                rebaser=rebase_centralized_scoring,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedScoreAssetName.COMPLETE,
        )
    )
    return _ScoreCentralizedReferenceResult(
        publication_status=publication.status,
        scoring=publication.value,
        complete_digest=checksum_file(request.output_directory / CentralizedScoreAssetName.COMPLETE),
    )


def _scoring_request(
    request: _ScoreCentralizedReferenceRequest,
    directory: Path,
) -> CentralizedScoringRequest:
    return CentralizedScoringRequest(
        coordinate=request.coordinate,
        checkpoint=request.checkpoint,
        autoencoder=request.autoencoder,
        feature_names=request.feature_names,
        calibration_features=request.calibration_features,
        evaluation_features=request.evaluation_features,
        batch_size=request.batch_size,
        output_directory=directory,
        preprocessing_state_checksum=request.preprocessing_state_checksum,
    )
