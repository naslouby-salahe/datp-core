# Task Contract Creation Check

## Purpose
Confirm a task has a real contract before any edit begins.

## When to apply
Apply at the start of every task, before the first file edit.

## Blocking rules
Block work with no selected contract, a contract missing scope/forbidden-actions/tests/done-criteria, or a contract copied from an unrelated task type.

## Pass criteria
A contract from `ai/contracts/` is selected, its scope and forbidden actions are stated, and its done-criteria are checkable.

## Fail criteria
Work begins with no contract, an incomplete contract, or a contract whose task type does not match the actual work.
