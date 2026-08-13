# Goal: Full Fresh Audit and Implementation Closure for DATP-Core

Perform a complete fresh audit of DATP-Core against the authoritative roadmap and continuously fix the repository until the implementation matches the roadmap.

Active audit matrix:

`/home/naslouby/Projects/datp-core/docs/DATP Core Audit Matrix.md`

The roadmap referenced by the matrix is the authoritative scientific specification.

The matrix is only the active audit and progress tracker.

Do not stop until the current repository has been audited end to end and every mandatory implementation requirement is truthfully closed.

---

## 1. Reset the Audit First

Before auditing any implementation, reset the active audit state in:

`/home/naslouby/Projects/datp-core/docs/DATP Core Audit Matrix.md`

This is a deliberate full re-audit.

Do not trust previous audit conclusions as current proof.

Reset all implementation and audit statuses so the current repository is audited again from scratch.

Reset:

- `PASS` to `NOT_AUDITED`
- `PARTIAL` to `NOT_AUDITED`
- previous implementation conclusions to unaudited
- previous gate PASS summaries to unaudited
- previous dataset and population PASS statuses to unaudited
- previous evaluation and statistical conclusions to unaudited
- previous reporting and deliverable conclusions to unaudited

Preserve:

- requirement IDs
- roadmap references
- experiment identities
- mandatory versus optional classification
- evidence roles
- scientific scope
- drift sentinels
- numerical-lock lookup information
- claim-survival rules
- typed-unavailability rules
- useful matrix structure and navigation

Do not delete useful historical evidence.

If this file exists:

`/home/naslouby/Projects/datp-core/docs/DATP Core Audit Progress Archive.md`

keep it as historical reference only.

Historical evidence may help locate code, tests, symbols, or previous issues, but it must not automatically restore a PASS.

Every PASS in this new audit must be independently re-established from the current roadmap and current repository.

---

## 2. Read the Entire Authoritative Roadmap

After resetting the audit matrix, identify the authoritative roadmap referenced by the matrix and read it completely from beginning to end.

Do this before making implementation conclusions.

Do not audit from memory.

Do not assume the current matrix is perfectly aligned with the roadmap.

Understand the complete scientific and engineering contract, including:

- scientific programme
- causal comparison
- preprocessing
- fixed-score identity
- calibration
- threshold methods
- threshold variants
- training methods
- datasets
- populations
- experiment programme
- evaluation semantics
- metrics
- statistical analysis
- mechanism analyses
- temporal analysis
- reporting
- claim boundaries
- negative-result handling
- typed unavailability
- provenance
- reproducibility
- release requirements
- Gates A through R
- exclusions and accepted limitations

The roadmap always wins if the roadmap and matrix disagree.

---

## 3. Audit and Adapt the Matrix Itself

Before performing the repository implementation audit, compare the lean matrix against the complete current roadmap.

Surgically update:

`/home/naslouby/Projects/datp-core/docs/DATP Core Audit Matrix.md`

so it accurately covers the current roadmap.

Verify that the matrix includes coherent tracking for all mandatory areas, including:

- scientific programme contracts
- causal isolation
- preprocessing
- fixed-score identity
- calibration
- thresholding
- training
- datasets and populations
- every Part II experiment and analysis
- evaluation
- metrics
- statistics
- terminal-detector rules
- mechanism analysis
- temporal analysis
- figures
- tables
- reporting
- claim-to-evidence rules
- negative evidence
- typed unavailability
- provenance
- reproducibility
- release requirements
- Gates A through R

Add, remove, rename, merge, or split matrix rows when required by the current roadmap.

### Keep the Matrix Lean

Do not recreate the previous enormous audit matrix.

Do not create separate queues for:

- every roadmap sentence
- every formula
- every literal
- every bullet
- prose sentinels
- source-table sentinels
- duplicated experiment cards
- duplicated roadmap content

The roadmap contains scientific detail.

The matrix should track coherent implementation responsibilities and audit state.

Each active matrix row should contain enough information to track:

