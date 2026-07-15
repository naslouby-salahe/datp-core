from dataclasses import fields, is_dataclass
from inspect import getmembers, isfunction, signature
from typing import Protocol, get_type_hints

from datp_core.application.ports import data, learning, scoring, thresholding

PORTS = (
    data.DatasetSourceInspector,
    data.ClientPartitioner,
    data.SplitManifestBuilder,
    data.PreprocessorFitter,
    data.ProcessedSplitMaterializer,
    learning.FederatedTrainer,
    learning.CentralizedModelTrainer,
    scoring.ScoreGenerator,
    thresholding.ThresholdConstructor,
    thresholding.ThresholdStrategy,
    thresholding.ClusteringStrategy,
    thresholding.QuantileEstimator,
)

THRESHOLD_REQUESTS = (
    thresholding.ConstructThresholdsRequest,
    thresholding.AssignThresholdRequest,
    thresholding.B4ClusteringRequest,
    thresholding.QuantileEstimateRequest,
)


def test_every_port_method_has_one_named_request_and_result() -> None:
    for port in PORTS:
        assert issubclass(port, Protocol)
        methods = tuple(member for _, member in getmembers(port, isfunction) if not member.__name__.startswith("_"))
        assert methods
        for method in methods:
            method_signature = signature(method)
            assert tuple(method_signature.parameters) == ("self", "request")
            annotations = get_type_hints(method)
            assert set(annotations) == {"request", "return"}
            assert is_dataclass(annotations["request"])
            assert is_dataclass(annotations["return"])


def test_threshold_requests_cannot_carry_test_or_attack_scores() -> None:
    forbidden_fragments = ("test", "attack")

    for request_type in THRESHOLD_REQUESTS:
        assert all(
            forbidden_fragment not in field.name.casefold()
            for field in fields(request_type)
            for forbidden_fragment in forbidden_fragments
        )


def test_federated_and_centralized_training_ports_are_distinct_protocols() -> None:
    assert learning.FederatedTrainer is not learning.CentralizedModelTrainer
    assert learning.TrainFederatedModelRequest is not learning.TrainCentralizedModelRequest
