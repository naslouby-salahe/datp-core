# Dependency graph and dead-code review

Scope: read-only review of all `src/datp_core` packages, using the existing Graphify graph and source verification. The authoritative roadmap was read in full before classification; `00_JOURNAL_CONTRACT.md` was read first. Tests were treated as evidence, never as production roots.

## Graph evidence and production roots

- Graphify 0.8.39 is installed in WSL at `/home/naslouby/.local/bin/graphify`.
- The repository graph was queried with `graphify explain`, `affected`, and `query`. At review time it contained approximately 4,905 nodes and 45,012 extracted links before the shared graph refresh; Graphify reported no reverse-reachable consumers for `heterogeneity_association_from_observations` and `multiplicity.py` as a module. Source verification corrected the latter false-negative: the multiplicity types are imported into analysis preparation/evidence, so it is not a dead-code finding.
- The actual Python package entrypoint is `datp_core.app.cli.app:main` (`pyproject.toml`); recipes in `app/recipes.py` provide the runtime dispatch surface. A Graphify-unreachable result was not treated as a deletion decision.
- `src/datp_core/experiments/confirmatory/run.py` is the live confirmation/mechanism path. It directly calls `cluster_evidence_from_grouped_result` and `cluster_stability` and publishes its `mechanisms` via confirmatory analysis. That source path is decisive for the cluster findings below.

## Confirmed issues

### DG-001

- **Severity:** LOW
- **Disposition:** DELETE_DEAD
- **File:** `src/datp_core/analysis/mechanisms/__init__.py:217`
- **Symbol:** `heterogeneity_association_from_observations`
- **Roadmap requirement:** Heterogeneity-benefit association must calculate the locked benign-score JS summary and B1–B2 benefit, then report Spearman/descriptive regression (roadmap §7.4 / §12.6).
- **Roadmap section:** Experiment catalogue §7.4; evaluation §12.6.
- **Graphify evidence:** `graphify explain heterogeneity_association_from_observations` reported only its contained outgoing call to `heterogeneity_benefit_association`; `graphify affected ... --depth 5` found no affected nodes.
- **Direct source evidence:** repository-wide symbol search finds this name only in its definition and `__all__`. Live `experiments/confirmatory/run.py` and `experiments/heterogeneity/run.py` import and call the authoritative `heterogeneity_benefit_association` directly.
- **Current callers:** none.
- **Current callees:** `heterogeneity_benefit_association`.
- **Production reachable:** NO.
- **Test-only reachable:** NO.
- **Scientifically required:** NO (the association responsibility is live through `heterogeneity_benefit_association`).
- **Problem:** An unused one-line forwarding wrapper adds a second public name for the same analysis without owning any protocol semantics.
- **Scientific consequence:** none if removed; the required association algorithm and its live callers remain unchanged.
- **Runtime consequence:** none.
- **Architecture consequence:** unnecessary public surface and indirection.
- **Correct final state:** remove this wrapper and its `__all__` entry; retain and use `heterogeneity_benefit_association` directly.
- **Affected callers:** none.
- **Affected callees:** `heterogeneity_benefit_association` remains live.
- **Affected tests:** none identified.
- **Affected artifacts:** none.
- **Why unreachable:** no production or test reference exists beyond definition/export.
- **Why scientifically unnecessary:** the roadmap requires the association result, not a wrapper; the direct implementation is already authoritative and live.
- **Superseding implementation:** `analysis/mechanisms/association.py:heterogeneity_benefit_association`.
- **Production behavior after removal:** unchanged.
- **Confidence:** CONFIRMED.

### DG-002

- **Severity:** MEDIUM
- **Disposition:** FIX_TEST_ONLY_ARTIFACT
- **File:** `src/datp_core/data/ciciot2023/populations.py:89,97`
- **Symbol:** `reject_physical_device_interpretation`, `reject_family_interpretation`
- **Roadmap requirement:** CICIoT2023 is limited to file-defined pseudo-clients; it cannot support physical-device claims, physical repartitioning, or B3 family thresholding (roadmap §9.2 / catalogue §4.2 and §10.2).
- **Roadmap section:** §9.2; catalogue §§4.2, 10.2.
- **Graphify evidence:** no production inbound edges were found for either function; graph inspection classified their only consumers as test files.
- **Direct source evidence:** exact symbol search finds only the two definitions and `tests/unit/datasets/ciciot2023/test_populations.py`. Production enforces the boundary centrally: `PopulationDeclaration` assigns `FILE_DEFINED_PSEUDO_CLIENTS`, and `protocols/validation.py:_validate_experiment_thresholds` rejects a family threshold for populations without a family taxonomy. CIC's construction also rejects temporal use directly.
- **Current callers:** unit test only.
- **Current callees:** none beyond constructing and raising `CapabilityError`.
- **Production reachable:** NO.
- **Test-only reachable:** YES.
- **Scientifically required:** NO as standalone functions; YES as a boundary, already enforced by live declaration/validation.
- **Problem:** test-oriented convenience raisers live in a production population builder but are not on any runtime route.
- **Scientific consequence:** retaining them does not add protection; the live registry/protocol validation is the actual guard.
- **Runtime consequence:** none at present.
- **Architecture consequence:** duplicate, bypassable enforcement vocabulary can mislead future callers about the authoritative guard.
- **Correct final state:** remove both helpers and migrate their tests to assert the live population declaration/protocol-validation rejection.
- **Affected callers:** only `test_populations.py`.
- **Affected callees:** none.
- **Affected tests:** `tests/unit/datasets/ciciot2023/test_populations.py`.
- **Affected artifacts:** none.
- **Confidence:** CONFIRMED.

