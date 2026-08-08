# Independent adversarial review

Read `00_JOURNAL_CONTRACT.md`, the complete roadmap, and every current report in `docs/graphify_audit/subagents/`. I used Graphify 0.8.39 as a navigation check and re-ran source searches from real CLI/recipe roots. Graphify's edge-collapse warning means classifications below rely on source-call evidence. Tests are not treated as production roots.

## Reconciled findings

### AR-001 — Legacy preprocessing island: one deletion finding, not two different remediations

- **Severity:** Medium
- **Disposition:** DELETE_DEAD
- **File:** `src/datp_core/data/preprocessing/{contracts,fitting,transforms,validation}.py`
- **Symbol:** legacy in-memory `PreprocessingProtocol` / `FittedPreprocessingState` family
- **Roadmap requirement/section:** persisted benign-train-only preprocessing is required; the old in-memory duplicate is not.
- **Graphify/source evidence:** `rg` confirms `fit_federated_preprocessing` has only its definition; the competing reports independently trace the persisted `service`/artifact-validation pipeline from execution. No production or test caller reaches the island.
- **Callers/callees:** internal-island imports only; live execution calls persisted preprocessing instead.
- **Prod/test reachable:** no/no.
- **Scientifically required:** no; its responsibility is superseded.
- **Problem/consequences:** Architecture and dataset reports describe the identical deletion candidate; leaving both as separate actions would duplicate remediation tracking.
- **Correct final state:** one deletion item, after checking any explicitly supported external Python API; no merge/compatibility alias in the repository.
- **Affected callers/callees/tests/artifacts:** no repository callers/tests/artifacts.
- **Confidence:** confirmed. Resolves AD-001 versus DP-001: `DELETE_DEAD` is more precise than `MERGE_DUPLICATE` because no migration consumer exists.

### AR-002 — Grouped dispersion remains a genuine required disconnected path

- **Severity:** High
- **Disposition:** WIRE_REQUIRED
- **File:** `src/datp_core/analysis/mechanisms/dispersion.py:62`; `src/datp_core/experiments/confirmatory/run.py:_confirmatory_cluster_mechanisms`
- **Symbol:** `grouped_dispersion`, `GroupedDispersionResult`
- **Roadmap requirement/section:** Regime-A cluster mechanism must publish within/across-group threshold and FPR dispersion.
- **Graphify/source evidence:** source search finds the computation called only by its unit test and dead `cluster_mechanism_bundle`; export has a renderer but no live producer. This is not refuted by the live cluster membership/stability calls.
- **Callers/callees:** test/dead bundle → `grouped_dispersion`; live confirmatory collector → membership/stability → analysis/export, with the dispersion edge missing.
- **Prod/test reachable:** computation no/yes; renderer yes/no.
- **Scientifically required:** yes.
- **Problem/consequences:** a renderable required evidence artifact is absent from published mechanism output.
- **Correct final state:** wire it at the live cluster collector with B4 membership and B4 FPR, retaining unavailable diagnostics.
- **Affected callers/callees/tests/artifacts:** confirmatory collector, analysis document/publication, mechanism integration test.
- **Confidence:** confirmed. DG-004 retained; DG-005 `cluster_mechanism_bundle` may be deleted only after this direct wiring, not repurposed as a shortcut.

### AR-003 — Anchor claims have two distinct gaps; do not collapse them

- **Severity:** High (checkpoint evidence); Medium (execution-time handoff)
- **Disposition:** FIX_RUNTIME_BUG (AS-001); WIRE_REQUIRED, suspected (AS-002)
- **File:** `experiments/anchor/run.py:observation_from_evaluation_document`; `app/{anchor,research}.py`; `experiments/anchor/gate.py`
- **Symbol:** adapter checkpoint relabelling; `anchor_gate_permits_dependents`/`_enforce_anchor_gate`
- **Roadmap requirement/section:** historical-checkpoint anchor evidence must fail closed and gate dependent work/claims.
- **Graphify/source evidence:** the adapter writes the historical checkpoint status as a constant although the evaluation document exposes only a checkpoint checksum; the comparison tests the adapter-produced status. Separately, full dispatch checks only PASS status, whereas handoff/programme validation appears at confirmatory analysis. `rg` confirms `load_anchor_confirmatory_handoff` is production-called only there.
- **Callers/callees:** anchor reproduction → observation package → gate; full experiment → status predicate; confirmatory analysis → verified handoff → publication.
- **Prod/test reachable:** yes/yes (tests exercise manual rejection but not the adapter provenance case).
- **Scientifically required:** yes.
- **Problem/consequences:** AS-001 is an actual evidence-integrity defect, not merely a missing test. AS-002 is distinct from CLI-02: it concerns stale programme binding before execution, while CLI-02 concerns non-confirmatory report roots bypassing any anchor check.
- **Correct final state:** bind checkpoint-selection provenance into observed anchor data; make full dependent dispatch use verified gate plus validated handoff. Gate every report that has `AnchorRequirement.REQUIRED` as separately identified by CLI-02.
- **Affected callers/callees/tests/artifacts:** anchor adapter/package/gate/handoff, full dispatch, report dispatch; integration tests for wrong checkpoint and stale handoff.
- **Confidence:** AS-001 confirmed; AS-002 remains suspected because final analysis already fails closed and roadmap ownership of the earlier execution boundary needs confirmation.

