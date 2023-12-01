from flask import Blueprint
from flask import request, jsonify, make_response, current_app
from ws_models import sess, Users
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


    try:
        request_json = request.json
    except Exception as e:
        logger_bp_apple_health.info(e)
        return jsonify({"status": "httpBody data recieved not json not parse-able."})
    
    logger_bp_apple_health.info(f"- ------------------------- -")
    logger_bp_apple_health.info(f"- Count of Apple Health Data: {len(request_json)} -")
    logger_bp_apple_health.info(f"- ------------------------- -")
    
    logger_bp_apple_health.info(f"- request_json: {type(request_json)} -")
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),f"AppleHealth-user_id{current_user.id}-{timestamp}.json")

    with open(json_data_path_and_name, 'w') as file:
        json.dump(request_json, file, indent=4)

    # response_dict = {}

    # for apple_health_entry in request_json:
    #     logger_bp_apple_health.info(f"- request_json key: {apple_health_entry} -")
        # response_dict[key]=value
    
    count_of_entries = len(request_json)

    return jsonify({"Message":"Success! We got the data.", "count_of_entries":count_of_entries })