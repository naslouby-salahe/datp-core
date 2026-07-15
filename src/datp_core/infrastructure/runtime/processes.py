from multiprocessing import get_context
from multiprocessing.context import BaseContext


def cuda_spawn_context() -> BaseContext:
    return get_context("spawn")
