# Test, compatibility, and stale-API audit

## Scope and method

- Read the complete audit contract in `docs/graphify_audit/00_JOURNAL_CONTRACT.md` (the parent audit also supplied the complete authoritative roadmap before this pass).
- Read-only review of all `tests/` sources (194 Python files by inventory), test configuration, compatibility paths, production imports, and the Graphify-indexed production declaration roots.
- Static import searches were followed by `pytest --collect-only -q`: **819 tests collected in 21.95 s**.  A focused collection of the CLI/architecture suite collected **8 tests in 3.67 s**.  Collection passed; this is collection evidence, not execution evidence.

## Confirmed boundaries

### `TEST_BOUNDARY-01` — no production dependency on the test suite (confirmed)

**Contract relevance.** Production execution and reporting must be independently runnable; test utilities must not become a production runtime dependency.

**Evidence.** A repository-wide production search for `pytest`, `hypothesis`, `tests.`, `unittest.mock`, `freezegun`, `faker`, and factory-library imports found no test-library/test-package import in `src/`.  The apparent matches for `hypothesis` are ordinary domain variables in `analysis/inference/multiplicity.py` and presentation formatting, not imports.  The reverse search found no `from tests...` or `import tests...` in production either.

**Caller/downstream chain.** Test runner -> `tests.pytest_cuda` (configured by `pyproject.toml` `addopts`) -> test items.  Production roots (`app/campaign.py`, `app/planning.py`, `experiments/execution/engine.py`) import only production protocol modules.  There is no production -> test edge.

**Disposition.** No test-only production dependency was confirmed.

### `TEST_BOUNDARY-02` — the remaining direct test imports of spec modules are live production protocol dependencies (confirmed)

**Evidence.** Tests import only `experiments.anchor.spec` and `experiments.confirmatory.spec` among the older spec family: e.g. anchor reproduction/declaration tests and confirmatory inference tests.  These are not test-only aliases: production validation imports `ANCHOR_DECISION_PROTOCOL` and `CONFIRMATORY_INFERENCE_PROTOCOL`, while analysis, temporal, external, and confirmatory execution paths consume the confirmatory protocol.  Focused CLI/architecture collection passed.

**Caller/downstream chain.** Tests -> anchor/confirmatory spec -> `protocols/validation.py` and production analysis/execution consumers.  These imports therefore exercise live protocol declarations rather than an orphan compatibility layer.

**Disposition.** No stale-test import finding for these two modules.

### `COMPAT-01` — legacy historical-artifact field is intentionally ignored, with a regression test (confirmed, not a defect)

**Evidence.** `experiments/anchor/contracts.py` documents the external historical-artifact boundary: extra legacy fields are ignored and never trusted.  `tests/integration/anchor/test_anchor_reproduction_pipeline.py` supplies `"baseline": "ignored_legacy_token"` and verifies the locked historical path.  The behavior is a deliberate compatibility boundary, not an active obsolete API accepted by planning/dispatch.

**Caller/downstream chain.** Historical external artifact -> anchor contract parser -> anchor reproduction gate; the legacy token is discarded rather than propagated into a threshold decision or claim.

**Disposition.** Keep the test; it protects the journal-required historical-anchor isolation boundary.

## Findings

### `STALE_API-01` — duplicate `ExperimentSpec` declaration surface is not reachable through the canonical experiment registry

**Status:** confirmed stale/debt; do **not** delete on this evidence alone.

**Contract relevance.** The contract requires all required programmes to have an authoritative, executable responsibility path and cautions that unreachable symbols are not automatically dead.  Multiple declaration authorities make it easier for tests or maintainers to validate the wrong graph.

**Evidence.** `experiments/common/coordinates.py` provides `ExperimentSpec`; the following modules construct named tuples of it:

