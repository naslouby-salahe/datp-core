from datp_core.application.ports.data import FitPreprocessorRequest, PreprocessorFitter
from datp_core.domain.data.preprocessing import FittedPreprocessorResult, PreprocessingSpec
from datp_core.domain.data.splitting import SplitManifestResult


def fit_preprocessor(
    *, fitter: PreprocessorFitter, split_manifest: SplitManifestResult, preprocessing: PreprocessingSpec
) -> FittedPreprocessorResult:
    return fitter.fit(FitPreprocessorRequest(split_manifest=split_manifest, preprocessing=preprocessing))
