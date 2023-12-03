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

    # for entry in json_data2[0:20]:
    for entry in request_json:
            # Check if a record with the same user_id, UUID, and sampleType already exists
        exists = sess.query(AppleHealhKit).filter_by(
            user_id=1, 
            UUID=entry.get('UUID'), 
            sampleType=entry.get('sampleType')
        ).first() is not None

        if not exists:
        
            new_entry = AppleHealhKit(user_id = 1,
                sampleType = entry.get('sampleType'),
                startDate = entry.get('startDate'),
                endDate = entry.get('endDate'),
                metadataAppleHealth = entry.get('metadata'),
                sourceName = entry.get('sourceName'),
                sourceVersion = entry.get('sourceVersion'),
                sourceProductType = entry.get('sourceProductType'),
                device = entry.get('device'),
                UUID = entry.get('UUID'),
                quantity = entry.get('quantity'))
            sess.add(new_entry)
            sess.commit()
            if counter_loop_request_json < 3:
                logger_bp_apple_health.info(f"UUID {entry.get('UUID')} Added ****")
        else:
            if counter_loop_request_json < 3:
                logger_bp_apple_health.info(f"UUID {entry.get('UUID')} already exists")
        
        counter_loop_request_json += 1

    response_dict = {}
    response_dict['Message'] = "Success! We got the data."
    response_dict['count_of_entries'] = "{:,}".format(count_of_entries)
    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict)