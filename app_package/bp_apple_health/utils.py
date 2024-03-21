from flask import Blueprint
from flask import request, jsonify, make_response, current_app
from ws_models import session_scope, engine, AppleHealthQuantityCategory
from werkzeug.security import generate_password_hash, check_password_hash #password hashing
import bcrypt
from datetime import datetime
from itsdangerous.url_safe import URLSafeTimedSerializer#new 2023
import logging
import os
from logging.handlers import RotatingFileHandler
import json
# import socket
from app_package.utilsDecorators import token_required
import requests
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from flask_mail import Message
from app_package import mail


formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_bp_apple_health = logging.getLogger(__name__)
logger_bp_apple_health.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','oura.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_bp_apple_health.addHandler(file_handler)
logger_bp_apple_health.addHandler(stream_handler)

bp_apple_health = Blueprint('bp_apple_health', __name__)


def add_apple_health_to_database(user_id, apple_json_data_filename, check_all_bool=False):
    logger_bp_apple_health.info(f"- accessed add_apple_health_to_database for user_id: {user_id} -")
    user_id = int(user_id)

    df_existing_user_data = get_existing_user_data(user_id)

    logger_bp_apple_health.info(f"- df_existing_user_data count : {len(df_existing_user_data)} -")
    logger_bp_apple_health.info(f"- {df_existing_user_data.head(1)} -")
    logger_bp_apple_health.info(f"- ------------------- -")

    # ws_data_folder ="/Users/nick/Documents/_testData/_What_Sticks"
    with open(os.path.join(current_app.config.get('APPLE_HEALTH_DIR'), apple_json_data_filename), 'r') as new_user_data_path_and_filename:
        # apple_json_data = json.load(new_user_data_path_and_filename)
        df_new_user_data = pd.read_json(new_user_data_path_and_filename)

    logger_bp_apple_health.info(f"- df_new_user_data count : {len(df_new_user_data)} -")
    logger_bp_apple_health.info(f"- {df_new_user_data.head(1)} -")
    logger_bp_apple_health.info(f"- ------------------- -")

    # Convert the 'value' column in both dataframes to string
    df_new_user_data['value'] = df_new_user_data['value'].astype(str)
    df_new_user_data['quantity'] = df_new_user_data['quantity'].astype(str)
    # Perform the merge on specific columns
    df_merged = pd.merge(df_new_user_data, df_existing_user_data, 
                        on=['sampleType', 'startDate', 'endDate', 'UUID'], 
                        how='outer', indicator=True)
    # Filter out the rows that are only in df_new_user_data
    df_unique_new_user_data = df_merged[df_merged['_merge'] == 'left_only']
    # Drop columns ending with '_y'
    df_unique_new_user_data = df_unique_new_user_data[df_unique_new_user_data.columns.drop(list(df_unique_new_user_data.filter(regex='_y')))]
    # Filter out the rows that are duplicates (in both dataframes)
    df_duplicates = df_merged[df_merged['_merge'] == 'both']
    # Drop the merge indicator column from both dataframes
    df_unique_new_user_data = df_unique_new_user_data.drop(columns=['_merge'])
    df_duplicates = df_duplicates.drop(columns=['_merge'])
    df_unique_new_user_data['user_id'] = user_id
    # Convert 'user_id' from float to integer and then to string
    df_unique_new_user_data['user_id'] = df_unique_new_user_data['user_id'].astype(int)
    # Drop the 'metadataAppleHealth' and 'time_stamp_utc' columns
    df_unique_new_user_data = df_unique_new_user_data.drop(columns=['metadataAppleHealth'])
    # Fill missing values in 'time_stamp_utc' with the current UTC datetime
    default_date = datetime.utcnow()
    df_unique_new_user_data['time_stamp_utc'] = df_unique_new_user_data['time_stamp_utc'].fillna(default_date)

    rename_dict = {}
    rename_dict['metadata']='metadataAppleHealth'
    rename_dict['sourceName_x']='sourceName'
    rename_dict['value_x']='value'
    rename_dict['device_x']='device'
    rename_dict['sourceProductType_x']='sourceProductType'
    rename_dict['sourceVersion_x']='sourceVersion'
    rename_dict['quantity_x']='quantity'
    df_unique_new_user_data.rename(columns=rename_dict, inplace=True)

    count_of_records_added_to_db = df_unique_new_user_data.to_sql('apple_health_kit', con=engine, if_exists='append', index=False)

    logger_bp_apple_health.info(f"- count_of_records_added_to_db: {count_of_records_added_to_db} -")
    with session_scope() as session:
        count_of_user_apple_health_records = session.query(AppleHealthQuantityCategory).filter_by(user_id=user_id).count()
    logger_bp_apple_health.info(f"- count of records in db: {count_of_user_apple_health_records}")
    logger_bp_apple_health.info(f"--- add_apple_health_to_database COMPLETE ---")
    
    response_dict = {
        'message': "Successfully added data!",
        'count_of_entries_sent_by_ios': f"{len(df_new_user_data):,}",
        'count_of_user_apple_health_records': f"{count_of_user_apple_health_records:,}",
        'count_of_added_records': f"{count_of_records_added_to_db:,}"
    }
    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return response_dict


def get_existing_user_data(user_id):
    try:
        # Define the query using a parameterized statement for safety
        query = """
        SELECT * 
        FROM apple_health_kit 
        WHERE user_id = :user_id;
        """
        # Execute the query and create a DataFrame
        df_existing_user_data = pd.read_sql_query(query, engine, params={'user_id': user_id})
        return df_existing_user_data
    except SQLAlchemyError as e:
        logger_bp_apple_health.info(f"An error occurred: {e}")
        return None


def send_confirm_email(email, count_of_records_added_to_db):
    if os.environ.get('FLASK_CONFIG_TYPE') != 'local':
        logger_bp_apple_health.info(f"-- sending email to {email} --")
        msg = Message('Apple Health Data succesfully added!',
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[email])
        msg.body = f'You have succesfully added {count_of_records_added_to_db} records.'
        mail.send(msg)
        logger_bp_apple_health.info(f"-- email sent --")
    else :
        logger_bp_apple_health.info(f"-- Non prod mode so no email sent --")


def apple_health_qty_cat_json_filename(user_id, timestamp_str):
    return f"{current_app.config.get('APPLE_HEALTH_QUANTITY_CATEGORY_FILENAME_PREFIX')}-user_id{user_id}-{timestamp_str}.json"

def apple_health_workouts_json_filename(user_id, timestamp_str):
    return f"{current_app.config.get('APPLE_HEALTH_WORKOUTS_FILENAME_PREFIX')}-user_id{user_id}-{timestamp_str}.json"
