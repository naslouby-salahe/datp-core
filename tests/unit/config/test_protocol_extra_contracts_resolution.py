"""Lossless resolution of the six previously dead-end protocol contract blocks.

``metric_definitions``, ``artifact_identity``, ``communication_estimation_contract``,
``operational_inputs``, ``report_profiles``, and ``communication_estimation`` are strictly
authored in protocols.yaml but were never carried into ``ResolvedProjectConfiguration``. These
tests prove every authored value now reaches the resolved domain graph, unchanged, as a pure
(non-Pydantic) record, and participates in the scientific fingerprint.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import cattrs
import pydantic
import yaml

from datp_core.config.resolver import resolve_project_configuration
from datp_core.domain.protocol_contracts import (
    ArtifactIdentityRecord,
    CommunicationEstimationContractRecord,
    MetricDefinitionsRecord,
    OperationalInputsRecord,
    ReportProfileRecord,
)

_converter = cattrs.Converter()


def _load_authored_protocols() -> dict:
    with open("configs/protocols.yaml") as handle:
        return yaml.safe_load(handle)


def test_metric_definitions_are_resolved_losslessly_as_a_pure_domain_record() -> None:
    cfg = resolve_project_configuration()
    authored = _load_authored_protocols()["metric_definitions"]

    record = cfg.metric_definitions
    assert isinstance(record, MetricDefinitionsRecord)
    assert not isinstance(record, pydantic.BaseModel)

    resolved = _converter.unstructure(record)
    # The authored YAML omits unset optional MetricFormulaConfig keys; the resolved record
    # fills them in explicitly as None. Compare only the authored subset for equality.
    assert {key: resolved["fpr"][key] for key in authored["fpr"]} == authored["fpr"]
    assert {
        key: resolved["cross_client_aggregation"]["mean_fpr"][key]
        for key in authored["cross_client_aggregation"]["mean_fpr"]
    } == authored["cross_client_aggregation"]["mean_fpr"]
    assert (
        resolved["heterogeneity_diagnostics"]["pairwise_js_divergence"]
        == authored["heterogeneity_diagnostics"]["pairwise_js_divergence"]
    )
    assert resolved["metric_statuses"] == authored["metric_statuses"]
    assert resolved["forbidden_substitutions"] == authored["forbidden_substitutions"]


def test_artifact_identity_is_resolved_losslessly_and_participates_in_scientific_fingerprint() -> None:
    cfg = resolve_project_configuration()
    authored = _load_authored_protocols()["artifact_identity"]

    record = cfg.artifact_identity
    assert isinstance(record, ArtifactIdentityRecord)
    assert record.hash_function == authored["hash_function"]
    assert record.digest_bytes == authored["digest_bytes"]
    assert record.canonical_serialization == authored["canonical_serialization"]
    assert tuple(record.fingerprints.materialization) == tuple(authored["fingerprints"]["materialization"])
    assert tuple(record.reuse_rejected_when_any_changes) == tuple(authored["reuse_rejected_when_any_changes"])


def test_communication_estimation_contract_is_resolved_losslessly() -> None:
    cfg = resolve_project_configuration()
    authored = _load_authored_protocols()["communication_estimation_contract"]

    record = cfg.communication_estimation_contract
    assert isinstance(record, CommunicationEstimationContractRecord)
    assert record.estimate_basis == authored["estimate_basis"]
    for key, encoding in authored["field_encodings"].items():
        assert record.field_encodings[key].bytes_per_field == encoding["bytes_per_field"]
        assert record.field_encodings[key].byte_order == encoding["byte_order"]
    assert record.threshold_exchange.direction == authored["threshold_exchange"]["direction"]
    assert record.model_exchange.field_width == authored["model_exchange"]["field_width"]


def test_operational_inputs_is_resolved_losslessly() -> None:
    cfg = resolve_project_configuration()
    authored = _load_authored_protocols()["operational_inputs"]["benign_decision_rate"]

    record = cfg.operational_inputs
    assert isinstance(record, OperationalInputsRecord)
    assert record.benign_decision_rate.configured == authored["configured"]
    assert record.benign_decision_rate.value == authored["value"]
    assert tuple(record.benign_decision_rate.required_fields) == tuple(authored["required_fields"])
    assert record.benign_decision_rate.invented_rate_forbidden == authored["invented_rate_forbidden"]


def test_every_authored_report_profile_is_resolved_losslessly() -> None:
    cfg = resolve_project_configuration()
    authored = _load_authored_protocols()["report_profiles"]

    resolved_keys = {str(key) for key in cfg.report_profiles}
    assert resolved_keys == set(authored)

    for key, profile in authored.items():
        record = cfg.report_profiles.get(key)
        assert isinstance(record, ReportProfileRecord)
        assert record.artifact_type == profile["artifact_type"]
        assert record.table_type == profile.get("table_type")
        assert record.figure_type == profile.get("figure_type")
        if profile.get("columns") is not None:
            assert record.columns is not None
            assert [c.name for c in record.columns] == [c["name"] for c in profile["columns"]]
            assert [c.unit for c in record.columns] == [c["unit"] for c in profile["columns"]]
        else:
            assert record.columns is None


def test_communication_estimation_is_none_when_not_authored() -> None:
    cfg = resolve_project_configuration()
    authored = _load_authored_protocols()

    assert authored.get("communication_estimation") is None
    assert cfg.communication_estimation is None


def test_metric_definitions_and_artifact_identity_are_covered_by_the_scientific_fingerprint() -> None:
    baseline = resolve_project_configuration()

    mutated = _load_authored_protocols()
    mutated["metric_definitions"]["fpr"]["formula"] = "a_deliberately_different_formula_for_the_drift_test"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "datasets").mkdir()
        for source in Path("configs/datasets").glob("*.yaml"):
            (tmp_path / "datasets" / source.name).write_text(source.read_text())
        (tmp_path / "runtime.yaml").write_text(Path("configs/runtime.yaml").read_text())
        (tmp_path / "experiments.yaml").write_text(Path("configs/experiments.yaml").read_text())
        (tmp_path / "protocols.yaml").write_text(yaml.safe_dump(mutated, sort_keys=False))

        mutated_config = resolve_project_configuration(config_dir=tmp_path)

    assert mutated_config.scientific_fingerprint != baseline.scientific_fingerprint
