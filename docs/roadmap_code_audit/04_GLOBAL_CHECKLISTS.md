# 04 — Global Checklists

Executed against each domain named in Audit Matrix's global checklists (scientific identity, datasets,
populations, splits, preprocessing, training, checkpointing, scoring, calibration, thresholding,
evaluation, statistics, experiments, anchor, temporal logic, artifacts/provenance, publication,
numerical locks, scientific drift). Each item below cites the discovery-subagent evidence file it came
from; see `08_FINDINGS.md` for the only two confirmed non-PASS items (both architectural, not scientific).

| Checklist item | Status | Evidence |
|---|---|---|
| Fixed-detector reuse across compared threshold policies | PASS | `ExperimentWorkspace.selected_checkpoint`/`.scores` are `@cached_property`, single evaluation per coordinate |
| Fixed-preprocessing reuse | PASS | zero `fit_*` calls found anywhere under `src/datp_core/thresholds/` |
| Score-artifact scientific identity (not just numeric closeness) | PASS | `FixedScoreInvariant` + exact-string completion-marker equality, no tolerance at policy level |
| Population/split identity reuse across compared conditions | PASS | `ExperimentCoordinate.stable_key` binds dataset/population/seed/split/preprocessing/coefficient/threshold/temporal/partition |
| Benign-only calibration | PASS | `reject_non_benign_labels()`/`load_benign_calibration_references()` in `thresholds/calibration/eligibility.py` |
| Eligibility timing (before subsampling, not redefined after) | PASS | `decide_eligibility()` operates on pre-subsampling `CalibrationSupport` |
| Checkpoint selection non-test | PASS | `require_non_test_checkpoint_selection_inputs()` raises `LeakageError` on held-out metrics/attack labels |
| CUDA-only training, no CPU fallback | PASS | `runtime/compute.require_cuda_available()` raises unconditionally if CUDA absent; called from all 4 training paths |
| FedProx ≠ FedAvg (proximal term genuinely conditional) | PASS | `engine.py` applies `ProximalTerm` only when coefficient present; μ=0 excluded from FedProx grid |
| Ditto genuinely personalized (not relabeled FedAvg) | PASS | separate `global_state`/`personalized_states` dicts, personalized states never aggregated |
| Anchor gate blocks downstream on failure | PASS | `_enforce_anchor_gate()` called before `run_campaign`/`generate_report`, raises on `ANCHOR_REPRODUCTION_FAILED` |
| Temporal ordering (historical < future) enforced in code | PASS | `validate_no_future_history_leakage()` in `data/populations/integrity.py` |
| No pseudo-chronology fabrication | PASS | temporal split raises `ScientificContractError` on null timestamps rather than synthesizing order |
| Metric formulas match Formula Ledger exactly | PASS (36 spot-checked) | `analysis/metrics/*`, `analysis/inference/*` |
| Statistical resampling unit is seeds, not rows/clients | PASS | `bootstrap/estimation.py` resamples `paired_deltas` (10 seeds), not row/client arrays |
| Unavailable metrics typed, never silently zero/NaN | PASS | `MetricAvailability = AvailableMetric \| UnavailableMetric` union, explicit `MetricReason` |
| Checksum/provenance single-sourced | PASS | `artifacts/provenance.py` (SHA-256) is the sole hashing implementation used across repositories |
| Completion markers fail-closed (missing → incomplete, not exception-swallowed success) | PASS | `artifact_completion_marker_matches()` returns `False` on missing/unreadable marker |
| `--overwrite` scoped to owning artifact only | PASS | targeted `rmtree(target)` per repository, no global purge |
| No `latest` alias / random run IDs / hidden caches | PASS | confirmed via grep, no `uuid`/`latest` in artifact path construction |
| Naming discipline (no B0-B5/Regime A-D in production code) | PASS | zero matches in `src/datp_core/` |
| No `pass`/`NotImplementedError`/TODO/FIXME in audited packages | PASS | zero matches across `app/`, `data/`, `detector/`, `thresholds/`, `analysis/`, `experiments/` |
| Canonical package-level tree (no obsolete top-level roots) | PASS | `test_architecture.py` + direct search confirm all obsolete roots absent |
| Canonical **file-level** tree in `artifacts/{repositories,serializers}` and `experiments/*/{spec,analyze,report}.py` | **PARTIAL** | see ARCH-001/ARCH-002 in `08_FINDINGS.md` — file-location deviation, no scientific-behavior consequence found |