- requirement or coherent scope
- roadmap owner
- semantic implementation owner
- status
- actual implementation
- runtime caller
- relevant tests
- problems found
- required remediation
- verification evidence

---

## 4. Rebuild the Audit Progress Baseline

Once the matrix has been reconciled with the roadmap, establish a fresh audit baseline.

Everything begins unaudited.

Maintain accurate progress totals for at least:

- total active rows
- PASS
- FAIL
- PARTIAL
- NOT_AUDITED
- NOT_APPLICABLE
- UNAVAILABLE_AS_SPECIFIED
- EVIDENCE_REQUIRED
- OPTIONAL_DEFERRED

Also track progress by major capability:

- scientific contracts
- datasets and populations
- preprocessing
- training
- scoring
- calibration
- thresholding
- experiments
- evaluation
- statistics
- mechanisms
- temporal analysis
- reporting
- provenance and reproducibility
- Gates A through R

Previous audit progress must not count as progress in this fresh audit.

---

## 5. Audit Everything From Scratch

Perform a fresh audit of the entire current repository.

Audit every active matrix area, including everything that was previously marked PASS.

Previous evidence may help navigation, but conclusions must be established again.

For each coherent audit row:

1. Read the complete referenced roadmap section.
2. Determine the intended semantic owner.
3. Search the repository for all relevant implementations.
4. Inspect the implementation itself.
5. Inspect callers.
6. Inspect reverse dependencies.
7. Inspect protocol and configuration declarations.
8. Inspect tests.
9. Inspect serialization and artifact contracts where applicable.
10. Verify runtime reachability.
11. Verify pipeline integration.
12. Compare actual behavior against the roadmap.
13. Record the fresh audit result.
14. Fix every discovered defect.
15. Verify the corrected behavior.
16. Update the matrix immediately.
17. Continue to the next coherent audit area.

Do not mark something PASS merely because:

- a similarly named class exists
- tests exist
- an enum exists
- a dataclass exists
- the previous matrix marked it PASS
- the code compiles
- the API looks reasonable
- a declaration exists

A PASS requires current evidence.

---

## 6. Verify Real Runtime Reachability

For every production scientific requirement, trace the complete execution path:

Roadmap contract  
→ typed protocol or domain identity  
→ semantic implementation owner  
→ pipeline caller  
→ experiment execution path  
→ artifact, evaluation, or analysis output  
→ verification evidence

A requirement is not PASS if it is:

- test-only
- unreachable
- dead
- duplicated
- shadowed
- implemented in the wrong layer
- bypassed by the real pipeline
- configured but never used
- represented only by an enum
- represented only by a dataclass
- implemented differently in competing runtime paths

There must be one active semantic owner for each scientific contract.

---

## 7. Audit Scientific Drift Aggressively

Explicitly search for scientific drift across the repository.

Check for:

- wrong numerical values
- wrong experiment grids
- missing grid cells
- undeclared extra cells
- hidden scientific defaults
- reliance on third-party defaults
- wrong quantile interpolation
- wrong floating-point precision
- wrong `ddof`
- wrong inequality semantics
- incorrect clipping
- incorrect eligibility
- policy-specific retraining
- policy-specific rescoring
- preprocessing refitting
- calibration and evaluation leakage
- attack-labelled threshold construction
- inconsistent score identity
- wrong terminal checkpoint
- wrong client population
- incorrect metric population
- wrong statistical unit
- incorrect pairing
- invalid bootstrap implementation
- invalid Wilcoxon behavior
- incorrect multiplicity correction
- invalid temporal ordering
- unsupported external metrics
- silent missing values
- incorrect typed-unavailability handling
- post-hoc selection
- supportive evidence being promoted to confirmatory evidence
- optional results being used to rescue mandatory results
- unsupported claims

Scientific correctness has higher priority than architectural cleanup.

---

## 8. Audit Every Numerical Lock

The numerical-lock section of the matrix is a lookup aid, not a separate duplicate work queue.

