# Claim Hierarchy

> Ticket: P0-T02. Source: [Journal_Extension_Master_Roadmap.md](../Journal_Extension_Master_Roadmap.md)
> §5, §9, §12. Nine ordered tiers. Exactly one claim carries `role=confirmatory`
> (Tier 1). Nothing below Tier 1 may be promoted to confirmatory. Fallback
> wording referenced here (`§12.x`) is defined in the roadmap and must not be
> reworded ad hoc after results are observed.

## Tier 1 — Confirmatory (role=confirmatory, singular)

| Field | Value |
|---|---|
| Claim | Under Regime A natural device split, per-client p95 calibration (B2) reduces CV(FPR) relative to the client-averaged shared threshold (B1) by a magnitude whose 95% BCa bootstrap CI on the per-seed delta excludes zero (positive direction). |
| Evidence | 10 paired seeds; Δ_s = CV(FPR)[B1,s] − CV(FPR)[B2,s]; BCa CI on Δ; sign-consistency summary |
| Regime | A (N-BaIoT, K = 9) |
| Metric | CV(FPR) (primary) |
| Minimum pass | BCa CI excludes zero, positive direction |
| Fallback | §12.1 (strong/weak/mixed/null/opposite wording); never suppressed |
| Reviewer risk | L04 tautology ("B2 equalizes FPR by construction") |
| Placement | Main paper, headline result |

## Tier 2 — Secondary Supportive (role=supportive)

Mean-artifact rule-out (pooled/weighted shared variants vs B2, Regime A);
absolute-dispersion confirmation (IQR, max−min alongside CV); heterogeneity
gradient (Dirichlet α sweep, Regime C); q-sensitivity robustness (Regime A).
See roadmap §5.2 for the four claim rows; E-S1, E-S2, E-S3 (§9.2).

## Tier 3 — External Validation (role=external_validation)

Threshold-scope effect generalizes to Edge-IIoTset (Regime D): B1–B4 +
q-sensitivity + `B-FedStatsBenign`; CV(FPR) + BCa CI; pass iff direction
consistent with Regime A, else reported as boundary. E-X1 (§9.2). Fallback
§12.9.

## Tier 4 — Stress-Test (role=stress_test, outside causal ladder)

Three claims: FedProx does not absorb the gain (E-T1, fallback §12.8);
model-side personalization does not absorb the gain, evaluated against the
pre-specified absorption bands (E-T2, §9.3, fallback §12.7); `B-FedStatsBenign`
does not dominate DATP (E-T3, fallback §12.9 pattern). None of these three
share the Tier-1 experimental control (SB-25).

## Tier 5 — Mechanism (role=mechanism)

Cluster/family scope as a middle ground (E-M1, fallback §12.3); cluster-feature
ablation (E-M2); per-client CDF overlays + Ennio deep dive (E-M3, fallback
§12.4 pattern via Tier 6); heterogeneity-severity vs gain regression (E-M4,
fallback §12.6 pattern); threshold-shift vs ΔFPR/ΔTPR surface (E-M5). See
roadmap §5.5.

## Tier 6 — Boundary-Condition (role=boundary)

Near-homogeneous CICIoT2023 file-level null (Regime B-a, fallback §12.10);
B2 low-separability degradation (P10 Macro-F1, worst-client BA); small-window
threshold degradation vs shrinkage stabilization (E-V1/E-V2, fallback §12.4,
§12.5); temporal recalibration outcome (E-B1, one of three pre-specified
outcomes, §11.1).

## Tier 7 — Exploratory (role=exploratory)

B4 K = 3 recovery percentage at N = 9 (fallback §12.2); B4 K-sweep granularity
sensitivity (not a main claim, SB-32); federated quantile-estimation error vs
threshold reliability (E-Q1, fallback §12.6).

## Tier 8 — Future Work (role=future_work, never executed)

Dynamic DATP; Conformal DATP beyond B2-conf; formal DP/SecAgg privacy;
fleet-scale (K > 100) validation; streaming drift mitigation; standalone
Model-vs-Threshold-Personalization 2×2 spin-off; exhaustive personalized-FL
and aggregation benchmarking. Named in Future Work only; never a result.

## Tier 9 — Forbidden (role=forbidden)

DATP "solves" non-IID FL; improved global Macro-F1; privacy preservation;
concept-drift handling beyond one-shot recalibration; universal dominance over
Laridi-style thresholding; fleet-scale validation; "first"/"novel" language
without independent verification; any dataset property (device IDs,
timestamps, family counts) stated as verified fact without an artifact check;
B4 fingerprints framed as a privacy mechanism.

## Consumers

- `ClaimRole` enum (P1-T02): `confirmatory | supportive | external_validation
  | stress_test | mechanism | boundary | exploratory | future_work |
  forbidden`.
- `claim_gates` metadata (P7-T04) and the claim-evidence map (P7-T05).
