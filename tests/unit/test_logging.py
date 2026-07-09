import logging

from datp_core.utils.logging import get_logger


def test_logger_can_be_created():
    logger = get_logger("datp_core.test.create")
    assert isinstance(logger, logging.Logger)


def test_duplicate_handlers_are_not_added():
    name = "datp_core.test.duplicate"
    get_logger(name)
    get_logger(name)
    get_logger(name)
    logger = logging.getLogger(name)
    managed = [h for h in logger.handlers if getattr(h, "_datp_core_managed", False)]
    assert len(managed) == 1


def test_run_id_appears_in_formatted_output():
    name = "datp_core.test.run_id"
    logger = get_logger(name, run_id="run-42")
    handler = next(h for h in logger.handlers if getattr(h, "_datp_core_managed", False))
    record = logger.makeRecord(name, logging.INFO, __file__, 0, "hello", (), None)
    for f in handler.filters:
        f.filter(record)
    assert handler.formatter is not None
    formatted = handler.formatter.format(record)
    assert "run-42" in formatted


def test_log_level_comes_from_explicit_argument():
    logger = get_logger("datp_core.test.level_explicit", level=logging.DEBUG)
    assert logger.level == logging.DEBUG


def test_log_level_defaults_to_info():
    logger = get_logger("datp_core.test.level_default")
    assert logger.level == logging.INFO
