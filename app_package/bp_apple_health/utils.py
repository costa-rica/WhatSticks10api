from flask import Blueprint
from flask import request, jsonify, make_response, current_app
from ws_models import sess, engine, AppleHealthKit
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
    with open(os.path.join(config.APPLE_HEALTH_DIR, apple_json_data_filename), 'r') as new_user_data_path_and_filename:
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
    count_of_user_apple_health_records = sess.query(AppleHealthKit).filter_by(user_id=user_id).count()
    logger_bp_apple_health.info(f"- count of records in db: {count_of_user_apple_health_records}")
    logger_bp_apple_health.info(f"--- add_apple_health_to_database COMPLETE ---")
    
    response_dict = {
        'message': "Successfully added data!",
        'count_of_entries_sent_by_ios': f"{len(df_new_user_data)}",
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


# # Assuming your dates are in a format like '2023-11-11 10:35:46 +0000'
# def parse_date(date_str):
#     return datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')


# def add_apple_health_to_database(user_id, apple_health_list_of_dictionary_file_name,check_all_bool=False):
#     logger_bp_apple_health.info("- accessed bp_apple_health/utils.py add_apple_health_to_database -")

#     # Load and sort data
#     json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'), apple_health_list_of_dictionary_file_name)
#     with open(json_data_path_and_name, 'r') as file:
#         apple_health_list_of_dictionary_records = json.load(file)
#         # sorted_request_json = sorted(apple_health_list_of_dictionary_records, key=lambda x: x.get('startDate'))
#     count_of_entries_sent_by_ios = len(apple_health_list_of_dictionary_records)
#     sorted_request_json = sorted(apple_health_list_of_dictionary_records, key=lambda x: parse_date(x.get('startDate')), reverse=True)
#     count_of_added_records = 0
#     logger_bp_apple_health.info(f"First record in sorted_request_json (sorted_request_json[0]) : {sorted_request_json[0].get('startDate')}")
#     logger_bp_apple_health.info(f"Last record in sorted_request_json (sorted_request_json[-1]) : {sorted_request_json[-1].get('startDate')}")
#     for i in range(0, len(sorted_request_json)):
#         # batch = sorted_request_json[i:i + batch_size]
#         try:
#             logger_bp_apple_health.info(f"Adding : {sorted_request_json[i].get('startDate')}")
#             if add_entry_to_database(sorted_request_json[i], user_id):
#                 count_of_added_records += 1
#                 sess.commit()  # Commit the transaction for the individual entry
#             # logger_bp_apple_health.info(f"- adding i: {count_of_added_records} -")
#         except IntegrityError as e:
#             sess.rollback()  # Rollback the transaction in case of an IntegrityError
#             logger_bp_apple_health.info(f"IntegrityError encountered in batch: {e}")
#             if check_all_bool:
#                 continue
#             else:
#                 logger_bp_apple_health.info(f"Ended adding data after entry (i): {i}")
#                 break

#     # Final logging and response
#     logger_bp_apple_health.info(f"- count_of_added_records: {count_of_added_records} -")
#     count_of_user_apple_health_records = sess.query(AppleHealthKit).filter_by(user_id=user_id).count()

#     response_dict = {
#         'message': "Successfully added data!",
#         'count_of_entries_sent_by_ios': f"{count_of_entries_sent_by_ios:,}",
#         'count_of_user_apple_health_records': f"{count_of_user_apple_health_records:,}",
#         'count_of_added_records': f"{count_of_added_records:,}"
#     }
#     logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
#     return response_dict


# def add_batch_to_database(batch, user_id):
#     logger_bp_apple_health.info(f"- add_batch_to_database length of batch: {len(batch)} -")
#     new_entries = [AppleHealthKit(
#                 user_id=user_id,
#                 sampleType=entry.get('sampleType'),
#                 startDate = entry.get('startDate'),
#                 endDate = entry.get('endDate'),
#                 metadataAppleHealth = entry.get('metadata'),
#                 sourceName = entry.get('sourceName'),
#                 sourceVersion = entry.get('sourceVersion'),
#                 sourceProductType = entry.get('sourceProductType'),
#                 device = entry.get('device'),
#                 UUID = entry.get('UUID'),
#                 quantity = entry.get('quantity'),
#                 value = entry.get('value')) for entry in batch]  # Construct AppleHealthKit objects
#     sess.bulk_save_objects(new_entries)
#     sess.commit()
#     return len(new_entries)

# def add_entry_to_database(entry, user_id):
#     new_entry = AppleHealthKit(
#                 user_id=user_id,
#                 sampleType=entry.get('sampleType'),
#                 startDate = entry.get('startDate'),
#                 endDate = entry.get('endDate'),
#                 metadataAppleHealth = entry.get('metadata'),
#                 sourceName = entry.get('sourceName'),
#                 sourceVersion = entry.get('sourceVersion'),
#                 sourceProductType = entry.get('sourceProductType'),
#                 device = entry.get('device'),
#                 UUID = entry.get('UUID'),
#                 quantity = entry.get('quantity'),
#                 value = entry.get('value')
#     )
#     sess.add(new_entry)
#     sess.commit()
#     return True


