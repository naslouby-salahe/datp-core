# CUDA Safety Check

## Purpose
Keep CUDA execution serialized, deterministic, and free of unsafe multiprocessing.

## When to apply
Apply whenever code touching `torch.cuda`, a CUDA-tagged test, or a multiprocessing start method is added or changed.

## Blocking rules
Block concurrent CUDA execution on one GPU under any configuration, an incorrect process start method for CUDA work, a non-picklable object crossing a process boundary, and a silent retry after CUDA OOM.

## Pass criteria
CUDA-tagged tests run in the serialized lane only, multiprocessing uses the approved start method, and a CUDA OOM terminates the current execution attempt without silent retry or batch-size mutation.

## Fail criteria
Two CUDA tests run concurrently on the same GPU, a CUDA OOM triggers an automatic retry or batch-size reduction, or a process-boundary object is unpicklable.
