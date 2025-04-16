from quickannotator.db import get_session
import logging
import quickannotator.db.models as db_models
from datetime import datetime

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


def init_logger(logger_name) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    handler = SQLAlchemyHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

qa_logger = init_logger("quickannotator")
