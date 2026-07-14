# Statistics Hook

## Trigger
After result, metric, statistics, seed, or interpretation changes.

## Purpose
Protect statistical validity and the sole confirmatory endpoint.

## Blocking status
Blocks completion.

## Required checks
- The sole confirmatory endpoint is Regime A, B1 vs B2, CV(FPR), ten-seed paired evidence, 95% BCa bootstrap CI on the per-seed delta, positive direction only; no other regime, policy pair, or metric may be labeled or presented as confirmatory, however it is named.
- CV(FPR) is the primary endpoint; AUROC is a control metric only, never the thresholding verdict.
- The confirmatory claim's 95% BCa bootstrap CI on the paired per-seed delta is checked in the correct, positive direction; a CI that does not exclude zero in that direction is never reported as confirmatory.
- Ten paired seeds back the confirmatory endpoint; seed pairing, sign consistency, q-sensitivity, Wilcoxon, and Cliff's delta are checked where relevant.
- A degenerate result (zero-mean CV, degenerate bootstrap interval) becomes a typed, persisted degeneracy outcome, never silently dropped or replaced with a percentile interval.
- Weak, null, mixed, or unfavorable-direction evidence is reported as such; it never triggers a rerun and is never reworded to look confirmatory.

## Failure behavior
Fix the statistical issue or report the blocker and affected evidence.