### DG-003

- **Severity:** MEDIUM
- **Disposition:** FIX_TEST_ONLY_ARTIFACT
- **File:** `src/datp_core/data/edge_iiotset/populations.py:154,162`
- **Symbol:** `reject_attack_sensitive_request`, `reject_family_thresholding`
- **Roadmap requirement:** static Edge sensor groups support benign FPR equity only; per-client attack-sensitive metrics and B3 are unavailable (roadmap §9.4 / catalogue §4.4 and §10.1).
- **Roadmap section:** §9.4; catalogue §§4.4, 10.1.
- **Graphify evidence:** no production inbound edges; Graphify and source search identify only `tests/unit/datasets/edge_iiotset/test_populations.py` as consumers.
- **Direct source evidence:** `PopulationDeclaration` marks `SOURCE_DEFINED_SENSOR_GROUPS` as not requiring client attack assignment or a family taxonomy. `protocols/validation.py:_validate_experiment_thresholds` rejects family thresholding, and `_validate_experiment_metrics` rejects attack-sensitive metrics for that population. The Edge recipe declares only the permitted scope.
- **Current callers:** unit test only.
- **Current callees:** none beyond constructing and raising `CapabilityError`.
- **Production reachable:** NO.
- **Test-only reachable:** YES.
- **Scientifically required:** NO as standalone functions; YES as a boundary, already enforced centrally.
- **Problem:** two test-only duplicate guards reside in production code.
- **Scientific consequence:** none if removed when tests are moved to the central validation path; central validation is stronger because it covers every declared experiment.
- **Runtime consequence:** none.
- **Architecture consequence:** duplicates an existing science boundary and expands an otherwise narrow population-builder API.
- **Correct final state:** remove both helpers; test the registry/protocol gate and the typed unavailable metrics instead.
- **Affected callers:** only `test_populations.py`.
- **Affected callees:** none.
- **Affected tests:** `tests/unit/datasets/edge_iiotset/test_populations.py`.
- **Affected artifacts:** none.
- **Confidence:** CONFIRMED.

### DG-004

- **Severity:** HIGH
- **Disposition:** WIRE_REQUIRED
- **File:** `src/datp_core/analysis/mechanisms/dispersion.py:62`
- **Symbol:** `grouped_dispersion` and `GroupedDispersionResult`
- **Roadmap requirement:** the Regime A family/cluster mechanism programme requires within-cluster and across-cluster threshold and FPR dispersion, alongside membership, sizes, singleton/empty diagnostics, and stability (catalogue §7.1; evaluation §6.3).
- **Roadmap section:** catalogue §7.1; evaluation §6.3.
- **Graphify evidence:** Graphify source-link inspection shows no production call to `grouped_dispersion`; its only execution consumer is its unit test. The result type is handled by presentation export, showing a complete output path exists if evidence reaches it.
- **Direct source evidence:** `_confirmatory_cluster_mechanisms()` in `experiments/confirmatory/run.py:432` emits `ClusterEvidenceRecord` and `ClusterStabilityResult` only. It never imports or calls `grouped_dispersion`, despite loading the cluster threshold result and the cluster evaluation documents needed to derive client FPRs. `GroupedDispersionResult` is constructed only in `grouped_dispersion`; the latter is referenced only by its unit test and the unused bundle below. `presentation/export.py` has explicit rendering for it, but no producer passes such a record to `analyze_confirmatory_evidence`.
- **Current callers:** `tests/unit/analysis/test_mechanisms.py` only; unused `cluster_mechanism_bundle` contains the sole non-test call.
- **Current callees:** none downstream at runtime; presentation can render it when present.
- **Production reachable:** PARTIAL (implementation/importable and renderable, but no runtime producer).
- **Test-only reachable:** YES.
- **Scientifically required:** YES.
- **Problem:** required grouped FPR-dispersion evidence is implemented but disconnected from the confirmatory mechanism workflow.
- **Scientific consequence:** the published mechanism evidence lacks the roadmap-required within/across group FPR dispersion (and associated singleton/empty group report) even though other cluster evidence is present.
- **Runtime consequence:** no failure; a scientifically incomplete report can be produced.
- **Architecture consequence:** a fully typed evidence model and renderer are stranded.
- **Correct final state:** have `_confirmatory_cluster_mechanisms()` construct one `GroupDispersionObservation` per persisted B4 membership from (a) each member's contributing local threshold and (b) the corresponding B4 evaluation FPR, call `grouped_dispersion`, and append the result to the `MechanismEvidence` tuple consumed by `analyze_confirmatory_evidence`. Preserve typed unavailable evidence for partial/corrupt/unavailable clusters rather than emitting zeroes.
- **Affected callers:** add the invocation in `experiments/confirmatory/run.py:_confirmatory_cluster_mechanisms`.
- **Affected callees:** `grouped_dispersion`; `analyze_confirmatory_evidence`/publication/export receive the evidence.
- **Affected tests:** extend confirmatory mechanism integration coverage; retain unit mathematical tests.
- **Affected artifacts:** confirmatory `analysis.json`, mechanism evidence report, publication tables/figures.
- **Required wiring detail:** the exact responsibility is catalogue §7.1 grouped dispersion. The owner is the existing confirmatory cluster-mechanism collector because it already owns threshold-result checksums, membership, B1/B2/B4 documents, and the final mechanism list. The downstream consumer is confirmatory analysis/publication.
- **Confidence:** CONFIRMED.

