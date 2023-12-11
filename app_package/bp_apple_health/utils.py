from flask import Blueprint
from flask import request, jsonify, make_response, current_app
from ws_models import sess, Users, AppleHealthKit
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
# from app_package.bp_apple_health.utils import add_oura_sleep_to_OuraSleepDescriptions
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError



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
logger_bp_apple_health.info(f'- WhatSticks10 API users Bluprints initialized')


def add_apple_health_to_database(user_id,apple_health_list_of_dictionary_file_name):
    logger_bp_apple_health.info(f"- accessed  bp_apple_health/utils.py add_apple_health_to_database() -")

    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),apple_health_list_of_dictionary_file_name)
    with open(json_data_path_and_name, 'r') as file:
        apple_health_list_of_dictionary_records = json.load(file)
    count_of_entries_sent_by_ios = len(apple_health_list_of_dictionary_records)
    counter_loop_request_json = 0

    unique_identifiers = [(entry.get('UUID'), entry.get('sampleType'), user_id) for entry in apple_health_list_of_dictionary_records]
    logger_bp_apple_health.info(f"--------------")
    logger_bp_apple_health.info(f"- unique_identifiers[0:20]: {unique_identifiers[0:20]} -")
    logger_bp_apple_health.info(f"- count of all trying to add (i.e. unique_identifiers): {len(unique_identifiers)} -")

    # Sort the data by startDate
    sorted_request_json = sorted(apple_health_list_of_dictionary_records, key=lambda x: x.get('startDate'))

    # Define batch size
    batch_size = 1000  # Adjust this number based on your needs
    count_of_added_records = 0
    # Process data in batches
    for i in range(0, len(sorted_request_json), batch_size):
        batch = sorted_request_json[i:i + batch_size]
        try:
            added_count = add_batch_to_database(batch, user_id)
            count_of_added_records += added_count
            logger_bp_apple_health.info(f"- adding batch i: {str(i)} -")
        except IntegrityError:
            # If a batch fails, try adding each entry individually
            logger_bp_apple_health.info(f"- failed to add batch i: {str(i)} -")
            for entry in batch:
                try:
                    if add_entry_to_database(entry, user_id):
                        count_of_added_records += 1
                except IntegrityError:
                    # Skip the remaining data after encountering a duplicate
                    logger_bp_apple_health.info(f"- failed to add batch i: {str(i)} --> skipping the rest -")
                    break
        except Exception as e:
            # Catchall exception handling
            logger_bp_apple_health.error(f"An error occurred while processing batch {i}: {e}")
            break


    logger_bp_apple_health.info(f"- count_of_added_records: {count_of_added_records} -")

    count_of_user_apple_health_records = sess.query(AppleHealthKit).filter_by(user_id=current_user.id).all()

    response_dict = {}
    response_dict['message'] = response_message
    response_dict['count_of_entries_sent_by_ios'] = "{:,}".format(count_of_entries_sent_by_ios)
    response_dict['count_of_user_apple_health_records'] = "{:,}".format(len(count_of_user_apple_health_records))
    response_dict['count_of_added_records'] = "{:,}".format(count_of_added_records)
    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return response_dict


def add_batch_to_database(batch, user_id):
    new_entries = []
    for entry in batch:
        new_entry = AppleHealthKit(
                user_id=user_id,
                sampleType=entry.get('sampleType'),
                startDate = entry.get('startDate'),
                endDate = entry.get('endDate'),
                metadataAppleHealth = entry.get('metadata'),
                sourceName = entry.get('sourceName'),
                sourceVersion = entry.get('sourceVersion'),
                sourceProductType = entry.get('sourceProductType'),
                device = entry.get('device'),
                UUID = entry.get('UUID'),
                quantity = entry.get('quantity'),
                value = entry.get('value'))
        new_entries.append(new_entry)
    sess.bulk_save_objects(new_entries)
    sess.commit()
    return len(new_entries)  # Return the count of added records

def add_entry_to_database(entry, user_id):
    new_entry = AppleHealthKit(
                user_id=user_id,
                sampleType=entry.get('sampleType'),
                startDate = entry.get('startDate'),
                endDate = entry.get('endDate'),
                metadataAppleHealth = entry.get('metadata'),
                sourceName = entry.get('sourceName'),
                sourceVersion = entry.get('sourceVersion'),
                sourceProductType = entry.get('sourceProductType'),
                device = entry.get('device'),
                UUID = entry.get('UUID'),
                quantity = entry.get('quantity'),
                value = entry.get('value')
    )
    sess.add(new_entry)
    sess.commit()
    return True  # Return True to indicate one record was added