However, during this fresh audit, every locked value must be verified through its owning implementation.

Search for relevant constants and values across the repository.

Verify:

- the value is correct
- it has one semantic owner
- it is not duplicated unnecessarily
- there is no conflicting alternative
- there is no hidden constructor default
- there is no hidden CLI default
- there is no library default silently changing behavior
- the complete grid exists
- canonical and sensitivity values remain distinct
- optional values cannot become canonical after observing results

No magic scientific numbers.

---

## 9. Audit Every Experiment and Analysis

Freshly audit every Part II experiment and analysis.

Do not assume an experiment is implemented merely because its underlying methods exist.

For every experiment verify:

- experiment identity
- evidence role
- population
- training method
- preprocessing identity
- training seed semantics
- nested randomness where applicable
- factor grid
- canonical versus sensitivity conditions
- score reuse
- calibration evidence
- threshold methods
- evaluation population
- metrics
- analysis
- statistical unit
- negative-result path
- typed unavailability
- artifacts
- pipeline wiring
- reporting path
- reconstruction path

Verify the complete coordinate expansion.

Search for:

- missing cells
- duplicate cells
- unauthorized cells
- silently dropped infeasible cells
- incorrect defaults
- post-hoc selectors
- inconsistent identities
- duplicate experiment implementations

Audit optional experiments too.

They remain scientifically optional, but any implementation that exists must still be correct.

---

## 10. Re-Audit Every Dataset and Population

Audit all dataset and population implementations from scratch.

Inspect:

- raw parsing
- canonical schemas
- feature selection
- label handling
- non-finite handling
- provenance
- row identity
- population construction
- client identity
- splits
- chronology
- capabilities
- typed unavailability
- downstream use

### N-BaIoT

Verify:

- exactly the roadmap-defined physical-device semantics
- exactly nine natural-device clients where required
- correct device-family taxonomy
- no invented chronology
- correct confirmatory role
- all physical-device identities remain stable throughout the pipeline

### CICIoT2023

Verify:

- file-defined pseudo-clients only
- no inferred physical devices
- no substitution of the paper's device count for missing artifact provenance
- correct recognized-label and finite-feature eligibility
- no fabricated chronology
- correct applicability-boundary role
- unsupported physical-device claims are impossible

### Edge-IIoTset

Verify:

- correct static client definition
- genuine supported chronology for the temporal population
- correct attack-metric unavailability
- no invented per-client attack assignment
- correct external-validation role
- correct temporal-boundary role

### Controlled N-BaIoT Population

Verify:

- explicitly synthetic identity
- deterministic construction
- source-row identity preservation
- no presentation as natural-device evidence

---

## 11. Audit Architecture and Code Quality

While auditing scientific correctness, also remove architectural drift.

There is no backwards compatibility requirement.

Replace obsolete interfaces at their callers and delete the obsolete implementation.

Remove:

- deprecated APIs
- compatibility shims
- legacy aliases
- redirects
- thin wrappers with no semantic purpose
- duplicate implementations
- dead classes
- dead functions
- dead modules
- unreachable commands
- obsolete tests
- duplicate configuration
- duplicate constants
- unnecessary abstraction layers

Do not retain bad architecture merely because old tests depend on it.

Adapt or replace the tests.

---

## 12. Strong Typing and Domain Modeling

Avoid primitive obsession.

Prefer:

- enums for closed identities and states
- dataclasses for structured domain values
- typed value objects
- typed protocol objects
- explicit configuration objects
- descriptive domain names

Avoid:

- raw string identities
- arbitrary dictionaries as domain contracts
- `Any`
- tuple-heavy interfaces
- magic numbers
- hidden defaults
- stringly typed statuses
- generic parameter names where a domain-specific name is available

Do not introduce opaque aliases or canonical shorthand that requires decoding.

Use descriptive identities directly.

---

## 13. Audit Configuration Ownership

Search carefully for configuration drift.

If a scientific parameter exists in configuration or a typed protocol declaration, implementation code must not silently duplicate another default.

Audit:

