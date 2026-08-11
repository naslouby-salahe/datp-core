from datp_core.analysis.metrics.cohorts import (
    ClientEligibilityRecord,
    ClientExclusionReason,
    EvaluationCohortManifest,
    EvaluationCohortMembership,
)
from datp_core.core.identifiers import (
    ClientIdentityToken,
    EvaluationCohort,
    PopulationId,
    PopulationIdentityKind,
)
from datp_core.core.numeric import RowCount, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.thresholds.calibration.construction import _cell_cohort
from datp_core.thresholds.protocols import MINIMUM_BENIGN_SUPPORT


def _client(client_id: str) -> ClientIdentity:
    return ClientIdentity(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        client_id=ClientIdentityToken(client_id),
        identity_kind=PopulationIdentityKind.PHYSICAL_DEVICES,
    )


def test_cell_cohort_moves_infeasible_clients_to_deployment_fallback() -> None:
    feasible_client = _client("feasible")
    infeasible_client = _client("infeasible")
    manifest = EvaluationCohortManifest(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        minimum_benign_calibration_support=MINIMUM_BENIGN_SUPPORT,
        records=(
            ClientEligibilityRecord(
                client=feasible_client,
                benign_calibration_count=RowCount(5000),
                benign_evaluation_count=RowCount(10),
                attack_evaluation_count=RowCount(10),
                calibration_eligible=True,
                fpr_evaluable=True,
                attack_evaluable=True,
                deployment_fallback=False,
                exclusion_reasons=(),
            ),
            ClientEligibilityRecord(
                client=infeasible_client,
                benign_calibration_count=RowCount(5000),
                benign_evaluation_count=RowCount(10),
                attack_evaluation_count=RowCount(10),
                calibration_eligible=True,
                fpr_evaluable=True,
                attack_evaluable=True,
                deployment_fallback=False,
                exclusion_reasons=(),
            ),
        ),
        memberships=(
            EvaluationCohortMembership(
                client=feasible_client,
                cohort=EvaluationCohort.FPR_EVALUABLE,
                reasons=(),
            ),
            EvaluationCohortMembership(
                client=feasible_client,
                cohort=EvaluationCohort.ATTACK_EVALUABLE,
                reasons=(),
            ),
            EvaluationCohortMembership(
                client=infeasible_client,
                cohort=EvaluationCohort.FPR_EVALUABLE,
                reasons=(),
            ),
            EvaluationCohortMembership(
                client=infeasible_client,
                cohort=EvaluationCohort.ATTACK_EVALUABLE,
                reasons=(),
            ),
        ),
    )

    cell = _cell_cohort(manifest, (feasible_client,))

    records = {record.client: record for record in cell.records}
    assert records[feasible_client].fpr_evaluable
    assert not records[infeasible_client].calibration_eligible
    assert not records[infeasible_client].fpr_evaluable
    assert records[infeasible_client].deployment_fallback
    assert records[infeasible_client].exclusion_reasons == (ClientExclusionReason.INSUFFICIENT_CALIBRATION_SIZE,)
    memberships = {(item.client, item.cohort): item for item in cell.memberships}
    assert (infeasible_client, EvaluationCohort.FPR_EVALUABLE) not in memberships
    assert memberships[(infeasible_client, EvaluationCohort.ATTACK_EVALUABLE)].reasons == ()
    assert memberships[(infeasible_client, EvaluationCohort.DEPLOYMENT_FALLBACK)].reasons == (
        ClientExclusionReason.INSUFFICIENT_CALIBRATION_SIZE,
    )
