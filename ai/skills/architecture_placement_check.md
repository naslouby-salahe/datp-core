# Architecture Placement Check

## Purpose
Place every new type in its one correct layer.

## When to apply
Apply whenever a new type, function, or module is added anywhere under `src/datp_core`.

## Blocking rules
Block a type placed in a layer it does not belong to, a type that could plausibly belong to two layers with no tie-breaker recorded, and a type placed by convenience rather than by the layer's actual responsibility.

## Pass criteria
The type's layer follows the ordered placement questions (scientific meaning vs. orchestration vs. configuration vs. reporting vs. framework need vs. wiring vs. entrypoint), and exactly one answer is "yes."

## Fail criteria
Two layers remain plausible with no recorded tie-breaker, or the type is placed in `infrastructure`/`composition` merely because it was easier to write there.
