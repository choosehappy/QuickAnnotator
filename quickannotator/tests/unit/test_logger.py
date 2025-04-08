import pytest
from quickannotator.db.logging import init_logger
from quickannotator.db.models import Log

def test_init_logger(db_session):
    # Arrange
    logger_name = "test_logger"
    test_message = "This is a test log message."

    # Act
    logger = init_logger(logger_name)
    logger.info(test_message)
    log_entry = db_session.query(Log).filter_by(name=logger_name).first()

    # Assert
    assert log_entry is not None, "Log entry was not created in the database."
    assert log_entry.name == logger_name, f"Expected logger name '{logger_name}', got '{log_entry.name}'."
    assert log_entry.level == "INFO", f"Expected log level 'INFO', got '{log_entry.level}'."
    assert test_message in log_entry.message, f"Expected message '{test_message}', got '{log_entry.message}'."
