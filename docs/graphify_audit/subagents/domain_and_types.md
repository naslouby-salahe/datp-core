# Domain, protocol, type, registry, and re-export audit

Scope: `src/datp_core/core`, `src/datp_core/protocols`,
`src/datp_core/data/registry.py`, `src/datp_core/experiments/registry.py`, and
the public package initializers.  This is a read-only structural audit; no
production code was changed.

## Method and evidence

- Read `docs/graphify_audit/00_JOURNAL_CONTRACT.md` and the complete master
  roadmap before classifying reachability.
- Used the existing WSL Graphify installation and current
  `graphify-out/graph.json`, then verified candidates with repository-wide
  `rg` searches.  Graphify confirms the core/protocol graph is connected to
  the experiment, training, analysis, and application layers; reachability
  conclusions below are based on direct source-import evidence as well.
- `uv run pyright src/datp_core/core src/datp_core/protocols
  src/datp_core/data/registry.py src/datp_core/experiments/registry.py`:
  **0 errors, 0 warnings, 0 informations**.
- `uv run ruff check` over the same domain/protocol/registry scope: **passed**.
- `uv run pytest -q tests/unit/domain tests/unit/protocols
  tests/unit/datasets/test_registry.py tests/unit/thresholding/test_dispatch.py`:
  **113 passed**.

`Production` below means an import/use under `src/`; `test-only` explicitly
means no production use was found.  A test-only reference does not make a
duplicate production code.

## Findings and dispositions

| ID | Evidence | Scientific disposition | Required action |
| --- | --- | --- | --- |
| DT-1 | `src/datp_core/experiments/registry.py` has no production or test import (`rg datp_core.experiments.registry` found none).  Its body is an exact duplicate of `src/datp_core/protocols/experiments.py` except for that module's relative metrics import. | **DELETE** the unused duplicate.  The live catalogue is `protocols/experiments.py`: it is imported by campaign planning, all experiment runners, the execution engine, protocol validation, and e2e tests.  Removing the duplicate does not remove a journal responsibility. | Delete `src/datp_core/experiments/registry.py`; add a regression/import-boundary test if the old path was ever intended to be public. |
| DT-2 | `ExecutionIdentityDeclaration`, `EXECUTION_IDENTITY_DECLARATIONS`, `ExternalTemporalExecutionIdentity`, and `require_execution_identity` occur independently in `protocols/experiments.py` and `experiments/common/coordinates.py`; the latter is the production runtime owner (preparation, preprocessing, scoring, population publication, and execution imports).  The protocol copy is not imported by production consumers; protocol unit tests only exercise it. | **FIX / CONSOLIDATE**, not delete semantics.  The bounded external/temporal identity guard is required by the roadmap (CIC file-client boundary, Edge static external validation, and three Edge temporal states).  Two independent definition sites can silently drift and invalidate those guards. | Choose one owner.  Prefer `experiments/common/coordinates.py` for the runtime identity and have `protocols/experiments.py` re-export it (or move the canonical definition into a dependency-neutral protocol module and import it from coordinates).  Update protocol tests to exercise the canonical object. |
| DT-3 | `require_calibration_subsample_replicate_count()` in `protocols/calibration.py:255` always raises `UnresolvedScientificValueError`; it is reached by campaign planning, threshold construction, and threshold-robustness execution. | **WIRE_REQUIRED / FIX_INCOMPLETE — do not delete or default.**  The roadmap requires multiple deterministic calibration subsampling replicates nested within seed, but provides no count.  This fail-closed behavior prevents pseudoreplication and is scientifically correct until a value is authorized. | Obtain and record a pre-specified `SubsampleReplicateCount`; replace the raising placeholder with the declared immutable protocol value; persist it in the calibration-size artifacts and retain the within-seed aggregation guard. |
| DT-4 | `require_temporal_decision_protocol()` in `protocols/temporal.py:166` always raises `UnresolvedScientificValueError`; temporal campaign analysis calls it.  `TemporalDecisionProtocol` already identifies the two missing fields. | **WIRE_REQUIRED / FIX_INCOMPLETE — do not delete or invent values.**  The roadmap mandates a positive drift-excess materiality threshold and a meaningful-recovery criterion before analysis; `recovery_ratio` must remain typed undefined when the former is not met. | Obtain and persist `drift_excess_materiality_threshold` and `material_recovery_ratio_minimum`, then instantiate the protocol.  Preserve the existing multi-seed/provenance/uncertainty validations. |
| DT-5 | `TrafficRateEvidence` (`protocols/traffic_rates.py`) has only `population`, `rate_per_day`, and a primitive `source_locator: str`; `TRAFFIC_RATE_EVIDENCE` is empty.  Protocol validation suppresses the alert-burden declaration and the roadmap forbids invented rates.  `TrafficRateEvidenceType` exists separately in analysis but is not represented in the protocol declaration. | **WIRE_REQUIRED, intentionally suppressed.**  Alert burden is a supportive operational translation only; it must not become executable without actual/cited rate provenance.  This is not dead code. | When evidence exists, add an immutable record with a non-empty typed/canonical locator plus evidence kind (`measured`, `dataset-derived`, or `externally-cited`), units and population binding; then allow only the relevant population's alert-burden experiment.  Until then retain `SUPPRESSED` and omit the metric. |
| DT-6 | `CentralizedQuantileProtocol`, shared/local/pooled `QuantileProtocol` constants, `SizeAwareShrinkageProtocol`, and `ConformalProtocol` declarations are mostly construction templates/tests; federated dispatch deliberately reconstructs the selected quantile protocol from each request so q-sensitivity can vary without changing B1 identity.  In contrast, canonical eligibility, size, shrinkage, cluster-median, and benign-statistics protocols have production consumers. | **KEEP; no deletion based on static direct-call counts.**  The required B1/B2/B3/B4 and variants need typed declarations and a variable q path.  However, there is an auditability gap: some declared canonical protocol objects are not the values passed to execution. | Add a request/artifact field carrying a checksum or serialized declared protocol identity (including q and method) rather than relying solely on reconstructed equivalent objects.  Do not wire a static q=.95 object into q-sensitivity runs. |
| DT-7 | `DatasetBinding` and `PopulationBinding` in `data/registry.py` are runtime-used by materialization, preparation, training, execution workspace, and campaign planning.  The five bindings exactly cover the locked populations; `construct_population` rejects undeclared/default controlled partitions and the Dirichlet binding requires an explicit condition. | **KEEP.**  This registry enforces the programme's client-population and evidence-role boundaries; it is not a convenience registry or type-level dead code. | Retain closed bindings.  If a new population is proposed, require a roadmap change and matching capabilities/declaration/validation update—not an ad-hoc registry entry. |
| DT-8 | Package `__init__.py` files are intentionally sparse except selected experiment/analysis façade modules.  `datp_core/__init__.py` exports only the version; `core`, `protocols`, `data`, detector package roots do not re-export domain types.  The populated facades (`analysis`, `analysis/mechanisms`, `detector/training/models`, and runnable experiment families) expose direct implementations that exist and are used. | **KEEP sparse roots; no broad re-export cleanup.**  There is no stale root-level alias found.  Broad re-exports would make provenance and ownership less explicit. | Preserve explicit import paths.  If DT-2 is consolidated by re-export, make that one compatibility re-export narrow and tested. |
| DT-9 | Core value objects and closed identities are production-used across artifacts, data, preprocessing, training, scoring, thresholding, analysis, and CLI.  The checked exceptions are also production-raised/caught (including `UnknownIdentifierError`, `MissingPrerequisiteError`, and `ReportEvidenceError`).  `CalibrationSampleWeights`, `AbsoluteThresholdError`, `RelativeThresholdError`, source/validation counts, and `BootstrapReplicateCount` all have production users; some also have unit-only coverage. | **KEEP.**  No supported core value object or error type met the positive deletion standard. | No action.  Continue to add domain values only for meaningfully distinct units/invariants, not as wrappers around temporary local arithmetic. |

