# Configuration Mapping Check

## Purpose
Keep configuration schema-to-domain mapping pure and one-directional.

## When to apply
Apply whenever a `config/schemas/` or `config/mapping/` file is added or edited.

## Blocking rules
Block a mapping function with a side effect, a Pydantic model or raw YAML mapping returned instead of a domain specification, and a mapping function that silently fills a value the schema itself did not validate.

## Pass criteria
Every mapping function has the shape `map_*(schema) -> DomainSpec`, is pure, and every field it produces traces to a validated schema field.

## Fail criteria
A mapping function performs I/O, returns a non-domain type, or invents a default the schema does not declare.
