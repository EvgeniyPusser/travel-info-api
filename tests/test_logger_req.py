import logging

from loggers.logger_req import logger


def test_logger_name_is_app():
    assert logger.name == 'app'


def test_logger_level_is_debug():
    assert logger.level == logging.DEBUG
