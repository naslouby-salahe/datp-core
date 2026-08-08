# Journal implementation matrix

| Roadmap responsibility / role | Actual owner / symbol | Production chain | Status / required action |
| --- | --- | --- | --- |
| Regime A B1-v-B2 confirmatory / confirmatory | `experiments.confirmatory.run` | CLI -> recipe -> seed runner -> execution -> analysis | `LIVE_AND_CORRECT` for frozen scores/paired BCa; B0 reporting WL-01 remains. |
| B0 independent centralized reference / contextual | `experiments.centralized_reference` | campaign only -> train/select/score/evaluate | `SCIENTIFICALLY_DRIFTED`: cache provenance II-03; `DISCONNECTED`: report WL-01. |
| B1/B2/B3/B4 policies / confirmation-mechanism | `thresholds.dispatch`, policies | workspace -> dispatch -> evaluation | `LIVE_AND_CORRECT`; grouped dispersion `DISCONNECTED` WL-07. |
| Cluster fingerprint/K=3/stability / mechanism | cluster policy + `analysis.mechanisms.clustering` | confirmation family route -> analysis | `LIVE_AND_CORRECT` except grouped FPR/threshold dispersion WL-07. |
| Pooled/weighted shared controls / supportive | threshold dispatch + robustness runner | recipe -> robustness run/report | `LIVE_AND_CORRECT`. |
| Quantile/shrinkage/conformal / variants | robustness runner | recipe -> frozen scores -> reports | `LIVE_AND_CORRECT`; size-aware intentionally unavailable until authorized lambda. |
| Calibration-size nested repeats / boundary | calibration protocol + robustness runner | planning/readiness -> runner | `INTENTIONALLY_UNAVAILABLE`: missing prespecified count II-05. |
| B-FedStatsBenign / mandatory comparator | federated statistics variant | dispatch -> evaluation -> N-BaIoT report | `INCOMPLETE` II-01; Edge consumer `DISCONNECTED` WL-05. |
| CIC B-a / applicability boundary | CIC materialize/population + external runner | external recipe -> execution | `LIVE_AND_CORRECT` for pseudo-client boundary; independent B0 `MISSING` WL-06. |
| Regime C Dirichlet / supportive mechanism | heterogeneity run | recipe -> controlled execution -> analysis | `LIVE_AND_CORRECT`; role label needs roadmap reconciliation. |
| Edge D benign equity / external | Edge materialize/population + external run | external recipe -> execution -> B1/B2 report | `LIVE_AND_CORRECT` for allowed outcomes; FedStats analysis `DISCONNECTED` WL-05. |
| D-temporal chronology/recalibration / boundary | Edge chronology + temporal runner | temporal recipe -> split -> run/analyze | `LIVE_AND_CORRECT`; decision criteria `INTENTIONALLY_UNAVAILABLE` II-06. |
| FedProx / training stress | training stress FedProx | recipe -> separate model/scores | `LIVE_AND_CORRECT`. |
| Ditto / personalized stress | training Ditto + stress runner | recipe -> distinct persistent client models | `LIVE_AND_CORRECT`. |
| Checkpoint selection / frozen detector | checkpoints selection | training -> selected terminal round -> scores | `LIVE_AND_CORRECT` for federated; anchor evidence `SCIENTIFICALLY_DRIFTED` II-04. |
| Benign-only calibration/isolation | calibration service + workspace | score artifacts -> threshold -> evaluation | `LIVE_AND_CORRECT` for policy construction; estimator oracle `SCIENTIFICALLY_DRIFTED` II-02. |
| Primary metrics/BCa / confirmatory statistics | metrics/contrasts/bootstrap | evaluations -> analysis -> publication | `LIVE_AND_CORRECT`. |
| Anchor reproduction / anchor | anchor run/reproduction/gate | anchor CLI/campaign -> gate -> analysis handoff | `SCIENTIFICALLY_DRIFTED` II-04; dispatch handoff hardening WL-08. |
| Reporting/publication / all roles | app recipes + presentation | report CLI/campaign -> handlers | `INCOMPLETE`: gate bypass WL-02, completion masking WL-03, B0/Edge gaps. |
| Operational alert burden / supportive | traffic rate protocol | declaration only | `INTENTIONALLY_UNAVAILABLE`, correctly suppressed until evidence II-07. |

Actual files and detailed symbols/callers are listed in the ledgers and subagent reports. No major roadmap responsibility is left unaccounted for.

