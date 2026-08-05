# Phase 16 — Final Scientific and Engineering Audit

## Authority and scope

`docs/Journal_Extension_Master_Roadmap.md` remains the scientific authority. Phase 16 audits the complete live repository after Phases 12–15, not only files changed during the final pass.

The final architecture is pipeline-first:

- `datp_core.pipeline` is the only execution spine;
- `datp_core.orchestration` is a thin Dagster adapter;
- `datp_core.cli` is a thin Typer adapter;
- `datp_core.reporting` consumes validated pipeline outputs;
- capability packages never import pipeline, orchestration, CLI, or reporting;
- deleted legacy paths, aliases, redirects, wrappers, and duplicate owners must not return.

## Audit passes

### Scientific identity

Verify that every implemented experiment is declared by the scientific programme, descriptive identities are used throughout, centralized reference remains independent, and the sole confirmatory endpoint remains shared versus local threshold calibration on N-BaIoT natural devices using FedAvg and `CV(FPR)`.

### Data, preprocessing, and causal isolation

Verify read-only raw data, reusable canonical and processed data under `data/`, independent centralized and federated preprocessing, complete reuse identities, calibration/evaluation disjointness, benign-only training and calibration, non-test checkpoint selection, fixed detector/checkpoint/scores across threshold comparisons, and no temporal future leakage.

### Dataset capability truth

Verify physical-device semantics only where supported, CIC file-defined pseudo-client boundaries, Edge benign-only external evidence where attack assignment is unavailable, genuine chronology for temporal experiments, and typed infeasibility or unavailability for unsupported cells.

### Models, checkpoints, thresholds, and metrics

Verify FedAvg, FedProx, and genuine Ditto semantics; independent centralized training; SafeTensors checkpoint persistence; exact checkpoint reload; shared/local/family/cluster threshold contracts; grouped-assignment prerequisites; full within/between benign statistics; exact metric definitions; typed undefined metrics; and no fallback-client contamination of confirmatory outcomes.

### Statistics and decisions

Verify ten paired seed contrasts, paired BCa resampling, explicit degenerate-bootstrap outcomes, secondary Wilcoxon and rank-biserial results, within-seed replicate aggregation, predeclared Holm families, and reportability of null, opposite, unstable, infeasible, unavailable, and boundary results.

### Planning, campaigns, and publication

Verify deterministic complete scientific coordinates, duplicate rejection, outcome-independent planning, deterministic campaign ordering, no run/job/resume/timestamp identities, validated reuse, full-coordinate overwrite deletion, deletion and restart of the first incomplete experiment, atomic publication, actual checksum validation, schema and coordinate validation, `COMPLETE` written last, and no reusable data copied under outputs.

### Reporting and extension boundaries

Verify anchor-dependent claim blocking, confirmatory decision discipline, evidence-role separation, Edge and CIC wording restrictions, one-shot temporal wording, privacy and deployment restrictions, traffic-rate requirements, full-precision calculations before presentation, immutable no-op extension hooks, and absence of future attack, defense, online, privacy, or dataset behavior.

### Architecture and repository hygiene

Verify dependency direction, one authoritative owner per concept, no compatibility surface, no `Any`, no project-owned domain/pipeline dictionaries, no numbered threshold identities, no unsafe object serializers, no generated runtime artifacts, no dead legacy tests, and roadmap paths matching final ownership.

## Required verification layers

Use meaningful unit, property, integration, architecture, scientific, and tiny deterministic end-to-end contract tests. Full scientific campaigns are not tests and must not be executed for this pull request.

At minimum, final audit coverage must exercise:

- deterministic planning and campaign ordering;
- complete, incomplete, invalid, and overwrite execution states;
- artifact corruption and reload rejection;
- fixed-detector and benign-only contracts;
- centralized independence;
- unavailable capability outcomes;
- claim suppression and negative-result reporting;
- extension no-op preservation;
- dependency and legacy-path ratchets;
- unsafe persistence and generated-file ratchets.

## Final verdict

Return exactly one repository verdict:

- `GO_FOR_FULL_EXPERIMENTS`;
- `NO_GO_SCIENTIFIC_BLOCKER`;
- `NO_GO_IMPLEMENTATION_DEFECT`;
- `NO_GO_REPRODUCIBILITY_DEFECT`.

`GO_FOR_FULL_EXPERIMENTS` requires all actionable defects discovered by the live audit to be fixed, relevant behavioral tests to pass, deterministic planning to be repeatable, publication reload to be trustworthy, and no unresolved mandatory scientific value to remain.

Formatting, Ruff, Pyright, Pylint, SonarQube, CodeScene, GitHub Actions, hosted CI, and external quality gates are explicitly outside this pull request's audit and completion procedure.