## Primitive-leak assessment

The main scientific values are already typed: seeds, counts, q, ratios,
thresholds, score values, metric values, model coefficients, partition roles,
dataset/population/experiment identities, and availability statuses.  The
following primitive fields are localized infrastructure/provenance boundaries,
not evidence that numeric scientific semantics are leaking:

- `protocols/training.py` uses `branch_label: str` only to build an error
  message after the typed selection rule and typed held-out/attack checks.
- `core/contracts.py` and `core/numeric.py` necessarily accept Python scalar
  values at Pydantic/value-object construction boundaries and immediately
  validate/wrap them.
- `DatasetBinding.publish: Callable[[Path, Path], ...]` is filesystem wiring.

The actionable exception is DT-5: a traffic-rate citation has scientific
provenance meaning and should be typed/structured before the suppressed
operational programme is enabled.

## Required scientific fields still absent from the live contract

These must be added by an authorized protocol decision, not inferred during
implementation:

1. `SubsampleReplicateCount` for the deterministic calibration-size nested
   repeats (DT-3).
2. Positive temporal `drift_excess_materiality_threshold` and
   `material_recovery_ratio_minimum` (DT-4).
3. For any alert-rate evidence: value, per-day unit, evidence kind, canonical
   source locator, and bound population (DT-5).

All three omissions are deliberately fail-closed.  They are journal-required
responsibilities and therefore **not** candidates for dead-code deletion.

## Overall conclusion

The domain layer is strongly typed and the live dataset registry correctly
enforces the scientific population boundaries.  The one confirmed deletable
unit is the unreferenced duplicate `experiments/registry.py`.  The higher-risk
structural issue is duplicated execution-identity declarations: consolidate
them before changing either copy.  The remaining unreachable paths are
explicit fail-closed markers for undeclared scientific constants and must stay
blocked until the missing values are pre-specified.
