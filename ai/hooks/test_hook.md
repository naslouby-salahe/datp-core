# Test Hook

## Trigger
After code changes or behavior-affecting config changes.

## Purpose
Run impacted tests and assert order independence; block failing or order-dependent behavior.

## Blocking status
Blocks completion when relevant tests fail, are skipped without reason, or depend on execution order.

## Required checks
- Impacted tests identified.
- Broader tests run only when shared behavior changed or the contract requires them.
- Skipped tests have a clear reason.
- The impacted suite is run twice, in two different random orders (pytest-randomly's default behavior across two invocations), and the results are compared; a test that passes in one order and fails in another is an order-dependence defect, never dismissed as flaky.

## Failure behavior
Fix failures in scope or report the failing command and blocker. Fix an order-dependence defect at its root (shared mutable state, execution-order assumption) rather than pinning a seed to hide it.
