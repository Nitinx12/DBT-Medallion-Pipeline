import logging
from pathlib import Path
from unittest.mock import patch


def test_get_logger_creates_handlers(tmp_path):
    """utils.logger.get_logger creates console + file handlers."""
    import utils.logger as logger_mod

    fake_log_dir = tmp_path / "logs"
    # patch LOG_DIR to isolated temp dir so we don't pollute real logs/
    with patch.object(logger_mod, "LOG_DIR", str(fake_log_dir)):
        name = "test_logger_unique"
        # Purge cached logger so we hit creation path
        logging.getLogger(name).handlers.clear()
        # Also clear cached entry in logging manager to force fresh
        if name in logging.Logger.manager.loggerDict:
            del logging.Logger.manager.loggerDict[name]

        log = logger_mod.get_logger(
            name, level=logging.DEBUG, console_level=logging.WARNING
        )

        assert log.name == name
        assert log.level == logging.DEBUG
        assert not log.propagate
        # 2 handlers: console + rotating file
        assert len(log.handlers) == 2
        # file handler points into fake dir
        file_handlers = [h for h in log.handlers if hasattr(h, "baseFilename")]
        assert len(file_handlers) == 1
        assert Path(file_handlers[0].baseFilename).parent == fake_log_dir
        # second call returns same logger without duplicating handlers
        log2 = logger_mod.get_logger(name)
        assert log2 is log
        assert len(log2.handlers) == 2


def test_get_logger_propagate_false_and_levels():
    """Console level override is respected."""
    import utils.logger as logger_mod

    name = "test_logger_levels"
    # Clear previous
    lg = logging.getLogger(name)
    lg.handlers.clear()
    if name in logging.Logger.manager.loggerDict:
        del logging.Logger.manager.loggerDict[name]

    log = logger_mod.get_logger(name, level=logging.INFO, console_level=logging.ERROR)
    console = next(
        h
        for h in log.handlers
        if isinstance(h, logging.StreamHandler) and not hasattr(h, "baseFilename")
    )
    assert console.level == logging.ERROR
