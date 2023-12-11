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
    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),f"AppleHealth-user_id{current_user.id}-{timestamp}.json")

    with open(json_data_path_and_name, 'w') as file:
        json.dump(request_json, file, indent=4)
    
    logger_bp_apple_health.info(f"- successfully saved apple health data in: {json_data_path_and_name} -")
    logger_bp_apple_health.info(f"- now working on adding to the what sticks database -")
    
    count_of_entries_sent_by_ios = len(request_json)
    counter_loop_request_json = 0

    unique_identifiers = [(entry.get('UUID'), entry.get('sampleType'), current_user.id) for entry in request_json]
    logger_bp_apple_health.info(f"--------------")
    logger_bp_apple_health.info(f"- unique_identifiers[0:20]: {unique_identifiers[0:20]} -")
    logger_bp_apple_health.info(f"- count of all trying to add (i.e. unique_identifiers): {len(unique_identifiers)} -")

    # Sort the data by startDate
    sorted_request_json = sorted(request_json, key=lambda x: x.get('startDate'))

    # Define batch size
    batch_size = 100  # Adjust this number based on your needs
    total_added_records = 0
    # Process data in batches
    for i in range(0, len(sorted_request_json), batch_size):
        batch = sorted_request_json[i:i + batch_size]
        try:
            added_count = add_batch_to_database(batch, current_user)
            total_added_records += added_count
            logger_bp_apple_health.info(f"- adding batch i: {str(i)} -")
        except IntegrityError:
            # If a batch fails, try adding each entry individually
            logger_bp_apple_health.info(f"- failed to add batch i: {str(i)} -")
            for entry in batch:
                try:
                    if add_entry_to_database(entry, current_user):
                        total_added_records += 1
                except IntegrityError:
                    # Skip the remaining data after encountering a duplicate
                    logger_bp_apple_health.info(f"- failed to add batch i: {str(i)} --> skipping the rest -")
                    break


    logger_bp_apple_health.info(f"- count to be added (i.e. new_entries): {len(new_entries)} -")

    count_of_user_apple_health_records = sess.query(AppleHealthKit).filter_by(user_id=current_user.id).all()

    response_dict = {}
    response_dict['message'] = response_message
    response_dict['count_of_entries_sent_by_ios'] = "{:,}".format(count_of_entries_sent_by_ios)
    response_dict['count_of_user_apple_health_records'] = "{:,}".format(len(count_of_user_apple_health_records))
    response_dict['count_of_added_records'] = "{:,}".format(count_of_added_records)
    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict)


def add_batch_to_database(batch, current_user):
    new_entries = []
    for entry in batch:
        new_entry = AppleHealthKit(
                user_id=current_user.id,
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

def add_entry_to_database(entry, current_user):
    new_entry = AppleHealthKit(
                user_id=current_user.id,
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


# @bp_apple_health.route('/receive_apple_health_data', methods=['POST'])
# @token_required
# def receive_apple_health_data(current_user):
#     logger_bp_apple_health.info(f"- accessed  receive_apple_health_data endpoint-")
#     response_dict = {}
#     try:
#         request_json = request.json
#     except Exception as e:
#         response_dict['error':e]
#         response_dict['status':"httpBody data recieved not json not parse-able."]

#         logger_bp_apple_health.info(e)
#         logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
#         # return jsonify({"status": "httpBody data recieved not json not parse-able."})
#         return jsonify(response_dict)
    

#     logger_bp_apple_health.info(f"- Count of Apple Health Data: {len(request_json)} -")
#     logger_bp_apple_health.info(f"- request_json: {type(request_json)} -")
#     timestamp = datetime.now().strftime('%Y%m%d-%H%M')
#     json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),f"AppleHealth-user_id{current_user.id}-{timestamp}.json")

#     with open(json_data_path_and_name, 'w') as file:
#         json.dump(request_json, file, indent=4)
    
#     count_of_entries_sent_by_ios = len(request_json)
#     counter_loop_request_json = 0

#     unique_identifiers = [(entry.get('UUID'), entry.get('sampleType'), current_user.id) for entry in request_json]
#     logger_bp_apple_health.info(f"--------------")
#     logger_bp_apple_health.info(f"- unique_identifiers[0:20]: {unique_identifiers[0:20]} -")
#     logger_bp_apple_health.info(f"- len(unique_identifiers) -count of all trying to add-: {len(unique_identifiers)} -")

#     existing_records = sess.query(AppleHealthKit.UUID, AppleHealthKit.sampleType, AppleHealthKit.user_id).filter(
#         and_(
#             AppleHealthKit.UUID.in_([uuid for uuid, _, _ in unique_identifiers]),
#             AppleHealthKit.sampleType.in_([sampleType for _, sampleType, _ in unique_identifiers]),
#             AppleHealthKit.user_id == current_user.id
#         )
#     ).all()
#     logger_bp_apple_health.info(f"- len(existing_records: {len(existing_records)} -")
#     existing_identifiers = set(existing_records)

#     new_entries = []
#     for entry in request_json:
#         identifier = (entry.get('UUID'), entry.get('sampleType'), current_user.id)
#         if identifier not in existing_identifiers:
#             new_entry = AppleHealthKit(
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
#             new_entries.append(new_entry)

#     logger_bp_apple_health.info(f"- len(new_entries) -count to be added-: {len(new_entries)} -")

#     try:
#         sess.bulk_save_objects(new_entries)
#         sess.commit()
#         response_message = "Success! We got the data."
#         count_of_added_records = len(new_entries)
#     except IntegrityError as e:
#         sess.rollback()
#         logger_bp_apple_health.error(f"IntegrityError: {e}")
#         response_message = "No data added. Encountered duplicates across user_id, UUID, and sampleType. Let Nick know about this. The problem is with the WSAPI receive_apple_health_data endpoint."
#         count_of_added_records = 0

#     count_of_user_apple_health_records = sess.query(AppleHealthKit).filter_by(user_id=current_user.id).all()

#     response_dict = {}
#     response_dict['message'] = response_message
#     response_dict['count_of_entries_sent_by_ios'] = "{:,}".format(count_of_entries_sent_by_ios)
#     response_dict['count_of_user_apple_health_records'] = "{:,}".format(len(count_of_user_apple_health_records))
#     response_dict['count_of_added_records'] = "{:,}".format(count_of_added_records)
#     logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
#     return jsonify(response_dict)