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
from app_package.bp_apple_health.utils import add_apple_health_to_database
import subprocess



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



@bp_apple_health.route('/delete_apple_health_for_user', methods=['POST'])
@token_required
def delete_apple_health_for_user(current_user):
    logger_bp_apple_health.info(f"- accessed  delete_apple_health_for_user endpoint-")
    response_dict = {}
    try:
        count_deleted_rows = sess.query(AppleHealthKit).filter_by(user_id = 1).delete()
        sess.commit()
        response_message = f"successfully deleted {count_deleted_rows} records"
    except Exception as e:
        session.rollback()
        logger_bp_apple_health.info(f"failed to delete data, error: {e}")
        response_message = f"failed to delete, error {e} "
        # response = jsonify({"error": str(e)})
        return make_response(jsonify({"error":response_message}), 500)

    response_dict['message'] = response_message
    response_dict['count_deleted_rows'] = "{:,}".format(count_deleted_rows)
    response_dict['count_of_entries'] = "0"

    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict)



@bp_apple_health.route('/receive_apple_health_data', methods=['POST'])
@token_required
def receive_apple_health_data(current_user):
    logger_bp_apple_health.info(f"- accessed  receive_apple_health_data endpoint-")
    response_dict = {}
    try:
        request_json = request.json
    except Exception as e:
        response_dict['error':e]
        response_dict['status':"httpBody data recieved not json not parse-able."]

        logger_bp_apple_health.info(e)
        logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
        # return jsonify({"status": "httpBody data recieved not json not parse-able."})
        return jsonify(response_dict)
    
    logger_bp_apple_health.info(f"- Count of Apple Health Data received: {len(request_json)} -")
    logger_bp_apple_health.info(f"- request_json type: {type(request_json)} -")
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    apple_health_data_request_json_file_name = f"AppleHealth-user_id{current_user.id}-{timestamp}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),apple_health_data_request_json_file_name)

    with open(json_data_path_and_name, 'w') as file:
        json.dump(request_json, file, indent=4)
    
    logger_bp_apple_health.info(f"- successfully saved apple health data in: {json_data_path_and_name} -")


    if len(request_json)< 2000:
        response_dict = add_apple_health_to_database(current_user.id, apple_health_data_request_json_file_name)
    else:
        # send email
        path_sub = os.path.join(current_app.config.get('APPLE_SERVICE_ROOT'), 'add_apple_health_to_database.py')
        subprocess.Popen(['python', path_sub,str(user_id),apple_health_data_request_json_file_name ])

    return jsonify(response_dict)


# def add_batch_to_database(batch, current_user):
#     new_entries = []
#     for entry in batch:
#         new_entry = AppleHealthKit(
#                 user_id=current_user.id,
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
#                 value = entry.get('value'))
#         new_entries.append(new_entry)
#     sess.bulk_save_objects(new_entries)
#     sess.commit()
#     return len(new_entries)  # Return the count of added records

# def add_entry_to_database(entry, current_user):
#     new_entry = AppleHealthKit(
#                 user_id=current_user.id,
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
#     return True  # Return True to indicate one record was added