### AR-004 — Centralized B0 cache defect is independent of the B0 report-wiring defects

- **Severity:** High
- **Disposition:** FIX_RUNTIME_BUG
- **File:** `detector/training/centralized_publication.py`; `detector/scoring/centralized.py`
- **Symbol:** `centralized_training_is_reusable`, `load_reused_centralized_training`, `centralized_scoring_is_reusable`
- **Roadmap requirement/section:** B0 must be independently trained with current pooled preprocessing/split provenance.
- **Graphify/source evidence:** real campaign root calls `run_centralized_reference_seed`; source cache reuse omits current coordinate/preprocessing/split/input identity then rebrands loaded artifacts.
- **Callers/callees:** campaign B0 runner → centralized training/reuse → scoring/threshold/evaluation.
- **Prod/test reachable:** yes/no.
- **Scientifically required:** yes.
- **Problem/consequences:** stale B0 can be presented as current. This is not cured by adding the missing B0 reports (CLI-01) or CIC B0 route (THRESH-04).
- **Correct final state:** persisted identity-bound centralized manifests and score-input provenance, then separate B0 report consumers for Regime A/CIC.
- **Affected callers/callees/tests/artifacts:** centralized B0 pipeline/reuse artifacts and report consumers.
- **Confidence:** confirmed. TS-001, CLI-01, and THRESH-04 are complementary, not duplicates.

### AR-005 — Confirmed downstream scientific omissions remain distinct

- **Severity:** High/Medium according to owning reports
- **Disposition:** FIX_INCOMPLETE or WIRE_REQUIRED
- **File:** `execution/workspace.py:_threshold_estimation_inputs`; `thresholds/variants/federated_statistics.py`; `experiments/{external,federated_threshold}/run.py`
- **Symbol:** held-out pooled oracle; FedStats benign-exceedance/communication record; Edge FedStats report; CIC B0 route
- **Roadmap requirement/section:** calibration/test separation; mandatory B-FedStatsBenign disclosure; Edge required comparator; CIC B0 contextual reference.
- **Graphify/source evidence:** alternate callers do not repair these: workspace evaluation is the only estimator diagnostic producer; Edge report reads B1/B2 only; centralized runner is N-BaIoT-hardcoded; FedStats dispatch is live but lacks required disclosure fields.
- **Callers/callees:** declared execution → workspace/threshold/evaluation; external run → B1/B2 report path only.
- **Prod/test reachable:** yes/no for the omissions.
- **Scientifically required:** yes.
- **Problem/consequences:** do not merge these into generic “reporting”: one contaminates a diagnostic oracle, one is an incomplete method contract, and two are missing consumers/routes.
- **Correct final state:** implement each owned artifact/route, preserving benign-only and unavailable semantics.
- **Affected callers/callees/tests/artifacts:** the named workspace, comparator, external analysis, and centralized/CIC route tests/artifacts.
- **Confidence:** confirmed from source; retain THRESH-01 through THRESH-04.

## Downgraded / disputed candidates

- **DP-002:** retain only as a low-priority `SIMPLIFY` hardening task, not a confirmed scientific defect. Both computations are deterministic under the same declared seed/protocol; no mismatch or alternate live root was demonstrated. A checksum assertion remains worthwhile.
- **DT-1 and STALE_API-01:** `experiments/registry.py` can be treated as a deletable exact duplicate after a public-API decision. The several family `ExperimentSpec` tuples should **not** be bulk-deleted yet: the reports establish no callers, but have not completed semantic parity/reconciliation with the canonical catalogue. Classify them as duplicate-declaration debt, not dead scientific implementation.
- **DT-3/DT-4/DT-5:** reject any deletion/defaulting. They are deliberate fail-closed unresolved protocol values; no caller path proves the scientific responsibility obsolete.
- **DG-002/DG-003:** test-only helper removal is safe only if tests are moved to the live declaration/protocol validator. Keep the underlying CIC/Edge boundary; do not describe the boundary itself as dead.
- **CLI-03/CLI-04:** retain as wiring/design findings, but distinguish execution `COMPLETE` from publication completion and keep optional-work separation; neither is evidence that individual scientific algorithms are unreachable.

## Coverage and conclusion

Reviewed all nine supplied reports against the CLI/campaign root, anchor/confirmatory handoff root, persisted preprocessing route, centralized B0 route, threshold workspace, external reporter, and test-only callers. Confirmed retain: legacy preprocessing deletion (one item), grouped-dispersion wiring, anchor checkpoint provenance, centralized cache identity, and threshold/external omissions. Flagged suspected: execution-time handoff validation. Reclassified DP-002 as hardening and shadow spec families as reconciliation debt. No production files were changed.
