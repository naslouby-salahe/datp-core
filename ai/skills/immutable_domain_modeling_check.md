# Immutable Domain Modeling Check

## Purpose
Keep domain and application objects immutable by construction.

## When to apply
Apply whenever a dataclass, value object, specification, or result type is added or edited in `domain`, `application`, or `analysis`.

## Blocking rules
Block a mutable dataclass in a scientific-identity path, a class missing `frozen=True`/`slots=True`/`kw_only=True` with no recorded reason, and a setter or in-place mutation on a specification or result type.

## Pass criteria
Every domain/application/analysis object carrying scientific identity or configuration state is a frozen, slotted, keyword-only dataclass (or an equivalent immutable construct), constructed once and never mutated.

## Fail criteria
A specification, result, or identity object is mutated after construction, or an object that should be immutable is a plain mutable class for convenience.
