# Skill: cuda-safety

## Trigger

Any change to code touching `torch.cuda`, a CUDA-tagged test, or a multiprocessing start method.

## Checks

- CUDA-tagged tests run in the serialized lane only (`uv run pytest -m cuda`); never two concurrent
  CUDA executions on one GPU.
- Multiprocessing uses the approved start method, and no non-picklable object crosses a process
  boundary.
- A CUDA OOM **terminates the current execution attempt**. No silent retry, no automatic batch-size or
  chunk-size reduction, no gradient-accumulation change after stage start.
- No silent fallback from required CUDA execution to CPU.

## Fail conditions

Concurrent CUDA on one GPU, an OOM that triggers retry or batch mutation, a CPU fallback presented as
success, or a non-picklable process-boundary object.

## Output

State which CUDA/execution behavior changed and which determinism checks ran.
