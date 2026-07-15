from datp_core.application.ports.data import MaterializeProcessedSplitsRequest, ProcessedSplitMaterializer
from datp_core.domain.data.preprocessing import FittedPreprocessorResult, ProcessedSplitResult
from datp_core.domain.data.splitting import SplitManifestResult


def materialize_splits(
    *,
    materializer: ProcessedSplitMaterializer,
    split_manifest: SplitManifestResult,
    fitted_preprocessor: FittedPreprocessorResult,
) -> ProcessedSplitResult:
    return materializer.materialize(
        MaterializeProcessedSplitsRequest(split_manifest=split_manifest, fitted_preprocessor=fitted_preprocessor)
    )
