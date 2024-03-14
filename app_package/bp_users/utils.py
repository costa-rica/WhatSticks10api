from flask import current_app, url_for
import json
from ws_models import sess, Users, Locations
from flask_mail import Message
from app_package import mail
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
import requests
from datetime import datetime 
from ws_models import sess, UserLocationDay, Locations


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
    
    # Replace 'url_for' with the full external reset URL, appending the token as a query parameter
    base_url = website_url()
    reset_url = f"{base_url}/reset_password?token={token}"
    # match os.environ.get('FLASK_CONFIG_TYPE'):
    #     case 'dev':
    #         reset_url = f"https://dev.what-sticks.com/reset_password?token={token}"
    #     case 'prod':
    #         reset_url = f"https://what-sticks.com/reset_password?token={token}"
    #     case _:
    #         reset_url = f"http://localhost:5000/reset_password?token={token}"
    
    long_f_string = (
        "To reset your password, visit the following link:" +
        f"\n {reset_url} " +
        "\n\n" +
        "If you did not make this request, simply ignore this email and no changes will be made."
    )
    msg.body =long_f_string

    mail.send(msg)

    #     msg.body = f'''To reset your password, visit the following link:
    # {url_for('users.reset_token', token=token, _external=True)}

    # If you did not make this request, ignore email and there will be no change
    # '''
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
    
    # dataframe pickle - apple category & quantity
    user_apple_health_dataframe_pickle_file_name = f"user_{current_user.id:04}_apple_health_dataframe.pkl"
    pickle_data_path_and_name = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_health_dataframe_pickle_file_name)
    if os.path.exists(pickle_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_apple_health_dataframe_pickle_file_name} successfully -")
        os.remove(pickle_data_path_and_name)
    
    # dataframe pickle - apple workouts
    user_apple_health_workouts_dataframe_pickle_file_name = f"user_{current_user.id:04}_apple_workouts_dataframe.pkl"
    pickle_data_path_and_name = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_health_workouts_dataframe_pickle_file_name)
    if os.path.exists(pickle_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_apple_health_workouts_dataframe_pickle_file_name} successfully -")
        os.remove(pickle_data_path_and_name)

    # data source json
    user_data_source_json_file_name = f"data_source_list_for_user_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), user_data_source_json_file_name)
    if os.path.exists(json_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_data_source_json_file_name} successfully -")
        os.remove(json_data_path_and_name)

    # dashboard json
    # user_sleep_dash_json_file_name = f"dt_sleep01_{current_user.id:04}.json"
    user_sleep_dash_json_file_name = f"data_table_objects_array_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DASHBOARD_FILES_DIR'), user_sleep_dash_json_file_name)
    if os.path.exists(json_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_sleep_dash_json_file_name} successfully -")
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
        response_message = f"Successfully deleted {count_deleted_rows} records from {table.__tablename__}"
    except Exception as e:
        sess.rollback()
        error_message = f"Failed to delete data from {table.__tablename__}, error: {e}"
        logger_bp_users.info(error_message)
        error = e
    
    return count_deleted_rows, error


def get_apple_health_count_date(user_id):
    user_apple_qty_cat_dataframe_pickle_file_name = f"user_{int(user_id):04}_apple_health_dataframe.pkl"
    user_apple_workouts_dataframe_pickle_file_name = f"user_{int(user_id):04}_apple_workouts_dataframe.pkl"
    pickle_data_path_and_name_qty_cat = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_qty_cat_dataframe_pickle_file_name)
    pickle_data_path_and_name_workouts = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_workouts_dataframe_pickle_file_name)
    df_apple_qty_cat = pd.read_pickle(pickle_data_path_and_name_qty_cat)
    df_apple_workouts = pd.read_pickle(pickle_data_path_and_name_workouts)

    # get count of qty_cat and workouts
    apple_health_record_count = "{:,}".format(len(df_apple_qty_cat) + len(df_apple_workouts))

    # Convert startDate to datetime
    df_apple_qty_cat['startDate'] = pd.to_datetime(df_apple_qty_cat['startDate'])
    earliest_date_qty_cat = df_apple_qty_cat['startDate'].min()

    df_apple_workouts['startDate'] = pd.to_datetime(df_apple_workouts['startDate'])
    earliest_date_workouts = df_apple_workouts['startDate'].min()
    earliest_date_str = ""
    if earliest_date_workouts < earliest_date_qty_cat:
        # formatted_date_workouts = earliest_date_workouts.strftime('%b %d, %Y')
        # print(f"workouts are older: {formatted_date_workouts}")
        earliest_date_str = earliest_date_workouts.strftime('%b %d, %Y')
    else:
        # formatted_date_qty_cat = earliest_date_qty_cat.strftime('%b %d, %Y')
        # print(f"qty_cat are older: {formatted_date_qty_cat}")
        earliest_date_str = earliest_date_qty_cat.strftime('%b %d, %Y')

    return apple_health_record_count, earliest_date_str

def website_url():
    match os.environ.get('FLASK_CONFIG_TYPE'):
        case 'dev':
            base_url = f"https://dev.what-sticks.com"
        case 'prod':
            base_url = f"https://what-sticks.com"
        case _:
            base_url = f"http://localhost:5000"
    
    return base_url

