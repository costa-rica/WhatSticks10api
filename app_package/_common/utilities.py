from ws_models import sess, engine, text, Users
import logging
from logging.handlers import RotatingFileHandler
import os


def wrap_up_session(custom_logger):
    custom_logger.info("- accessed wrap_up_session -")
    try:
        # perform some database operations
        sess.commit()
        custom_logger.info("- perfomed: sess.commit() -")
    except:
        sess.rollback()  # Roll back the transaction on error
        custom_logger.info("- perfomed: sess.rollback() -")
        raise
    # finally:
    #     sess.close()  # Ensure the session is closed in any case
    #     custom_logger.info("- perfomed: sess.close() -")


def custom_logger(logger_filename):
    """
    Creates and configures a logger with both file and stream handlers, while ensuring
    no duplicate handlers are added.
    :param logger_filename: Filename for the log file.
    :return: Configured logger object.
    """
    path_to_logs = os.path.join(os.environ.get('API_ROOT'), 'logs')
    full_log_path = os.path.join(path_to_logs, logger_filename)

    # Formatter setup
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
    formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

    # Logger setup
    logger = logging.getLogger(logger_filename)  # Use the filename as the logger's name
    logger.setLevel(logging.DEBUG)

    # Avoid adding multiple handlers to the same logger
    if not logger.handlers:  # Check if the logger already has handlers
        # File handler setup
        file_handler = RotatingFileHandler(full_log_path, mode='a', maxBytes=5*1024*1024, backupCount=2)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Stream handler setup
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter_terminal)
        logger.addHandler(stream_handler)

    return logger