### DG-005

- **Severity:** LOW
- **Disposition:** DELETE_DEAD
- **File:** `src/datp_core/analysis/mechanisms/__init__.py:170`
- **Symbol:** `cluster_mechanism_bundle`
- **Roadmap requirement:** Cluster evidence, stability, and grouped dispersion are required as separate evidence records where valid (catalogue §7.1; evaluation §6.3).
- **Roadmap section:** catalogue §7.1; evaluation §6.3.
- **Graphify evidence:** no inbound production or test call exists; exact source search finds only definition and `__all__`.
- **Direct source evidence:** the live collector independently calls `cluster_evidence_from_grouped_result` and `cluster_stability` (`confirmatory/run.py:503,514`). This unused bundle additionally contains the stranded call to `grouped_dispersion`, but no runtime code invokes it. Its two-seed signature does not match the collector's separate all-adjacent-seed stability loop, so wiring it would be a misleading partial replacement.
- **Current callers:** none.
- **Current callees:** `cluster_evidence_from_grouped_result`, `cluster_stability`, `grouped_dispersion`.
- **Production reachable:** NO.
- **Test-only reachable:** NO.
- **Scientifically required:** NO as a bundle; its responsibilities are either already live or must be wired explicitly under DG-004.
- **Problem:** unused composition helper duplicates the live cluster-evidence and stability construction, while its only unique computation is not actually delivered.
- **Scientific consequence:** do not wire this wrapper merely because it calls grouped dispersion; DG-004 should be integrated at the actual evidence owner with correct B4 FPR mapping.
- **Runtime consequence:** none if removed after DG-004 is wired.
- **Architecture consequence:** dead orchestration code obscures the true producer and falsely suggests dispersion is already included.
- **Correct final state:** delete the bundle and its `__all__` export; keep its needed grouped-dispersion logic through an explicit, verified implementation at the collector.
- **Affected callers:** none.
- **Affected callees:** retain the individual live algorithms.
- **Affected tests:** none identified; add integration coverage under DG-004 instead of a bundle test.
- **Affected artifacts:** none directly.
- **Why unreachable:** no symbol reference beyond definition/export.
- **Why scientifically unnecessary:** the roadmap specifies outputs, not this wrapper; live code already owns two outputs and the required third must be integrated there.
- **Superseding implementation:** direct calls in `_confirmatory_cluster_mechanisms`, extended per DG-004.
- **Production behavior after removal:** unchanged after the correct grouped-dispersion wiring.
- **Confidence:** CONFIRMED.

## Deliberately retained / not classified as dead

- `analysis/inference/multiplicity.py` initially appears reverse-unreachable in a Graphify module query, but `analysis/preparation.py` and `analysis/evidence.py` import its types and invoke `holm_adjust` when a plan is supplied. It is conditional support for the roadmap's secondary multiplicity rule, not dead.
- `analysis/adapters/scipy.py` is live: association analysis imports and calls both extraction adapters.
- `canonical_schema_checksum` is live through every dataset schema declaration; the apparent test-only direct call is not a dead-code signal.
- `jensen_shannon_from_client_scores` and `threshold_movements_from_evaluations` are live in confirmatory and controlled-heterogeneity runs.

## Coverage and conclusion

Reviewed all production packages at dependency-graph level, production script entrypoint, CLI/recipe root, direct experiment runner imports, re-exports, test-only inbound candidates, and all Graphify-unreachable candidates material to the required threshold/cluster mechanism path. This focused dependency review identified **three confirmed dead/test-only abstractions (five symbols)** and **one confirmed journal-required disconnected evidence path**. No deletion is recommended solely from Graphify reachability. No suspected-only issues are carried forward from this subtask.
