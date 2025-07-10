from quickannotator.db import get_session
import logging
import quickannotator.db.models as db_models
from datetime import datetime
from enum import Enum
import quickannotator.constants as constants
import logging

class SQLAlchemyHandler(logging.Handler):
    def emit(self, record):
        with get_session() as db_session:
            log_entry = db_models.Log(
                name=record.name,
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                message=self.format(record)
            )
            db_session.add(log_entry)

class LoggingManager:

    @staticmethod
    def init_logger(logger_name: str) -> logging.Logger:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = SQLAlchemyHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger


# Example usage
# flask_logger = logging.getLogger(constants.LoggerNames.FLASK.value)