- YAML or configuration values
- Python protocol declarations
- dataclass defaults
- constructor defaults
- function defaults
- CLI defaults
- constants
- experiment declarations
- third-party defaults

There must be one semantic source of truth.

Remove duplicated or conflicting hardcoded values.

---

## 14. Preserve One Execution Spine

Scientific execution belongs to the pipeline.

The CLI must remain thin.

Capability packages own scientific semantics.

The pipeline composes those capabilities.

Reporting consumes retained outputs.

Do not introduce or restore:

- Dagster
- a second orchestration framework
- duplicated execution paths
- command-specific scientific logic
- separate implementations of the same experiment

---

## 15. Naming and Comments

Use clear and descriptive names.

Do not add comments referring to:

- the roadmap
- the audit matrix
- implementation phases
- temporary audit fixes
- previous agents
- migration history

Do not add strange AI-generated comments.

Comments should explain only genuinely non-obvious domain or implementation reasoning.

Prefer self-explanatory types and names over comments.

---

## 16. Fix Problems While Auditing

This is not a read-only audit.

Do not first create a giant backlog and postpone all fixes.

Use this loop:

1. Audit one coherent capability or experiment.
2. Identify all problems in that area.
3. Fix them comprehensively.
4. Update all callers.
5. Remove replaced or stale implementations.
6. Adapt or create tests.
7. Verify the capability.
8. Update the matrix.
9. Commit the completed coherent chunk.
10. Move to the next area.

---

## 17. Testing Strategy

Create, adapt, rewrite, and remove tests as needed.

Do not run expensive repository-wide validation after every small edit.

After a substantial coherent chunk:

1. Run the relevant targeted tests.
2. Fix all failures.
3. Run relevant integration tests.
4. Run Ruff.
5. Run formatting validation.
6. Run Pyright or the project's Pylance-compatible static checking.
7. Fix all issues exposed by the chunk.
8. Update the matrix.
9. Commit.

Run broader validation only after major implementation chunks and at final closure.

Tests should run in parallel where supported.

---

## 18. Do Not Run the Scientific Campaign

This task is an implementation and audit task.

Do not execute the complete scientific experiment campaign.

Do not launch the full multi-seed 200-round programme merely to prove that code is wired.

Use:

- source inspection
- unit tests
- property tests
- integration tests
- deterministic fixtures
- planner inspection
- coordinate-expansion validation
- artifact-schema validation
- bounded smoke validation when genuinely necessary
- static checking
- runtime reachability analysis

Campaign-dependent or submission-dependent requirements may legitimately end as:

`EVIDENCE_REQUIRED`

when implementation is correct but the real evidence cannot yet exist.

Never fabricate results.

---

## 19. Freshly Audit Every Gate A Through R

Ignore previous Gate A through R PASS conclusions as current proof.

Audit every detailed gate requirement again once.

For each gate:

1. Read the corresponding roadmap gate requirements.
2. Inspect the current repository.
3. Establish fresh implementation evidence.
4. Record the outcome of every detailed gate requirement.
5. Derive the gate summary from the newly audited detailed checks.

Even a gate that was previously fully PASS must be independently re-audited.

After a gate has been freshly audited during this run, do not repeatedly redo it unless later changes affect its semantic owner.

---

## 20. Historical Evidence Is Navigation Only

Historical evidence may be used to locate:

- files
- symbols
- tests
- previous implementation areas
- previous defects

But never restore PASS directly from history.

The required process is:

Historical evidence  
→ locate current implementation  
→ inspect current implementation  
→ compare with current roadmap  
→ verify runtime reachability  
→ verify current tests and evidence  
→ assign new audit outcome

---

## 21. Audit Priority

Use this priority order:

1. Scientific validity failures
2. Protocol and numerical correctness
3. Dataset and population integrity
4. Split and preprocessing integrity
5. Training and terminal-detector integrity
6. Fixed-score integrity
7. Calibration
8. Threshold implementations
9. Mandatory experiments
10. Evaluation and metrics
11. Statistical analysis
12. Mechanism analysis
13. Temporal analysis
14. Reporting and claim boundaries
15. Provenance and reproducibility
16. Structural cleanup
17. Optional implementation correctness
18. Final Gates A through R closure

