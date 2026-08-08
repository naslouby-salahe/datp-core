# Wiring ledger

| ID | Severity / disposition | File / symbol | Roadmap responsibility and exact missing edge |
| --- | --- | --- | --- |
| WL-01 | HIGH `WIRE_REQUIRED` | `app/research.py:_run_centralized_reference`; report handlers | B0 is mandatory contextual independent reference. Campaign produces B0 but no report validates/consumes it; direct experiment/report has no B0 dependency. Add a Regime-A B0 report consumer and fail a B0-required package without all independent artifacts. |
| WL-02 | HIGH `WIRE_REQUIRED` | `app/research.py:generate_report` | Anchor-required report handlers skip the general anchor precondition. Enforce `recipe.anchor_requirement` before all dependent report outputs. |
| WL-03 | HIGH `WIRE_REQUIRED` | `app/research.py:run_campaign` | Campaign `COMPLETE` is written before reports; missing mandatory reports are caught/hidden. Publish execution and publication completion separately, only mark scientific package complete after mandatory reports validate. |
| WL-04 | MEDIUM `WIRE_REQUIRED` | `app/recipes.py` optional recipes/campaign loop | Roadmap says group median/optional equity cannot delay mandatory programme; campaign treats them as required. Split mandatory vs optional cohorts. |
| WL-05 | HIGH `WIRE_REQUIRED` | `experiments/external/run.py` Edge analysis | Edge declaration executes B-FedStatsBenign but analysis loads B1/B2 only; add external benign-only FedStats report with estimator, variance, communication and typed-unavailable attack outcomes. |
| WL-06 | HIGH `WIRE_REQUIRED` | CIC declaration/centralized runner | Roadmap permits CIC B0; no CIC independent B0 declaration/runner/report exists. Add independent pooled MinMax B0 route or obtain an authoritative roadmap change. |
| WL-07 | HIGH `WIRE_REQUIRED` | `experiments/confirmatory/run.py:_confirmatory_cluster_mechanisms` | Roadmap requires cluster within/across threshold/FPR dispersion, sizes/singletons. `grouped_dispersion` is renderable/tested but never produced. Construct observations from B4 memberships/evaluations, append evidence to confirmatory analysis. |
| WL-08 | MEDIUM `WIRE_REQUIRED` | `experiments/anchor/gate.py`; `app/research.py:_enforce_anchor_gate` | Full execution checks status only; programme-bound handoff is checked only during final analysis. Make dispatch load and validate verified gate plus handoff. Confidence: HIGH/SUSPECTED boundary timing, not a confirmed false pass. |

All entries are production reachable (WL-06 is missing branch), scientifically required YES except WL-04's optional-cohort routing, and test-only reachable NO. Current callers/callees, artifacts, direct proof and required tests are in subagent reports.

