# Scientific-drift audit

## Confirmed drift

- **SD-01 / HIGH / `FIX_SCIENTIFIC_DRIFT`:** threshold-estimation diagnostics construct the exact pooled reference from held-out evaluation benign scores, violating calibration/evaluation isolation. See II-02.
- **SD-02 / HIGH / `FIX_SCIENTIFIC_DRIFT`:** B-FedStatsBenign omits a declared benign summary and its complete communication disclosure. See II-01.
- **SD-03 / HIGH / `FIX_RUNTIME_BUG`:** stale B0 cache reuse can rebrand prior preprocessing/split/model state as the current independent centralized reference. See II-03.
- **SD-04 / HIGH / `FIX_RUNTIME_BUG`:** anchor checkpoint status is asserted instead of artifact-evidenced. See II-04.

## Verified aligned controls

FedAvg and B1–B4 preserve fixed scores, score coordinates, preprocessing, splits, eligibility, and paired BCa seed semantics. B1 is mean local quantiles, B2 local, B3 taxonomy-bound, B4 has the locked score fingerprint/StandardScaler/K=3. Calibration is benign-only and checks row disjointness; prediction uses strict `>`; metrics use `ddof=0` and typed undefined values. FedProx has separate detector/scores and non-test loss selection; Ditto preserves global/personalized state separation. Edge attack-sensitive outcomes are typed unavailable; CIC remains file-pseudo-client only; temporal chronology path is guarded. These were source-verified and 819 tests passed.

## Claim/role watch

Regime C is declared `MECHANISM` in code while the contract describes it as supportive controlled sensitivity. This is a LOW `ROADMAP_AMBIGUITY`: reconcile export/manuscript role metadata before results are framed; it does not change runtime threshold semantics.

