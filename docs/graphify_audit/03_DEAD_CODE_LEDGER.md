# Dead-code ledger

All entries below have both source/Graphify and journal evidence. No item is classified from reachability alone.

| ID | Severity / disposition | File and symbol | Evidence / final state |
| --- | --- | --- | --- |
| DC-01 | MEDIUM `DELETE_DEAD` | `data/preprocessing/{contracts,fitting,transforms,validation}.py` legacy in-memory preprocessing island | Graphify/source: internal imports only; no production or test caller. Journal needs persisted train-only/skops/reload-validated preprocessing, already owned by `service`, `federated`, `centralized`, `artifact_validation`, `models`, `state`. Delete all four, no behavior/artifact change, no shim. |
| DC-02 | LOW `DELETE_DEAD` | `analysis/mechanisms/__init__.py:heterogeneity_association_from_observations` | No caller except export; direct `heterogeneity_benefit_association` is live in confirmation/heterogeneity paths. Delete wrapper/export; science remains live. |
| DC-03 | LOW `DELETE_DEAD` | `analysis/mechanisms/__init__.py:cluster_mechanism_bundle` | No caller/test. It duplicates the live cluster-evidence/stability collector and misleadingly contains the disconnected dispersion call. Delete after WL-07 is wired at the real owner. |
| DC-04 | MEDIUM `FIX_TEST_ONLY_ARTIFACT` | CIC helpers `reject_physical_device_interpretation`, `reject_family_interpretation` | Unit-test-only; live population declarations/protocol validation enforce the same boundary. Delete helpers and migrate tests to authoritative validation. |
| DC-05 | MEDIUM `FIX_TEST_ONLY_ARTIFACT` | Edge helpers `reject_attack_sensitive_request`, `reject_family_thresholding` | Unit-test-only; live capabilities/protocol validation enforce typed unavailable outcomes/B3 prohibition. Delete helpers and migrate tests. |
| DC-06 | LOW `DELETE_DEAD` | `experiments/registry.py` duplicate catalogue | No source/test importer; live owner is `protocols/experiments.py`. Delete only after checking external consumers are out of scope; no compatibility alias. |

For DC-01–06, current production callers are none (DC-04/05 test-only); callee/superseding ownership is stated above, production reachability is NO, and confidence is CONFIRMED. Detailed evidence, consequences, affected tests/artifacts, and deletion answers are in the corresponding subagent reports.

