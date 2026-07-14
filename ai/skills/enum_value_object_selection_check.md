# Enum, Value-Object, and Dataclass Selection Check

## Purpose
Choose the correct typed construct for a given piece of scientific or protocol state.

## When to apply
Apply whenever a new field, parameter, or return value needs a type decision.

## Blocking rules
Block a raw string standing in for a closed set of values, a boolean flag standing in for a discriminated variant, an optional-field combination used to infer a variant, and a tuple used as a pseudo-object.

## Pass criteria
A closed set of named values is a `StrEnum`; a bounded, validated quantity is a value object; a bundle of related fields with identity is a frozen dataclass; a discriminated variant is a tagged union or `match`-dispatched type, never a boolean or optional-field combination.

## Fail criteria
A closed set is represented as a bare string, a variant is inferred from which optional fields are set, or a tuple carries positionally-meaningful fields that should be named.
