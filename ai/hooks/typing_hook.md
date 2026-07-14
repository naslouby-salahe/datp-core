# Typing Hook

## Trigger
After code edits that affect protocol state, configs, metrics, or cross-module data.

## Purpose
Require explicit protocol state and enforce the strict-typing gate.

## Blocking status
Blocks completion for protocol-level issues.

## Required checks
- Pyright strict passes with no untyped public surface (the underlying strict-mode configuration is owned by the Pyright/Pylance parity gate; this hook enforces its result).
- No raw protocol strings where `Enum`/`Literal` is appropriate; no hardcoded scientific, status, or policy identifier that belongs in a typed enum.
- No raw protocol dicts, object-shaped dictionaries, `dict[str, Any]`, `Dict[str, Any]`, or untyped `dict` where a typed object is clearer.
- No unjustified `Any`, no unexplained `cast`, no unjustified `type: ignore` (a narrow, explained suppression at a genuine third-party typing gap is not itself a violation; an unexplained one is).
- No tuple-based pseudo-object where a named, typed structure belongs.
- No boolean flag standing in for a discriminated variant, and no variant inferred from which optional fields happen to be set.
- No generic request/result/payload/context object; no incomplete `match`/enum dispatch missing `assert_never` where exhaustiveness is required.
- No duplicated constant defined in more than one place, and no primitive obsession (a bounded or validated quantity represented as a bare `int`/`str`/`float` instead of a value object).
- No hidden default, mutable default, or unexplained broad default.

## Failure behavior
Replace loose state with explicit typed structures or report why the task scope prevents the fix.
