import numpy as np

from datp_core.analysis.metrics.family_recall import (
    FamilyRecallApplicability,
    FamilyRecallRecord,
    FamilyRecallSummary,
    WorstFamilyClientRecall,
)
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.core.contracts import StrictModel
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, PopulationId
from datp_core.core.numeric import MetricValue, Seed, SeedObservationCount
from datp_core.data.nbaiot.schema import NBaIoTAttackFamily
from datp_core.data.populations.contracts import ClientIdentity


class FamilyRecallPolicyEvidence(StrictModel):
    threshold_method: FederatedThresholdMethod
    records: tuple[FamilyRecallRecord, ...]
    summaries: tuple[FamilyRecallSummary, ...]
    worst_family_client: WorstFamilyClientRecall


class FamilyRecallDifference(StrictModel):
    client: ClientIdentity
    family: NBaIoTAttackFamily
    compared_method: FederatedThresholdMethod
    compared_minus_shared_true_positive_rate: MetricValue


class FamilyRecallPolicyComparison(StrictModel):
    seed: Seed
    policies: tuple[FamilyRecallPolicyEvidence, ...]
    shared_differences: tuple[FamilyRecallDifference, ...]


class FamilyRecallMacroCampaignSummary(StrictModel):
    threshold_method: FederatedThresholdMethod
    family: NBaIoTAttackFamily
    seed_values: tuple[MetricValue, ...]
    arithmetic_mean: MetricValue
    median: MetricValue
    minimum: MetricValue
    maximum: MetricValue


class FamilyRecallPolicyCampaignSummary(StrictModel):
    comparisons: tuple[FamilyRecallPolicyComparison, ...]
    observed_seed_count: SeedObservationCount
    macro_summaries: tuple[FamilyRecallMacroCampaignSummary, ...]


def compare_family_recall_policies(
    documents: tuple[FederatedEvaluationDocument, ...],
) -> FamilyRecallPolicyComparison:
    if len(documents) != 4:
        raise ScientificContractError(ErrorMessage("family recall comparison requires exactly four policy documents"))
    expected_methods = {
        FederatedThresholdMethod.SHARED_THRESHOLD,
        FederatedThresholdMethod.LOCAL_THRESHOLD,
        FederatedThresholdMethod.FAMILY_THRESHOLD,
        FederatedThresholdMethod.CLUSTER_THRESHOLD,
    }
    methods = {document.threshold_method for document in documents}
    if methods != expected_methods:
        raise ScientificContractError(
            ErrorMessage("family recall comparison requires shared/local/family/cluster policies")
        )
    first = documents[0]
    if any(
        document.score_coordinate.population is not PopulationId.NBAIOT_NATURAL_DEVICES
        or document.score_coordinate.training_seed != first.score_coordinate.training_seed
        for document in documents
    ):
        raise ScientificContractError(ErrorMessage("family recall comparison requires one N-BaIoT seed"))
    policies = tuple(
        _policy_evidence(document) for document in sorted(documents, key=lambda item: item.threshold_method)
    )
    shared = next(item for item in policies if item.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD)
    shared_by_pair = {(item.client, item.family): item for item in shared.records}
    differences: list[FamilyRecallDifference] = []
    for policy in policies:
        if policy.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD:
            continue
        for record in policy.records:
            reference = shared_by_pair.get((record.client, record.family))
            if reference is None:
                raise ScientificContractError(
                    ErrorMessage("family recall policy support must be fixed across policies")
                )
            differences.append(
                FamilyRecallDifference(
                    client=record.client,
                    family=record.family,
                    compared_method=policy.threshold_method,
                    compared_minus_shared_true_positive_rate=MetricValue(
                        record.true_positive_rate.value - reference.true_positive_rate.value
                    ),
                )
            )
    return FamilyRecallPolicyComparison(
        seed=first.score_coordinate.training_seed,
        policies=policies,
        shared_differences=tuple(differences),
    )


def summarize_family_recall_campaign(
    comparisons: tuple[FamilyRecallPolicyComparison, ...], *, required_seed_count: SeedObservationCount
) -> FamilyRecallPolicyCampaignSummary:
    if len(comparisons) != required_seed_count.value:
        raise ScientificContractError(ErrorMessage("family recall campaign must contain every declared seed"))
    seeds = tuple(item.seed for item in comparisons)
    if len(seeds) != len(frozenset(seeds)):
        raise ScientificContractError(ErrorMessage("family recall campaign cannot repeat a seed"))
    summaries: list[FamilyRecallMacroCampaignSummary] = []
    for method in FederatedThresholdMethod:
        matching_policies = tuple(
            next((policy for policy in comparison.policies if policy.threshold_method is method), None)
            for comparison in comparisons
        )
        if any(policy is None for policy in matching_policies):
            continue
        for family in NBaIoTAttackFamily:
            values = tuple(
                summary.macro_family_true_positive_rate.value
                for policy in matching_policies
                if policy is not None
                for summary in policy.summaries
                if summary.family is family
            )
            if len(values) != len(comparisons):
                raise ScientificContractError(
                    ErrorMessage("family macro recall must be available for every campaign seed")
                )
            array = np.asarray(values, dtype=np.float64)
            summaries.append(
                FamilyRecallMacroCampaignSummary(
                    threshold_method=method,
                    family=family,
                    seed_values=tuple(MetricValue(value) for value in values),
                    arithmetic_mean=MetricValue(float(np.mean(array))),
                    median=MetricValue(float(np.median(array))),
                    minimum=MetricValue(float(np.min(array))),
                    maximum=MetricValue(float(np.max(array))),
                )
            )
    return FamilyRecallPolicyCampaignSummary(
        comparisons=comparisons,
        observed_seed_count=SeedObservationCount(len(comparisons)),
        macro_summaries=tuple(summaries),
    )


def _policy_evidence(document: FederatedEvaluationDocument) -> FamilyRecallPolicyEvidence:
    diagnostics = document.diagnostics.family_recall
    if diagnostics.applicability is not FamilyRecallApplicability.APPLICABLE:
        raise ScientificContractError(ErrorMessage("N-BaIoT family recall diagnostics must be applicable"))
    if diagnostics.worst_family_client is None:
        raise ScientificContractError(
            ErrorMessage("applicable family recall diagnostics require a worst supported pair")
        )
    return FamilyRecallPolicyEvidence(
        threshold_method=document.threshold_method,
        records=diagnostics.records,
        summaries=diagnostics.summaries,
        worst_family_client=diagnostics.worst_family_client,
    )
