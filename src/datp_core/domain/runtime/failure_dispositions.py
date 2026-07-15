from enum import StrEnum


class FailureDisposition(StrEnum):
    RUN_BLOCKING = "run_blocking"
    STAGE_BLOCKING = "stage_blocking"
    RETRYABLE_TRANSIENT = "retryable_transient"
