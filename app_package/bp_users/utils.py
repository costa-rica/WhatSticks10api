from flask import current_app, url_for
import json
from ws_models import sess, Users
from flask_mail import Message
from app_package import mail
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_bp_users = logging.getLogger(__name__)
logger_bp_users.setLevel(logging.DEBUG)


#where do we store logging information
file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),"logs",'users_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_bp_users.addHandler(file_handler)
logger_bp_users.addHandler(stream_handler)


def send_reset_email(user):
    token = user.get_reset_token()
    logger_bp_users.info(f"current_app.config.get(MAIL_USERNAME): {current_app.config.get('MAIL_USERNAME')}")
    msg = Message('Password Reset Request',
                  sender=current_app.config.get('MAIL_USERNAME'),
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request, ignore email and there will be no change
'''
    mail.send(msg)


def send_confirm_email(email):
    if os.environ.get('FLASK_CONFIG_TYPE') != 'local':
        logger_bp_users.info(f"-- sending email to {email} --")
        msg = Message('Welcome to What Sticks!',
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[email])
        msg.body = 'You have succesfully been registered to What Sticks.'
        mail.send(msg)
        logger_bp_users.info(f"-- email sent --")
    else :
        logger_bp_users.info(f"-- Non prod mode so no email sent --")


def delete_user_data_files(current_user):
    
    # dataframe pickle
    user_apple_health_dataframe_pickle_file_name = f"user_{current_user.id:04}_apple_health_dataframe.pkl"
    pickle_data_path_and_name = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_health_dataframe_pickle_file_name)
    if os.path.exists(pickle_data_path_and_name):
        os.remove(pickle_data_path_and_name)

    # data source json
    user_data_source_json_file_name = f"data_source_list_for_user_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), user_data_source_json_file_name)
    if os.path.exists(json_data_path_and_name):
        os.remove(json_data_path_and_name)

    # dashboard json
    user_sleep_dash_json_file_name = f"dt_sleep01_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DASHBOARD_FILES_DIR'), user_sleep_dash_json_file_name)
    if os.path.exists(json_data_path_and_name):
        os.remove(json_data_path_and_name)

def delete_user_from_table(current_user, table):
    count_deleted_rows = 0
    error = None
    try:
        if table.__tablename__ != "users":
            count_deleted_rows = sess.query(table).filter_by(user_id = current_user.id).delete()
        else:
            count_deleted_rows = sess.query(table).filter_by(id = current_user.id).delete()
        sess.commit()
        response_message = f"successfully deleted {count_deleted_rows} records"
    except Exception as e:
        sess.rollback()
        error_message = f"Failed to delete data from {table.__tablename__}, error: {e}"
        logger_bp_users.info(error_message)
        error = e
    
    return count_deleted_rows, error