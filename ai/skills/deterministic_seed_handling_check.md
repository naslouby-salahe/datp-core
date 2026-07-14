# Deterministic Seed Handling Check

## Purpose
Keep seed derivation explicit and reproducible.

## When to apply
Apply whenever a seed, `SeedPlan`, or DataLoader seeding path is added or changed.

## Blocking rules
Block a scattered global seed call outside the approved seed-derivation path, a seed-list position used as an identity, and a seed value invented rather than recorded from an approved source.

## Pass criteria
Every seed derives deterministically from a typed `SeedPlan`/`Seed` value, the derivation is reproducible from tracked configuration, and no seed's identity depends on its position in an unordered collection.

## Fail criteria
A seed is set globally and implicitly, two runs with the same configuration produce different seeds, or a seed's meaning depends on list order.
