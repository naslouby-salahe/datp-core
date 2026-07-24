"""Scientific fingerprint projection assembly and the scientific fingerprint builder.

Absolute filesystem paths are deliberately excluded from identity (artifact_identity rule);
datasets are projected via their schema id and fingerprint field lists rather than their
resolved (absolute-path-bearing) record.
"""

from __future__ import annotations


def build_scientific_projection(
    *,
    resolved_datasets: dict,
    catalogue,  # ResolvedExperimentCatalogue
    protocols,  # ResolvedProtocols
    projection_module,  # unstructure_projection
) -> dict[str, object]:
    from datp_core.config.resolution.experiments import experiment_scientific_projection as _sci_proj

    return {
        "datasets": {
            str(k): {
                "schema_id": v.schema_id,
                "source_layout_contract": projection_module(v.source_layout_contract),
                "field_schema": projection_module(v.field_schema),
                "source_contract": projection_module(v.source_contract),
                "client_identity_contract": projection_module(v.client_identity_contract),
                "setups": projection_module(v.setups),
                "materializations": projection_module(v.materializations),
                "capabilities": list(v.capabilities),
                "fingerprint_source_fields": list(v.fingerprint_source_fields),
                "fingerprint_schema_fields": list(v.fingerprint_schema_fields),
                "fingerprint_materialization_fields": list(v.fingerprint_materialization_fields),
                "fingerprint_client_assignment_fields": list(v.fingerprint_client_assignment_fields),
            }
            for k, v in sorted(resolved_datasets.items(), key=lambda x: str(x[0]))
        },
        "populations": {
            str(k): projection_module(v)
            for k, v in sorted(catalogue.populations.items(), key=lambda x: str(x[0]))
        },
        "experiments": {
            str(k): _sci_proj(v)
            for k, v in sorted(catalogue.experiments.items(), key=lambda x: str(x[0]))
        },
        "threshold_policies": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.threshold_policies.items(), key=lambda x: str(x[0]))
        },
        "seed_cohorts": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.seed_cohorts.items(), key=lambda x: str(x[0]))
        },
        "training_profiles": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.training_profiles.items(), key=lambda x: str(x[0]))
        },
        "checkpoint_profiles": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.checkpoint_profiles.items(), key=lambda x: str(x[0]))
        },
        "model_architectures": {
            k: projection_module(v) for k, v in sorted(protocols.model_architectures.items())
        },
        "optimizers": {
            k: projection_module(v) for k, v in sorted(protocols.optimizers.items())
        },
        "batching": {
            k: projection_module(v) for k, v in sorted(protocols.batching_profiles.items())
        },
        "eligibility_policies": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.eligibility_policies.items(), key=lambda x: str(x[0]))
        },
        "normalization_strategies": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.normalization_strategies.items(), key=lambda x: str(x[0]))
        },
        "quantile_estimators": {
            k: projection_module(v) for k, v in sorted(protocols.quantile_estimators.items())
        },
        "metric_bundles": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.metric_bundles.items(), key=lambda x: str(x[0]))
        },
        "statistical_profiles": {
            str(k): projection_module(v)
            for k, v in sorted(protocols.statistical_profiles.items(), key=lambda x: str(x[0]))
        },
        "metric_definitions": projection_module(protocols.metric_definitions),
        "artifact_identity": projection_module(protocols.artifact_identity),
        "communication_estimation_contract": projection_module(protocols.communication_estimation_contract),
        "operational_inputs": projection_module(protocols.operational_inputs),
        "report_profiles": {k: projection_module(v) for k, v in sorted(protocols.report_profiles.items())},
        "communication_estimation": projection_module(protocols.communication_estimation),
        "protocol_determinism": projection_module(protocols.protocol_determinism),
        "normalization_fit_scopes": dict(sorted(protocols.normalization_fit_scopes.items())),
        "normalization_leakage_rule": protocols.normalization_leakage_rule,
        "threshold_policy_defaults": projection_module(protocols.threshold_policy_defaults),
        "nested_replicate_policy": projection_module(protocols.nested_replicate_policy),
        "result_types": {k: projection_module(v) for k, v in sorted(protocols.result_types.items())},
        "evaluation_result_contract": projection_module(protocols.evaluation_result_contract),
        "report_defaults": projection_module(protocols.report_defaults),
        "capabilities": sorted(catalogue.capabilities),
        "suppression_behaviors": sorted(catalogue.suppression_behaviors),
        "population_readiness_rule": dict(sorted(catalogue.population_readiness_rule.items())),
        "eligibility_gates": {
            k: projection_module(v) for k, v in sorted(catalogue.eligibility_gates.items())
        },
        "analysis_conventions": dict(sorted(catalogue.analysis_conventions.items())),
    }
