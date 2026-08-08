# Incomplete implementations

| ID | Severity / disposition | File / symbol | Direct evidence and correct final state |
| --- | --- | --- | --- |
| II-01 | HIGH `FIX_INCOMPLETE` | `thresholds/variants/federated_statistics.py:_client_summary` and reporting | B-FedStatsBenign always sets permitted benign exceedance count to `None`, so its byte count omits it and no per-client disclosed communication record is published. Define the locked benign summary, persist n/mean/variance/exceedance and bytes, retain full within+between variance and benign-only inputs. |
| II-02 | HIGH `FIX_SCIENTIFIC_DRIFT` | `experiments/execution/workspace.py:_threshold_estimation_inputs` | Exact pooled threshold-estimation oracle is computed from held-out benign **evaluation** scores. Use eligible calibration scores for the oracle; retain evaluation only for attainment/coverage. |
| II-03 | HIGH `FIX_RUNTIME_BUG` | `detector/training/centralized_publication.py` and centralized scoring reuse | B0 reuse only binds model tensor/maximum round/batch and rebrands stale training provenance from request. Persist/validate manifest with coordinate, model/schema, preprocessing/split/input checksums, candidates; bind score reuse likewise. |
| II-04 | HIGH `FIX_RUNTIME_BUG` | `experiments/anchor/run.py:observation_from_evaluation_document` | Adapter unconditionally labels observations `historical_endpoint`; gate then validates the asserted label, not artifact checkpoint semantics. Carry and validate selection identity/status/checksum from score/evaluation provenance. |
| II-05 | MEDIUM `FIX_INCOMPLETE` | `protocols/calibration.py:require_calibration_subsample_replicate_count` | Intentionally raises until roadmap owner declares deterministic nested replicate count. Do not default it; record immutable protocol value before enabling calibration-size execution. |
| II-06 | MEDIUM `FIX_INCOMPLETE` | `protocols/temporal.py:require_temporal_decision_protocol` | Intentionally raises until positive drift materiality and recovery criteria are predeclared. Do not invent criteria; persist before temporal analysis. |
| II-07 | LOW `FIX_INCOMPLETE` | `protocols/traffic_rates.py` | Alert burden correctly suppressed: no measured/cited rate record. When authority exists, add evidence kind/unit/source/population; otherwise retain suppression. |

II-05–07 are fail-closed journal ambiguities, not defects to bypass. All detailed caller/callee, consequence, test, artifact and confidence evidence appears in the domain/threshold reports.

