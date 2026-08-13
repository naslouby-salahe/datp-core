from enum import StrEnum

import numpy as np
import polars as pl

from datp_core.analysis.metrics.models import ClientMetricResult
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import PopulationId, ScoreFrameColumn
from datp_core.core.numeric import Ratio, RowCount
from datp_core.data.nbaiot.schema import NBaIoTAttackFamily
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.detector.scoring.contracts import FederatedScoreArtifactManifest
from datp_core.detector.scoring.frames import validate_persisted_score_frame


class FamilyRecallApplicability(StrEnum):
    APPLICABLE = "applicable"
    OUT_OF_SCOPE = "out_of_scope"


class FamilyRecallRecord(StrictModel):
    client: ClientIdentity
    family: NBaIoTAttackFamily
    support_count: RowCount
    true_positive_count: RowCount
    false_negative_count: RowCount
    true_positive_rate: Ratio
    false_negative_rate: Ratio


class FamilyRecallSummary(StrictModel):
    family: NBaIoTAttackFamily
    supported_client_count: RowCount
    macro_family_true_positive_rate: Ratio


class WorstFamilyClientRecall(StrictModel):
    client: ClientIdentity
    family: NBaIoTAttackFamily
    true_positive_rate: Ratio


class FamilyRecallDiagnostics(StrictModel):
    applicability: FamilyRecallApplicability
    records: tuple[FamilyRecallRecord, ...]
    summaries: tuple[FamilyRecallSummary, ...]
    worst_family_client: WorstFamilyClientRecall | None


def evaluate_nbaiot_family_recall(
    score_manifest: FederatedScoreArtifactManifest,
    clients: tuple[ClientMetricResult, ...],
) -> FamilyRecallDiagnostics:
    if score_manifest.coordinate.population is not PopulationId.NBAIOT_NATURAL_DEVICES:
        return FamilyRecallDiagnostics(
            applicability=FamilyRecallApplicability.OUT_OF_SCOPE,
            records=(),
            summaries=(),
            worst_family_client=None,
        )

    clients_by_id = {item.client: item for item in clients}
    if len(clients_by_id) != len(clients):
        raise ScientificContractError(ErrorMessage("family recall diagnostics require unique evaluation clients"))
    records: list[FamilyRecallRecord] = []
    for score_record in sorted(score_manifest.evaluation_records, key=lambda item: item.scored_client):
        client = clients_by_id.get(score_record.scored_client)
        if client is None:
            raise ScientificContractError(
                ErrorMessage("family recall diagnostics require every score client to be evaluated")
            )
        frame = validate_persisted_score_frame(score_record.path, score_record.row_count, score_record.partition_role)
        labels = frame.get_column(ScoreFrameColumn.OUTCOME_LABEL.value)
        families = frame.get_column(ScoreFrameColumn.ATTACK_FAMILY.value)
        scores = frame.get_column(ScoreFrameColumn.RECONSTRUCTION_ERROR.value)
        _validate_attack_family_provenance(labels, families)
        for family in NBaIoTAttackFamily:
            mask = (labels == PopulationOutcomeLabel.ATTACK.value) & (families == family.value)
            support = int(mask.sum())
            if not support:
                continue
            true_positive = int((scores.filter(mask) > client.threshold.value).sum())
            false_negative = support - true_positive
            rate = true_positive / support
            records.append(
                FamilyRecallRecord(
                    client=client.client,
                    family=family,
                    support_count=RowCount(support),
                    true_positive_count=RowCount(true_positive),
                    false_negative_count=RowCount(false_negative),
                    true_positive_rate=Ratio(rate),
                    false_negative_rate=Ratio(1.0 - rate),
                )
            )

    summaries = tuple(
        FamilyRecallSummary(
            family=family,
            supported_client_count=RowCount(len(family_records)),
            macro_family_true_positive_rate=Ratio(
                float(np.mean(tuple(item.true_positive_rate.value for item in family_records)))
            ),
        )
        for family in NBaIoTAttackFamily
        if (family_records := tuple(item for item in records if item.family is family))
    )
    if not records:
        raise ScientificContractError(ErrorMessage("N-BaIoT evaluation requires held-out family support"))
    worst = min(
        records,
        key=lambda item: (item.true_positive_rate.value, item.client.client_id.value, item.family.value),
    )
    return FamilyRecallDiagnostics(
        applicability=FamilyRecallApplicability.APPLICABLE,
        records=tuple(records),
        summaries=summaries,
        worst_family_client=WorstFamilyClientRecall(
            client=worst.client,
            family=worst.family,
            true_positive_rate=worst.true_positive_rate,
        ),
    )


def _validate_attack_family_provenance(labels: pl.Series, families: pl.Series) -> None:
    attack_families = families.filter(labels == PopulationOutcomeLabel.ATTACK.value)
    if attack_families.null_count():
        raise ScientificContractError(ErrorMessage("N-BaIoT attack score rows require attack-family provenance"))
    unknown = set(str(item) for item in attack_families.unique()) - {family.value for family in NBaIoTAttackFamily}
    if unknown:
        raise ScientificContractError(ErrorMessage("N-BaIoT attack score rows have an unknown attack family"))