- `experiments/threshold_robustness/spec.py` (`THRESHOLD_ROBUSTNESS_EXPERIMENTS`)
- `experiments/federated_threshold/spec.py` (`FEDERATED_THRESHOLD_EXPERIMENTS`)
- `experiments/heterogeneity/spec.py` (`HETEROGENEITY_EXPERIMENTS`)
- `experiments/external/spec.py` (`EXTERNAL_EXPERIMENTS`)
- `experiments/applicability/spec.py` (`APPLICABILITY_EXPERIMENTS`)
- `experiments/training_stress/fedprox.py` (`FEDPROX_ABSORPTION_STRESS_TEST`)

No test imports any of the five `*.spec` module groups above, and the production root search instead resolves the canonical `protocols.experiments.EXPERIMENTS`: `app/campaign.py` selects it for execution, `experiments/execution/engine.py` derives its canonical checksum from it, `app/planning.py` consumes its declarations, and `protocols/validation.py` constructs the canonical graph from it.  `pytest --collect-only` sees no direct collection path to the shadow tuples.

**Caller/downstream chain.** CLI/campaign -> `app/campaign.py` -> `protocols.experiments.EXPERIMENTS` -> execution engine/protocol validation.  The duplicate `ExperimentSpec` tuples have no discovered caller from either production or tests.

**Impact.** This is currently a shadow API/documentation debt, not evidence that a required programme is absent: the authoritative registry is live.  It leaves stale declarations untested and could produce divergent maintenance edits or future accidental imports.

**Direction.** Reconcile each tuple with `protocols.experiments.EXPERIMENTS` and identify any non-overlapping responsibility before removal or consolidation.  Add an explicit registry-consistency test if these modules remain.  Do not delete merely from absence of callers, per the contract's audit rule.

### `TEST_ENVIRONMENT-01` — CUDA-sensitive contract coverage is intentionally skipped on CPU-only runners

**Status:** confirmed coverage boundary; conditional CI/release risk, not a defect in the skip implementation.

**Contract relevance.** Training/scoring are frozen-device scientific responsibilities, including deterministic CUDA execution and no CPU fallback.  A successful CPU-only suite does not exercise the CUDA implementation of those requirements.

**Evidence.** `pyproject.toml` always loads `tests.pytest_cuda`.  On `torch.cuda.is_available() == false`, `pytest_collection_modifyitems` skips eight CUDA-only modules plus named tests for runtime device resolution, deterministic setup, CUDA tensor smoke, training, checkpointing, centralized scoring, and fixed-detector provenance.  The focused CLI/architecture collection and full collection succeed, but collection does not establish that a GPU lane executed these tests.

**Caller/downstream chain.** pytest -> `tests.pytest_cuda.py` -> CPU availability decision -> CUDA-marked tests skipped; with CUDA -> tests call runtime/device resolution, training, checkpoint, and score-generation production paths.

**Impact.** If CI/release evidence has no CUDA job, the suite can report green without running the device-specific assertions that protect the locked execution environment.  No source defect follows from the plugin itself; it is narrowly scoped and clearly labelled.

**Direction.** Require/preserve a CUDA CI lane and retain its result as release/audit evidence.  Do not weaken the CPU-only skip, which allows the rest of the deterministic test suite to run.

## Test harness observations

- `tests/unit/app/test_architecture.py` blocks resurrection of retired `datp_core.cli`, `datp_core.reporting`, and `datp_core.pipeline` ownership, restricts Typer imports to `app/cli`, and constrains experiment modules to the application planning owner.  It is a useful negative compatibility guard.
- `tests/unit/app/test_cli.py` covers public help surfaces and the required preprocessing dataset argument.  These 8 focused architecture/CLI tests collect cleanly.
- Full collection exposes scientific, property, integration, e2e, unit, presentation, protocol, and runtime suites; no collection-time stale import or test/production import-cycle failure was found.

## Audit conclusion

No production test-only dependency or harmful live compatibility alias was found.  The actionable maintenance item is the unreachable duplicate `ExperimentSpec` declaration surface (`STALE_API-01`), which should be reconciled—not blindly removed.  GPU-specific assurance remains dependent on an external CUDA execution lane (`TEST_ENVIRONMENT-01`).
