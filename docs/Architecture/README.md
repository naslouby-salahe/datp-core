# DATP-Core Architectural Package

## Purpose

- Complete, consolidated, implementation-ready architecture specification.
- Derived from the technical architecture and master roadmap.
- A design, not an implementation claim.
- Statements about code, tests, YAML, or repository layout remain
  unverified source material until classified with a status in
  `ENGINEERING_DECISIONS_AND_CONFORMANCE.md §1`.

## Authoritative for

- Package navigation, authority order, and the architecture lifecycle.

## Not authoritative for

- Scientific, domain, configuration, pipeline, metric, or reporting details
  owned by the linked documents.

## Authority order

1. **The DATP-Core master roadmap:** scientific scope, identity, datasets,
   splits, detector/threshold roles, comparators, experiments, evidence,
   claims, metrics, statistics, seeds, eligibility, feasibility,
   suppression, publication placement, and scope boundaries.
2. **This package:** architecture consolidation, naming, type design,
   configuration, pipeline/artifact design, reporting safety, and clean
   replacement.
3. **The technical architecture:** audited requirements and candidate
   decisions; each major concept has a disposition in
   `ENGINEERING_DECISIONS_AND_CONFORMANCE.md`.

- The roadmap wins scientific conflicts.
- Roadmap inconsistencies are recorded as `BLOCKED` with their minimum
  resolving evidence.
- Missing scientific values are never invented; affected configurations are
  blocked from scientific execution.

## DATP-Core

- Names the architecture, configurations, experiments, pipeline, artifacts,
  analyses, reports, and extension mechanisms.
- Never uses publication or version wording as a software-system name.
- Uses manuscript, article, publication evidence, main analysis, or
  supplementary analysis for publication context.

## Anchor

- Reproduces required DATP scientific behavior and acts as a locked
  reproducibility prerequisite, except for source inspection and feasibility
  audits.
- Uses the same resolver, domain model, stages, lifecycle, artifacts,
  persistence, provenance, evaluation, statistics, and reporting as other
  experiments.
- Differs only in scientific definition, evidence role, expected evidence,
  and equivalence condition (`SCIENTIFIC_FOUNDATION.md §2`,
  `PIPELINE_EXECUTION_AND_ARTIFACTS.md §7`).
- Has no separate execution path, planner, persistence, reporting, or
  compatibility layer.

## Package navigation

| File | Answers |
|---|---|
| `SCIENTIFIC_FOUNDATION.md` | What is DATP-Core's complete scientific program, and how does the anchor relate to it? |
| `DOMAIN_AND_APPLICATION_ARCHITECTURE.md` | What are the layers, the compact aggregate model, and the complete public contract catalogue? |
| `CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md` | How is every experiment driven from YAML, with no hidden defaults? |
| `PIPELINE_EXECUTION_AND_ARTIFACTS.md` | How does a stage execute, reuse evidence, persist atomically, and recover? |
| `EVALUATION_REPORTING_AND_PROVENANCE.md` | How is a metric derived, a claim decided, and a report safely rendered? |
| `ENGINEERING_DECISIONS_AND_CONFORMANCE.md` | What was decided, rejected, deferred, or blocked, and how is conformance proven? |

## Document relationships

```mermaid
graph TD
    RM[DATP-Core roadmap] --> SCI[SCIENTIFIC_FOUNDATION]
    SCI --> DOM[DOMAIN_AND_APPLICATION_ARCHITECTURE]
    DOM --> CFG[CONFIGURATION_AND_EXPERIMENT_CATALOGUE]
    SCI --> CFG
    CFG --> PIPE[PIPELINE_EXECUTION_AND_ARTIFACTS]
    DOM --> PIPE
    PIPE --> EVAL[EVALUATION_REPORTING_AND_PROVENANCE]
    SCI --> EVAL
    SCI --> DEC[ENGINEERING_DECISIONS_AND_CONFORMANCE]
    DOM --> DEC
    CFG --> DEC
    PIPE --> DEC
    EVAL --> DEC
```

## How decisions are traced

