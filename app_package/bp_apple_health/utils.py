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

# Assuming your dates are in a format like '2023-11-11 10:35:46 +0000'
def parse_date(date_str):
    return datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')


def add_apple_health_to_database(user_id, apple_health_list_of_dictionary_file_name):
    logger_bp_apple_health.info("- accessed bp_apple_health/utils.py add_apple_health_to_database -")

    # Load and sort data
    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'), apple_health_list_of_dictionary_file_name)
    with open(json_data_path_and_name, 'r') as file:
        apple_health_list_of_dictionary_records = json.load(file)
        # sorted_request_json = sorted(apple_health_list_of_dictionary_records, key=lambda x: x.get('startDate'))
    
    sorted_request_json = sorted(apple_health_list_of_dictionary_records, key=lambda x: parse_date(x.get('startDate')))
    count_of_added_records = 0
    for i in range(0, len(sorted_request_json)):
        # batch = sorted_request_json[i:i + batch_size]
        try:
            if add_entry_to_database(sorted_request_json[i], user_id):
                count_of_added_records += 1
                sess.commit()  # Commit the transaction for the individual entry
            logger_bp_apple_health.info(f"- adding i: {count_of_added_records} -")
        except IntegrityError as e:
            sess.rollback()  # Rollback the transaction in case of an IntegrityError
            logger_bp_apple_health.info(f"IntegrityError encountered in batch: {e}")
            if check_all_bool:
                continue
            else:
                break

    # Final logging and response
    logger_bp_apple_health.info(f"- count_of_added_records: {count_of_added_records} -")
    count_of_user_apple_health_records = sess.query(AppleHealthKit).filter_by(user_id=user_id).count()

    response_dict = {
        'message': "Successfully added data!",
        'count_of_entries_sent_by_ios': f"{count_of_entries_sent_by_ios:,}",
        'count_of_user_apple_health_records': f"{count_of_user_apple_health_records:,}",
        'count_of_added_records': f"{count_of_added_records:,}"
    }
    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return response_dict


def add_batch_to_database(batch, user_id):
    logger_bp_apple_health.info(f"- add_batch_to_database length of batch: {len(batch)} -")
    new_entries = [AppleHealthKit(
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
                value = entry.get('value')) for entry in batch]  # Construct AppleHealthKit objects
    sess.bulk_save_objects(new_entries)
    sess.commit()
    return len(new_entries)

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
    return True


