# Entrypoints and workflows

## Real production roots

| Root | Actual flow | Result |
| --- | --- | --- |
| `datp-core validate [ID]` | CLI -> `validate_programme` -> canonical protocol graph | validates 5 populations, 23 declarations, 22 registered recipes, 1 suppressed. |
| `datp-core plan [ID]` | CLI -> `build_programme_plan` | creates deterministic coordinate/seed plan. |
| `datp-core preprocess [DATASET]` | CLI -> materializers -> canonical publication | dataset-only assets. |
| `datp-core smoke [ID]` | CLI -> one-seed recipe execution | development smoke, not a scientific evidence root. |
| `datp-core anchor reproduce|verify|status` | anchor CLI -> independent reproduction/gate | historical equivalence gate. |
| `datp-core run experiment ID` | execution CLI -> `run_experiment` -> recipe dispatch | individual programme branch; does not materialize data or B0. |
| `datp-core run campaign` | campaign -> validate -> materialize -> anchor -> B0 -> every recipe -> reports | full programme root. |
| `datp-core report [ID]` | report CLI -> recipe report handler | publication-only root; has gate defects WL-02/03. |
| `datp-core status [ID]` | status CLI -> artifact/marker inspection | reports readiness, not scientific proof. |

Tests, fixtures, `noxfile.py`, and examples are not production roots.

## Journal workflow coverage

All non-suppressed declarations have one recipe. Confirmed routes include Regime A confirmation/family, Regime C controlled heterogeneity, CIC/Edge external, temporal, FedProx, Ditto, threshold robustness and estimation, mechanism analyses, and exploratory supplements. Alert burden is intentionally suppressed because no actual/cited traffic-rate evidence exists. Known workflow divergences are: B0 is not consumed in reports (WL-01); Edge FedStats artifacts are not analyzed (WL-05); CIC B0 has no route (WL-06); and grouped cluster dispersion is not produced (WL-07).

