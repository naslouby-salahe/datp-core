# Architecture and duplication

Confirmed simplification is narrowly bounded: remove the four-module in-memory preprocessing island (DC-01/AD-01) and the dead wrappers/duplicate registry (DC-02–06). No broad factory, protocol, registry, repository, façade, or artifact-publication deletion is recommended. Those boundaries encode client capabilities, fixed-score provenance, atomic/reusable artifacts, or confirmatory-versus-stress roles.

Two duplication risks need a deliberate owner decision:

- **AD-02 / MEDIUM `MERGE_DUPLICATE`:** execution identity declarations are duplicated in `protocols/experiments.py` and `experiments/common/coordinates.py`; runtime uses the latter. Canonicalize one dependency-neutral owner, then migrate tests/imports without a compatibility shim.
- **AD-03 / LOW `SIMPLIFY`:** N-BaIoT execution and preprocessing recompute a split independently. Pass/validate one split handoff/checksum; no current mismatch was demonstrated.
- **AD-04 / LOW `ROADMAP_AMBIGUITY`:** unreachable family `ExperimentSpec` tuples shadow the canonical `protocols.experiments.EXPERIMENTS`. Reconcile each before deletion; tests do not preserve them.

No stale re-export, redirect, or broad compatibility layer was confirmed.

