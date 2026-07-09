"""Project logging convention: one managed handler per logger name, no duplicates."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping

LOG_LEVEL_ENV_VAR = "DATP_LOG_LEVEL"
DEFAULT_LOGGER_NAME = "datp_core"
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [%(run_id)s] %(message)s"
_MANAGED_HANDLER_ATTR = "_datp_core_managed"
_RUN_FILTER_ATTR = "_datp_core_run_filter"


class _RunIdFilter(logging.Filter):
    def __init__(self, run_id: str | None = None) -> None:
        super().__init__()
        self.run_id = run_id or "-"

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = self.run_id
        return True


def _level_from_env(env: Mapping[str, str] | None = None) -> int:
    env_map = os.environ if env is None else env
    raw = env_map.get(LOG_LEVEL_ENV_VAR, "INFO").upper()
    return getattr(logging, raw, logging.INFO)


def get_logger(
    name: str = DEFAULT_LOGGER_NAME,
    *,
    level: int | None = None,
    run_id: str | None = None,
) -> logging.Logger:
    """Return a logger with exactly one managed stream handler for ``name``.

    Calling this repeatedly for the same name never adds a second handler; a
    new ``run_id`` updates the existing handler's filter in place.
    """
    logger = logging.getLogger(name)
    managed_handler = next((h for h in logger.handlers if getattr(h, _MANAGED_HANDLER_ATTR, False)), None)

    if managed_handler is None:
        managed_handler = logging.StreamHandler()
        managed_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        setattr(managed_handler, _MANAGED_HANDLER_ATTR, True)
        run_filter = _RunIdFilter(run_id)
        managed_handler.addFilter(run_filter)
        setattr(managed_handler, _RUN_FILTER_ATTR, run_filter)
        logger.addHandler(managed_handler)
        logger.propagate = False
    elif run_id is not None:
        getattr(managed_handler, _RUN_FILTER_ATTR).run_id = run_id

    logger.setLevel(level if level is not None else _level_from_env())
    return logger
