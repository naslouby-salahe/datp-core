# Threshold Semantics Hook

## Trigger
After any edit touching B0, B1, B2, B3, B4, `B-FedStatsBenign`, τ-shrink, calibration-size-aware fallback, or B2-conf.

## Purpose
Protect the locked threshold-policy meanings and naming.

## Blocking status
Blocks completion.

## Required checks
- B1 (client-averaged shared τ) and B2 (per-client p95) keep their exact locked meanings; B3 is family-mean only (Regime A, requires taxonomy); B4 is k-means cluster-mean on the four-scalar fingerprint `[µ_e, σ_e, skew_e, p95(e)]` with canonical `K = 3` (K = 9 and other K are exploratory only, never presented as canonical).
- `B-FedStatsBenign`/`B-LaridiFaithful` never regress to a prior `B5` label; τ-shrink/LGS never regresses to a prior `B3-LGS` label; a model-personalization fallback is never labeled "Ditto" unless the true Ditto algorithm is implemented.
- No threshold construction accepts attack/test-split data as calibration input.
- Threshold state crossing a module boundary is typed (enum/frozen-dataclass), never a raw protocol string or dict.
- No hidden default or silent fallback replaces a stale threshold value.

## Failure behavior
Stop the edit and report the exact semantic or naming violation; never rename or reinterpret a locked threshold identifier to make an edit fit.
