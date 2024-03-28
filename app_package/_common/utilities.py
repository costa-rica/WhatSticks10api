from ws_models import sess, engine, text, Users
import logging
from logging.handlers import RotatingFileHandler
import os

# import os
import json
from datetime import datetime
from flask import current_app, request


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



def save_request_data( request_data_to_save,route_path_for_name, user_id, path_to_folder_to_save, custom_logger):
    ## NOTE: This is used just to check and reuse the JSON body
    ## The resulting file of this funtion is not used by any other application and can be deleted.
    
    # Sanitize the path to remove leading slashes and replace remaining slashes with underscores
    # sanitized_path = path.lstrip('/').replace('/', '_')
    sanitized_route_path_for_name = route_path_for_name.lstrip('/').replace('/', '_')
    
    if request_data_to_save.get("dateStringTimeStamp") is not None:
        timestamp = request_data_to_save.get("dateStringTimeStamp")
    else:
        # Get the current timestamp
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    
    # Construct the filename
    filename = f"{sanitized_route_path_for_name}_userID_{user_id}_{timestamp}.json"
    
    # Get the directory from the app's configuration
    # directory = current_app.config.get('APPLE_HEALTH_DIR')
    if not os.path.exists(path_to_folder_to_save):
        os.makedirs(path_to_folder_to_save)  # Create the directory if it doesn't exist
    
    # Full path for the file
    file_path = os.path.join(path_to_folder_to_save, filename)
    
    # Write the request_data_to_save to the file
    with open(file_path, 'w') as file:
        json.dump(request_data_to_save, file)
    
    custom_logger.info(f"Saved data to {file_path}")  # Optional: print confirmation to the terminal

