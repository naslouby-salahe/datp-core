# Result Traceability Check

## Purpose
Keep every rendered table or figure traceable to a frozen, provenance-closed result.

## When to apply
Apply whenever a table, figure, or report artifact is rendered or its provenance record is added or changed.

## Blocking rules
Block a render attempted before result-freeze and provenance closure complete, a table or figure sourcing a value only from logs rather than a traced artifact reference, and a `TRACE_REFUSED` result rendered anyway.

## Pass criteria
Every rendered output's `TableProvenance`/`FigureProvenance` resolves to a closed set of frozen source records, with no gap between the rendered value and its traced origin.

## Fail criteria
A render happens before freeze/closure, or a rendered value cannot be traced to a specific frozen artifact reference.
