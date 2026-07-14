# Changelog

## Phase 0 — Repository and Engineering Foundation (2026-07-14)

Phase 0, the repository and engineering foundation phase, is complete. The repository
now has a Python 3.12 project with pinned scientific dependencies and a committed lock, an empty seven-layer
`src/datp_core/` skeleton, a tracked/generated root layout, a full tooling stack (Ruff,
Pyright strict, pytest with coverage/timeout/order-randomization, Hypothesis,
import-linter, pytest-archon, syrupy, Nox), a serialized CUDA lane and CPU xdist policy,
a complete AI governance catalogue (agents, skills, contracts, workflows, commands, and
their thin provider adapters), a full blocking-hook suite, a Sonar project configuration
with an explicit quality gate, and a CodeScene project configuration with its own
explicit Code Health delta-analysis quality gate.

`src/datp_core/` remains an empty architectural skeleton with no scientific behavior, as
required for this phase. No Phase 1 domain, application, or infrastructure behavior was
introduced.

The composed baseline gate (Ruff, Pyright strict, import-linter, pytest-archon, every
Nox validation session, a live Sonar analysis, and a live CodeScene delta analysis)
passes green on a freshly rebuilt environment resolved strictly from the committed
dependency lock: the Sonar analysis found zero issues across the current tree once an
operator authenticated, and the CodeScene analysis found zero remaining Code Health
findings once a genuine code-duplication finding it surfaced in the Nox session
definitions was fixed. The connected SonarCloud project separately carries pre-existing
open issues referencing files absent from this repository; those predate this phase's
rebuild and are not part of it.
