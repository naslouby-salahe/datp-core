# Anchor reproduction and scientific-fidelity audit

Scope: read-only review of the historical-anchor execution, comparison/gate, confirmatory handoff, scientific decision, and publication paths.  I read `docs/graphify_audit/00_JOURNAL_CONTRACT.md` and the complete master roadmap before classifying findings.  Graphify 0.8.39 was available in WSL; its BFS traversal for `anchor gate confirmatory publication` linked the gate, `ConfirmatoryAnalysis`, and publication communities.  Source tracing below is authoritative where the graph is broad.

## Findings

### AS-001 — Anchor checkpoint semantics are asserted by the adapter, not evidenced by the evaluation artifact

- **Severity:** High
- **Disposition:** FIX_RUNTIME_BUG
- **File:** `src/datp_core/experiments/anchor/run.py:126-168`; `src/datp_core/experiments/anchor/reproduction.py:365-376`; `src/datp_core/experiments/anchor/comparison.py:193-208`
- **Symbol:** `observation_from_evaluation_document`; `_reject_non_historical_checkpoint`; `_coordinate_mismatch_reason`
- **Roadmap requirement/section:** Historical anchor reproduction must preserve the historical endpoint/checkpoint semantics and fail closed before dependent confirmatory claims.
- **Graphify/source evidence:** Graphify BFS reaches the anchor gate and confirmatory-publication domain. Source shows the actual production adapter unconditionally constructs every `AnchorObservedMetric` with `checkpoint_status=ANCHOR_CHECKPOINT_STATUS`. The gate later rejects only that constructed field, and comparison compares only that same field to the reference. `FederatedEvaluationDocument` instead contains `score_checkpoint_checksum` but no checkpoint-selection/status evidence consumed here.
- **Callers/callees:** `app.anchor.reproduce_anchor` → `collect_independent_observations_from_evaluations` → `observation_from_evaluation_document` → `publish_independent_observations` → `verify_anchor` → `reproduce_anchor`/gate. `analyze_confirmatory_campaign` subsequently uses the verified gate/handoff for publication.
- **Prod/test reachable:** Production-reachable through `datp-core anchor reproduce` and full research flow; coverage exists for semantic rejection with manually-built observations, but it does not establish that a non-historical evaluation document cannot be relabelled as historical by the adapter.
- **Scientifically required:** Yes. A successful anchor must prove the historical checkpoint convention, not merely label an arbitrary score document as it.
- **Problem/consequences:** An evaluation document produced from a non-historical selection can be accepted if it is placed at the expected coordinate/path and happens to match reference metrics. The emitted anchor evidence then says `historical_endpoint` regardless of the checkpoint that generated it, allowing a false gate pass and a confirmatory publication to cite it.
- **Correct final state:** Carry verifiable checkpoint-selection identity/status from the scoring/evaluation provenance into the evaluation document, then have `observation_from_evaluation_document` validate it against the locked historical checkpoint protocol before assigning the anchor status. Bind the verified identity/checksum into the independent observation and make the comparison/gate reject mismatch.
- **Affected callers/callees/tests/artifacts:** `observation_from_evaluation_document`, `FederatedEvaluationDocument`/score provenance, independent observation package, anchor diagnostics/handoff; add an integration test producing a document with a non-historical selected checkpoint and asserting that collection/verification blocks.
- **Confidence:** Confirmed (high).

### AS-002 — Execution-time anchor gate does not validate the programme-binding handoff

- **Severity:** Medium
- **Disposition:** WIRE_REQUIRED
- **File:** `src/datp_core/app/anchor.py:22-27`; `src/datp_core/app/research.py:82-91`; `src/datp_core/experiments/anchor/gate.py:328-374`
- **Symbol:** `anchor_gate_permits_dependents`; `_enforce_anchor_gate`; `validate_handoff_against_confirmatory_programme`
- **Roadmap requirement/section:** The anchor gate is the required dependency before the full confirmatory programme; a pass must be tied to the locked programme rather than a mutable boolean/status.
- **Graphify/source evidence:** Graphify traversal placed the gate on the confirmatory path. Source tracing shows full `run_experiment` calls `_enforce_anchor_gate`, which calls `anchor_gate_permits_dependents`; that function only loads a decision and accepts PASS/PASS_WITH_DECLARED_DISCREPANCY. The stronger `load_verified_anchor_gate_artifact` plus `load_anchor_confirmatory_handoff` and `validate_handoff_against_confirmatory_programme` are called only later by `analyze_confirmatory_campaign`.
- **Callers/callees:** Full experiment dispatch → `_enforce_anchor_gate` → `anchor_gate_permits_dependents`; later confirmatory analysis → verified gate + handoff validation → publication.
- **Prod/test reachable:** Production-reachable for a full dependent run. Tests cover handoff validation, but no production execution caller invokes it before dispatch.
- **Scientifically required:** Yes; otherwise a pre-change PASS can authorize costly/reported dependent execution after a confirmatory protocol/provenance change, even though final analysis later fails.
- **Problem/consequences:** The final publication is protected, but the mandatory gate is incomplete at the stated execution boundary. A stale/partial anchor decision can let dependent artifacts be created, creating avoidable scientific-wiring ambiguity and wasted computation.
- **Correct final state:** Replace the status-only predicate used for full dependent execution with a fail-closed verified-gate-and-handoff loader (or make it call `load_anchor_confirmatory_handoff` after verification). Preserve an explicit inspect-only status path separately.
- **Affected callers/callees/tests/artifacts:** `app.research._enforce_anchor_gate`, `app.anchor.anchor_gate_permits_dependents`, all recipes with `AnchorRequirement`, gate diagnostics/handoff; add a full-dispatch test with a syntactically valid PASS whose handoff is stale against the confirmatory programme and assert dispatch blocks.
- **Confidence:** Suspected (medium): source establishes the missing execution-time wiring; the exact intended boundary wording should be reconciled with the roadmap owner.

## Verified controls / no issue recorded

- Full anchor reproduction dispatches the historical declaration for the locked five-seed cohort before collecting observations; it does not simply compare a hand-authored metric file.
- The comparison rejects the confirmatory ten-seed cohort, wrong coordinates, missing/duplicate observations, and uses full precision plus per-metric rules rather than a global rounding tolerance.
- Gate persistence checks the decision digest and completion marker; a blocked gate cannot yield a verified claim-permitting artifact. Confirmatory analysis validates both verified gate and programme-bound handoff before `export_confirmatory_publication`.
- Publication export routes confirmatory claims through `validate_claim`, which requires the verified anchor artifact and narrows non-supported/non-primary evidence. `decide_confirmatory` appropriately uses the paired BCa interval sign/zero crossing rather than a point estimate alone.

## Coverage and classification

Covered production modules: `experiments/anchor/{run,reproduction,comparison,gate,contracts,spec}`, `app/{anchor,research}`, confirmatory analysis handoff, `analysis/{preparation,scientific_decision}`, and `presentation/{validation,export}`; relevant unit/integration/scientific test references were inspected by call-site search. No production files were changed and tests were not run. Confirmed: 1 (AS-001). Suspected wiring: 1 (AS-002). No test-only/dead-code candidates were recorded in this scientific-fidelity pass.
