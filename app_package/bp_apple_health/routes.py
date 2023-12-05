from flask import Blueprint
from flask import request, jsonify, make_response, current_app
from ws_models import sess, Users, AppleHealhKit
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


@bp_apple_health.route('/receive_steps', methods=['POST'])
@token_required
def receive_steps(current_user):
    logger_bp_apple_health.info(f"- accessed  receive_steps endpoint-")
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
    
    logger_bp_apple_health.info(f"- Count of Apple Health Data: {len(request_json)} -")
    logger_bp_apple_health.info(f"- request_json: {type(request_json)} -")
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),f"AppleHealth-user_id{current_user.id}-{timestamp}.json")

    with open(json_data_path_and_name, 'w') as file:
        json.dump(request_json, file, indent=4)
    
    count_of_entries = len(request_json)
    counter_loop_request_json = 0

    unique_identifiers = [(entry.get('UUID'), entry.get('sampleType'), current_user.id) for entry in request_json]
    logger_bp_apple_health.info(f"--------------")
    logger_bp_apple_health.info(f"- unique_identifiers[0:20]: {unique_identifiers[0:20]} -")
    logger_bp_apple_health.info(f"- len(unique_identifiers) -count of all trying to add-: {len(unique_identifiers)} -")
    # existing_records = sess.query(AppleHealhKit.UUID, AppleHealhKit.sampleType).filter(
    #     and_(
    #         AppleHealhKit.UUID.in_([uuid for uuid, _, _ in unique_identifiers]),
    #         AppleHealhKit.sampleType.in_([sampleType for _, sampleType, _ in unique_identifiers]),
    #         AppleHealhKit.user_id == current_user.id
    #     )
    # ).all()
    # logger_bp_apple_health.info(f"- len(existing_records: {len(existing_records)} -")
    # existing_identifiers = set(existing_records)

    existing_records = sess.query(AppleHealhKit.UUID, AppleHealhKit.sampleType, AppleHealhKit.user_id).filter(
        and_(
            AppleHealhKit.UUID.in_([uuid for uuid, _, _ in unique_identifiers]),
            AppleHealhKit.sampleType.in_([sampleType for _, sampleType, _ in unique_identifiers]),
            AppleHealhKit.user_id == current_user.id
        )
    ).all()
    logger_bp_apple_health.info(f"- len(existing_records: {len(existing_records)} -")
    existing_identifiers = set(existing_records)


    new_entries = []
    for entry in request_json:
        identifier = (entry.get('UUID'), entry.get('sampleType'), current_user.id)
        if identifier not in existing_identifiers:
            new_entry = AppleHealhKit(
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
                quantity = entry.get('quantity'))
            new_entries.append(new_entry)

    logger_bp_apple_health.info(f"- len(new_entries) -count to be added-: {len(new_entries)} -")

    sess.bulk_save_objects(new_entries)
    sess.commit()

    try:
        sess.bulk_save_objects(new_entries)
        sess.commit()
        response_message = "Success! We got the data."
    except IntegrityError as e:
        sess.rollback()
        duplicate_entries_count = len(new_entries)
        response_message = "Data partially added. Some entries were duplicates and ignored."





    response_dict = {}
    response_dict['message'] = response_message
    response_dict['count_of_entries'] = "{:,}".format(count_of_entries)
    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict)