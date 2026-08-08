# CLI, orchestration, entrypoint, dispatch, and artifact wiring audit

## Scope and method

Read `docs/graphify_audit/00_JOURNAL_CONTRACT.md` and the complete `docs/Journal_Extension_Master_Roadmap.md` before tracing production roots. This is a read-only production audit; no production file was changed.

Graphify was already installed in WSL at `/home/naslouby/.local/bin/graphify`. I refreshed the repository AST graph using `graphify update . --no-cluster`: 6,396 nodes and 95,547 extracted edges (6,382/48,746 after Graphify's directed edge collapse). Its multigraph diagnostic shows a high same-endpoint collapse count, so Graphify was used for traversal only; every conclusion below is corroborated in source.

The installed console script is `datp-core = datp_core.app.cli.app:main` (`pyproject.toml:51-52`). The WSL venv successfully rendered the root Typer help. `datp-core validate` reported five populations, 23 declarations, one suppressed declaration, and 22 registered recipes. `plan shared_vs_local_confirmation` reported the ten locked seeds `0..9` and 240 executable coordinate entries.

## Live roots and actual caller/downstream chains

| Public route | Actual chain | Boundary/artifacts |
|---|---|---|
| `datp-core run campaign` | `cli.execution.campaign_command` → `research.run_campaign` → validate declarations → readiness check all recipes → materialize all data → reproduce/verify anchor → `_run_centralized_reference` → `run_experiment` for every recipe → campaign `COMPLETE` → `generate_report(None)` | Only public route invoking independent B0 training/evaluation. |
| `datp-core run experiment ID` | `cli.execution.experiment_command` → `research.run_experiment` → declaration/readiness → FULL anchor gate where required → recipe dispatch | Does not materialize data or run B0. |
| Confirmatory dispatch | `_dispatch_confirmatory` → `confirmatory.run_confirmatory_seed` → `execution.execute_declared_experiment_seed` → `PipelineStageRunner` / completion store | B1/B2 coordinate plans run per seed. |
| Family mechanism | `_dispatch_family` → `run_family_grouped_mechanism_seed` → declared-execution primitive | Separate B1/B3/B4/B2 mechanism ladder. |
| Other regimes | external dispatcher → external/CIC runners; temporal dispatcher → temporal runner; stress dispatchers → FedProx/Ditto runners | Dedicated, non-confirmatory training/temporal routes. |
| Reporting | `cli.app.report_command` → `research.generate_report` → `recipe_for(ID).report` | Directly callable, independently of campaign execution. |
| Status | `cli.app.status_command` → `research.programme_status` → marker/analysis-marker checks | Campaign state is inferred solely from campaign `COMPLETE`. |

Graphify corroboration:

- `cli_execution_campaign_command --calls--> app_research_run_campaign` (one hop).
- `app_recipes_dispatch_confirmatory --calls--> run_confirmatory_seed --calls--> execute_declared_experiment_seed` (two hops).
- `cli_app_report_command --calls--> app_research_generate_report` (one hop).
- `app_research_run_campaign --calls--> app_research_run_centralized_reference` (one hop).

## Findings requiring wiring decisions

### WIRE_REQUIRED-CLI-01 — B0 is campaign-only and has no report consumer

**Journal requirement.** B0 is the contextual centralized reference: independently trained pooled AE, its own pooled MinMax preprocessing, and pooled benign threshold. It is not in the B1–B4 causal ladder, but the Regime A programme requires B0–B4 where valid.

**Evidence.** `run_campaign` is the only production orchestrator calling `_run_centralized_reference` (`src/datp_core/app/research.py:218-248`). The helper runs all ten confirmatory seeds (`:198-215`). The independent B0 runner performs population construction → centralized preprocessing → centralized training → checkpoint selection → scoring → pooled threshold → centralized evaluation (`src/datp_core/experiments/centralized_reference.py:54-145`). By contrast, the individual route ends at `run_experiment`/recipe dispatch (`research.py:91-119`; `app/cli/execution.py:24-48`).

No B0 recipe exists. `EXPERIMENT_RECIPES` starts with the B1/B2 confirmatory recipe and contains no centralized-reference entry (`src/datp_core/app/recipes.py:813-956`). `_report_confirmatory` only calls `analyze_confirmatory_campaign` (`recipes.py:425-428`), whose live analysis loads B1/B2 (and optional B4) federated evaluation documents, not centralized evaluation (`experiments/confirmatory/run.py:158-238`). Repository search found the centralized runner called from `research.py` only; no report/presentation consumer was found.

**Impact.** `run experiment shared_vs_local_confirmation` and `report shared_vs_local_confirmation` can complete without B0. Even the campaign creates B0 artifacts which no report reads, validates, or presents. The journal-required contextual comparator is therefore not connected to the experiment/report product.

**Required direction.** Add a B0 report/presentation consumer and make the Regime A campaign/report package validate all ten independent B0 evaluations. If B0 remains campaign-only, make B0 an explicit reporting dependency and reject a Regime A report without it; never substitute a FedAvg pooled-score result.

### WIRE_REQUIRED-CLI-02 — anchor-gated reports bypass the anchor gate

**Journal requirement.** Historical-anchor equivalence gates dependent Regime-A evidence. A dependent claim cannot be released after a failed anchor gate.

**Evidence.** Execution is protected: FULL `run_experiment` calls `_enforce_anchor_gate` (`src/datp_core/app/research.py:91-109`) and Regime-A recipes carry `AnchorRequirement.REQUIRED` (`src/datp_core/app/recipes.py:813-956`). But `generate_report(ID)` immediately resolves `recipe.report` with no `_enforce_anchor_gate`/`anchor_gate_permits_dependents` call (`research.py:256-265`), and public `report` calls it directly (`app/cli/app.py:99-113`). `_report_confirmatory` alone loads the verified gate artifact and handoff (`recipes.py:425-428`; `experiments/confirmatory/run.py:158-171`). `_report_supplementary`, `_report_fedprox`, `_report_ditto`, `_report_robustness`, `_report_estimation`, and `_report_heterogeneity` have no comparable precondition (`app/recipes.py:460-621`).

**Impact.** Existing/staged evidence can be rendered by direct report commands for family, stress, robustness, estimation, and mechanism experiments despite anchor failure. Execution-time protection is insufficient because reporting is a separate public root.

**Required direction.** Enforce `recipe.anchor_requirement` in `generate_report` (or a shared report precondition) before every handler. Retain the confirmatory handoff as its stronger experiment-specific check.

### WIRE_REQUIRED-CLI-03 — campaign `COMPLETE` precedes reporting and can signal completion with missing mandatory packages

**Journal requirement.** Mandatory evidence must be reportable with typed unavailable/infeasible outcomes; completion must not imply a complete journal package while mandatory reports are silently absent.

**Evidence.** `run_campaign` writes `outputs/campaign/COMPLETE` after recipe executions (`src/datp_core/app/research.py:235-247`) then calls `generate_report(None)` (`:248`). `_generate_campaign_report` catches `AnchorReproductionError`, `MissingPrerequisiteError`, `ReportEvidenceError`, and `ScientificContractError` for each recipe, appends `...:missing(...)`, and continues (`research.py:268-288`). It returns normally, so the already-written marker remains. `programme_status` determines campaign completion solely from this marker (`research.py:291-310`).

**Impact.** A campaign can be marked complete while mandatory reports are absent. Downstream automation has no artifact-level barrier against treating the marker as full scientific completion.

**Required direction.** Publish campaign completion only after mandatory report artifacts validate, or split execution completion from publication completion and display both. Typed unavailable results are fine; silently missing mandatory reports are not.

### WIRE_REQUIRED-CLI-04 — optional analyses are on the mandatory campaign critical path

**Journal requirement.** The roadmap says optional high-value analyses (robust cluster-median and additional equity indices) cannot delay the mandatory programme.

**Evidence.** `GROUP_MEDIAN_SUPPLEMENT` and `OPTIONAL_EQUITY_INDICES` are exploratory in the canonical protocol (`src/datp_core/protocols/experiments.py:439-455`) but registered as ordinary recipes (`src/datp_core/app/recipes.py:944-955`). `run_campaign` readiness-checks **all** recipes and executes **all** recipes before the completion marker (`src/datp_core/app/research.py:218-247`). Thus either optional runner may throw and prevent campaign completion.

**Impact.** A discretionary exploratory failure can block the confirmatory result and mandatory comparator/stress programme.

**Required direction.** Separate mandatory and optional recipe cohorts. Make optionals explicit-run or post-completion work with independent status; do not put them on the mandatory campaign critical path.

## Confirmed wiring and intentional boundaries

- Console entrypoint, Typer sub-app registration, error-to-exit mapping, `run experiment`, and `run campaign` are live in WSL.
- Confirmatory and family routes use the shared declared-execution primitive. External, temporal, FedProx, and Ditto use distinct runners, so they are not silently run as FedAvg confirmatory work.
- B-FedStatsBenign is live for Edge validation through the canonical declaration and external dispatcher (`src/datp_core/protocols/experiments.py:370-399`; `src/datp_core/app/recipes.py:215-235`).
- Alert-burden translation is suppressed with no recipe (`protocols/experiments.py:207-215,430-437`). With no declared measured/cited benign rate, this matches the roadmap's omit-if-unavailable rule and is not a missing implementation.
- Size-aware shrinkage deliberately executes only B1/B2 reference corners and marks the method unavailable because no `lambda(n_k)` function is declared (`threshold_robustness/run.py:496-570`; `app/recipes.py:326-355`). This respects the no-invention rule.
- `src/datp_core/experiments/registry.py` and several family `spec.py` modules duplicate declarations, but production planner/runners import `datp_core.protocols.experiments.EXPERIMENTS`; `rg` found no production caller of the shadow registry/spec tuples. This is divergence debt, not currently a missing live route.

## Artifact lifecycle conclusion

The generic execution primitive creates coordinate completion records only after model/evaluation artifacts reload and validate (`src/datp_core/experiments/execution/engine.py`, finalization stage). That local lifecycle is sound. The campaign/publication boundary is the weakness: B0 has no report edge, anchor-gated direct reports lack gate validation, campaign `COMPLETE` precedes and masks report failures, and optional work gates the mandatory completion path.
