class NVMLError(Exception): ...
class c_nvmlDevice_t: ...  # noqa: N801

class c_nvmlMemory_t:  # noqa: N801
    total: int

def nvmlInit() -> None: ...  # noqa: N802
def nvmlShutdown() -> None: ...  # noqa: N802
def nvmlSystemGetDriverVersion() -> bytes | str: ...  # noqa: N802
def nvmlDeviceGetHandleByIndex(index: int) -> c_nvmlDevice_t: ...  # noqa: N802
def nvmlDeviceGetName(handle: c_nvmlDevice_t) -> bytes | str: ...  # noqa: N802
def nvmlDeviceGetMemoryInfo(handle: c_nvmlDevice_t) -> c_nvmlMemory_t: ...  # noqa: N802