Every scientific rule, architectural rule, and naming rule in this package
carries a stable identifier from one family: `SCI-*`, `ANCHOR-*`, `NAME-*`,
`ARCH-*`, `TYPE-*`, `CFG-*`, `PIPE-*`, `EXEC-*`, `ART-*`, `EVAL-*`, `STAT-*`,
`REPORT-*`, `PROV-*`, `TEST-*`. Every rule is defined exactly once, in
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §2`; other files reference the
identifier rather than repeat the rule text. That file also carries a
concise source-coverage ledger showing where each major roadmap and prior-
architecture concept landed in this package, and a full disposition table
for every consolidated or removed concept.

## Configuration directories

```text
configs/
├── experiments/     # one document per swept or standalone ExperimentDefinition
├── datasets/          # reusable DataDefinition documents
├── detectors/           # reusable DetectorDefinition and EvaluationDefinition fragments
├── runtime/               # named ExecutionDefinition profiles
└── reporting/               # ReportingDefinition catalogues
```

`detectors/` is the only name used for this directory anywhere in this
package; the prior `protocols/` name is retired
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §1`).

## Canonical CLI

One canonical CLI, `datp-core experiment <action>`, with exactly seven
actions and no scientific override flag
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §21`):

```bash
datp-core experiment list
datp-core experiment validate --config <experiment.yaml>
datp-core experiment resolve --config <experiment.yaml>
datp-core experiment plan --config <experiment.yaml>
datp-core experiment run --config <experiment.yaml>
datp-core experiment status --config <experiment.yaml>
datp-core experiment report --config <experiment.yaml>
```

## Zero-input Make targets

Every regularly executed experiment exposes a discoverable, zero-input
Make target per meaningful action — no `EXPERIMENT=...`, `CONFIG=...`, or
other parameter (`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §23`):

```bash
make help              # lists every supported target and its exact experiment
make experiments        # datp-core experiment list
make anchor-run
make confirmatory-run
make cluster-mechanism-plan
make external-validation-run
make mandatory-run       # the fixed, explicitly listed mandatory sequence
```

## Experiment lifecycle

```text
CLI command or zero-input Make target
  → experiment configuration selection
    → root experiment YAML loading
      → referenced YAML resolution
        → Pydantic boundary validation
          → enum and discriminated-union construction
            → frozen domain dataclass construction
              → cross-document scientific validation
                → resolved-configuration snapshot creation
                  → resolved-configuration fingerprinting and persistence
                    → typed sweep expansion into resolved runs
                      → prerequisite and scientific-readiness checks
                        → stage planning
                          → artifact-reuse decisions
                            → stage execution
                              → evaluation
                                → statistical analysis
                                  → result freeze
                                    → reporting
```

Configuration resolution — everything through fingerprinting and
persistence — is pre-pipeline composition, performed once by
`config/compose.py`; it is never an executable `PipelineStage`
(`CONFIGURATION_AND_EXPERIMENT_CATALOGUE.md §3`,
`PIPELINE_EXECUTION_AND_ARTIFACTS.md §2`).

## Mandatory workflow

`anchor_reproduction` must pass its `AnchorEquivalenceGate` before any
other experiment runs; `confirmatory_threshold_scope_effect` carries this
as a typed `ExperimentPrerequisite`, enforced by the planner, not merely by
Make-target ordering (`SCIENTIFIC_FOUNDATION.md §2`,
`PIPELINE_EXECUTION_AND_ARTIFACTS.md §7`). `make mandatory-run` sequences
the anchor and the confirmatory experiment; every other registered
experiment is independently discoverable through `make experiments` and its
own Make-target family.

## Implementation status

No file, class, dataclass, port, stage, or test named in this package is
asserted to exist, to be implemented, to be tested, or to be passing.
`ENGINEERING_DECISIONS_AND_CONFORMANCE.md §1` defines the six-state status
vocabulary (`LOCKED`, `DESIGNED_NOT_IMPLEMENTED`, `BLOCKED`, `DEFERRED`,
`OUT_OF_SCOPE`, `REJECTED`) every design commitment in this package carries.
