# Skill: datp-scope-guard

## Trigger

Any change to protocol, experiments, thresholds, results, claims, or repository governance.

## Required context

The touched diff, and — only when scientific meaning is in question —
`docs/Journal_Extension_Master_Roadmap.md` (§2 locked identity, §3 locked claim).

## Checks

- Fixed encoder and FedAvg baseline (E=1, full participation) are preserved; **threshold-calibration
  scope is the sole causal-ladder variable**.
- Calibration is benign-only; attack/test-split data never fit or tune a threshold.
- AUROC stays a model-quality control; the primary operating-point concern is per-client FPR
  dispersion, never global F1/AUROC/accuracy.
- Threshold meanings are locked: B1 = client-averaged shared τ; B2 = per-client p95; B3 = family-mean
  (Regime A, needs taxonomy); B4 = k-means cluster-mean on `[µ_e, σ_e, skew_e, p95(e)]` with canonical
  `K = 3` (other K is exploratory only). No renaming to old labels (`B5`, `B3-LGS`, "Ditto" unless the
  real algorithm is implemented).
- Stress-test comparators (FedProx, model personalization, Laridi-style) stay outside the causal ladder
  and are never presented as sharing its experimental control.
- No drift into poisoning, Dynamic DATP, privacy guarantees, deployment profiling, backdoor, evasion,
  full drift detection, or generic FL-IDS expansion; any mention is explicitly future-work/spin-off wording.

## Fail conditions

Scope expands, a locked threshold identifier is renamed or reinterpreted, a stress test is promoted to
confirmatory, or attack data enters calibration.

## Output

Stop and report the exact scope or semantics violation; never narrow the locked identity to fit an edit.
