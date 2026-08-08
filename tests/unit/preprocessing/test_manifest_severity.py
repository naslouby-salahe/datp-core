from pathlib import Path

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    DatasetId,
    FeatureName,
    FeatureNameSequence,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.core.numeric import AbsoluteTolerance, DirichletConcentration, Seed
from datp_core.data.populations.contracts import ControlledPartitionCondition, ControlledPartitionKind
from datp_core.data.preprocessing.artifact_validation import build_preprocessing_manifest
from datp_core.data.preprocessing.artifacts import PreprocessingFitScope, RelativeAssetPath, TrustedEstimatorClassName
from datp_core.data.preprocessing.models import PreprocessingProtocol, PreprocessingPublishContext

_PROTOCOL = PreprocessingProtocol(
    identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
    fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
    input_feature_names=FeatureNameSequence((FeatureName("f0"), FeatureName("f1"))),
    serialization_format=SerializationFormat.SKOPS,
    estimator_class_name=TrustedEstimatorClassName.STANDARD_SCALER,
    numerical_equivalence_absolute_tolerance=AbsoluteTolerance(1e-12),
)
_ASSET_PATHS = (RelativeAssetPath("estimator.skops"),)


def _context(condition: ControlledPartitionCondition | None) -> PreprocessingPublishContext:
    return PreprocessingPublishContext(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_DIRICHLET_CLIENTS,
        partition_seed=Seed(0),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        protocol=_PROTOCOL,
        canonical_schema_checksum=Checksum("a" * 64),
        data_root=Path("data"),
        dirichlet_condition=condition,
    )


def test_manifest_stores_the_dirichlet_severity_condition() -> None:
    condition = ControlledPartitionCondition(
        kind=ControlledPartitionKind.DIRICHLET, concentration=DirichletConcentration(0.1)
    )
    manifest = build_preprocessing_manifest(
        _context(condition), branch=ProcessedDataBranch.FEDERATED, asset_paths=_ASSET_PATHS
    )
    assert manifest.controlled_partition_kind is ControlledPartitionKind.DIRICHLET
    assert manifest.dirichlet_concentration == DirichletConcentration(0.1)


def test_manifests_for_different_dirichlet_severities_are_not_equal() -> None:
    low_alpha = build_preprocessing_manifest(
        _context(
            ControlledPartitionCondition(
                kind=ControlledPartitionKind.DIRICHLET, concentration=DirichletConcentration(0.1)
            )
        ),
        branch=ProcessedDataBranch.FEDERATED,
        asset_paths=_ASSET_PATHS,
    )
    high_alpha = build_preprocessing_manifest(
        _context(
            ControlledPartitionCondition(
                kind=ControlledPartitionKind.DIRICHLET, concentration=DirichletConcentration(0.3)
            )
        ),
        branch=ProcessedDataBranch.FEDERATED,
        asset_paths=_ASSET_PATHS,
    )
    assert low_alpha != high_alpha


def test_iid_and_dirichlet_manifests_are_not_equal() -> None:
    iid = build_preprocessing_manifest(
        _context(ControlledPartitionCondition(kind=ControlledPartitionKind.IID, concentration=None)),
        branch=ProcessedDataBranch.FEDERATED,
        asset_paths=_ASSET_PATHS,
    )
    dirichlet = build_preprocessing_manifest(
        _context(
            ControlledPartitionCondition(
                kind=ControlledPartitionKind.DIRICHLET, concentration=DirichletConcentration(0.1)
            )
        ),
        branch=ProcessedDataBranch.FEDERATED,
        asset_paths=_ASSET_PATHS,
    )
    assert iid != dirichlet