Do not prioritize cosmetic cleanup above scientific correctness.

---

## 22. Commit Strategy

Commit after meaningful coherent changes.

Before each commit:

- inspect all changed files
- remove accidental changes
- remove obsolete implementations
- ensure tests appropriate to the chunk pass
- ensure the matrix reflects the current state

Do not create commits after trivial edits.

Use meaningful commit messages describing the completed capability or correction.

---

## 23. When Blocked

Do not stop because one item is difficult.

If blocked:

1. Re-read the relevant roadmap section.
2. Inspect surrounding implementation.
3. Search the repository for reusable functionality.
4. Prefer established libraries over unnecessary custom implementations.
5. Research primary technical or scientific sources when genuinely required.
6. Record the exact blocker in the matrix.
7. Continue with another independent audit area.
8. Return to the blocker later.

Never invent scientific behavior simply to make a requirement pass.

If the roadmap contains a genuine internal contradiction, record the exact conflicting sections and do not silently choose one interpretation.

---

## 24. Keep the Matrix Current

Update the audit matrix continuously.

After each coherent audit and fix chunk, update:

- status
- semantic owner
- actual implementation
- runtime caller
- tests
- verification evidence
- discovered problems
- required remediation
- affected gates

Keep the progress totals accurate.

Do not wait until the end to update the matrix.

---

## 25. Final Bidirectional Audit

After all active areas have been audited and mandatory implementation appears complete, perform two full final audits.

### Roadmap to Repository

For every roadmap requirement, confirm that the required implementation, validation, reporting, or explicit unavailability owner exists.

This catches missing implementation.

### Repository to Roadmap

Inspect the repository for behavior not authorized by the roadmap.

Search for:

- orphan experiments
- extra datasets
- extra threshold methods
- extra training methods
- unauthorized configuration
- hidden scientific defaults
- obsolete identities
- stale aliases
- duplicate semantics
- unsupported claims
- dead scientific paths

This catches unauthorized implementation.

Both directions must close.

---

## 26. Final Validation

Before declaring completion, verify all of the following:

- every active mandatory matrix row received a fresh audit
- every previously PASS area was actually re-audited
- every dataset and population was re-audited
- every mandatory experiment was re-audited
- every evaluation and statistical requirement was re-audited
- every detailed Gate A through R requirement was freshly reviewed
- all discovered scientific drift was fixed or explicitly documented
- no mandatory grid cell is silently missing
- no unauthorized grid cell exists
- no runtime scientific path bypasses its semantic owner
- no required behavior exists only in tests
- no dead or conflicting semantic implementation remains
- no backwards-compatibility layer remains
- no hidden scientific magic value remains
- typed identities replace primitive ambiguity
- configuration ownership is coherent
- targeted and integration tests pass
- broad final tests pass
- Ruff passes
- formatting passes
- Pyright or Pylance-compatible static checking passes
- final runtime reachability audit passes
- roadmap-to-repository audit passes
- repository-to-roadmap audit passes

Campaign or submission evidence may remain `EVIDENCE_REQUIRED` only when the roadmap inherently requires real experiment outputs or submission-time activity.

`EVIDENCE_REQUIRED` must never be used to hide missing implementation.

---

## 27. Completion Condition

Do not stop because:

- the repository was previously audited
- old evidence says PASS
- most tests pass
- most matrix rows are green
- one area is difficult
- the implementation looks mostly complete

The goal is reached only when the current DATP-Core repository has been freshly audited in full against the current authoritative roadmap, every mandatory implementation defect discovered during that audit has been corrected, every required runtime path is correctly wired, every audit row has fresh evidence, every detailed Gate A through R requirement has been reviewed, and the final bidirectional audit finds no remaining scientific or implementation drift.

Continue working until that state is reached.