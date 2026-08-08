# Pre-Implementation State — Prompt 4/8 Federated Threshold Estimation

## Three-experiment readiness matrix (before implementation)

| Experiment | Declaration | Threshold Methods | Core Implementation | Workflow Runner | Report | CLI | Tests |
|---|---|---|---|---|---|---|---|
| FEDERATED_BENIGN_STATISTICS_COMPARISON | YES | YES (5 methods) | YES (B-FedStatsBenign) | NO | NO | NO | NO |
| FEDERATED_QUANTILE_ESTIMATION | YES | YES (5 methods) | YES (B-FedStatsBenign) | NO | NO | NO | NO |
| FIXED_COEFFICIENT_STATISTICS_SENSITIVITY | YES | YES (3 methods) | YES (B-FedStatsBenign) | NO | NO | NO | NO |

## Core implementation audit (pre-existing)

### B-FedStatsBenign math (federated_statistics.py)
- Pooled variance decomposition: CORRECT — includes within-client, between-client mean-shift, and full pooled variance
- Between-ratio: CORRECT — `between / (within + between)`, undefined when denominator is zero
- Gaussian-matched exceedance threshold: CORRECT — uses global mean and full pooled variance
- Fixed coefficient curve: CORRECT — uses locked grid {2.0, 2.5, 3.0}
- Benign-only inputs: VERIFIED — no attack-labelled data enters construction
- Communication bytes estimate: CORRECT — scalar count * float64 size, explicitly estimated

### Communication diagnostics (communication.py)
- Naming: CORRECT — `SERIALIZED_MESSAGE_SIZE_ESTIMATE` basis, docstring says "estimates, not network measurements"
- Typed payloads: CORRECT — `SerializedPayloadEvidence` wraps actual bytes, not object-size estimates

### Threshold estimation diagnostics (threshold_estimation.py)
- Properly typed: CORRECT — `ThresholdEstimationDiagnostic` with provenance, metrics, bounds
- Contravariant contracts: CORRECT — validates signed attainment, non-negative absolute errors

## What was missing

1. Workflow module (federated_threshold_estimation.py) — NEW
2. Registration in _REGISTERED_WORKFLOWS — 3 new entries
3. Dispatch functions — _dispatch_federated_benign_statistics_comparison, _dispatch_federated_quantile_estimation, _dispatch_fixed_coefficient_statistics_sensitivity
4. Report handlers — report_federated_benign_statistics_comparison, report_federated_quantile_estimation, report_fixed_coefficient_statistics_sensitivity
5. Analysis marker checks — 3 new marker functions
6. WorkflowHandlers entries — 3 new entries
7. Registry tests — extended with new experiment expectations
