from flask import Blueprint
from flask import request, jsonify, make_response, current_app, g
from ws_models import DatabaseSession, Users, OuraSleepDescriptions, OuraToken
from werkzeug.security import generate_password_hash, check_password_hash #password hashing
import bcrypt
from datetime import datetime
from itsdangerous.url_safe import URLSafeTimedSerializer#new 2023
# import logging
import os
# from logging.handlers import RotatingFileHandler
import json
# import socket
# from app_package.utilsDecorators import token_required
from app_package._common.token_decorator import token_required
import requests
from app_package.bp_oura.utils import add_oura_sleep_to_OuraSleepDescriptions
from app_package._common.utilities import custom_logger, wrap_up_session

logger_bp_oura = custom_logger('bp_oura.log')
bp_oura = Blueprint('bp_oura', __name__)
logger_bp_oura.info(f'- WhatSticks10 API users Bluprints initialized')


@bp_oura.before_request
def before_request():
    logger_bp_oura.info(f"- in def before_request() -")
    # Assign a new session to a global `g` object, accessible during the whole request
    g.db_session = DatabaseSession()
    if request.referrer:
        logger_bp_oura.info(f"- request.referrer: {request.referrer} ")
    
    logger_bp_oura.info(f"- db_session ID: {id(g.db_session)} ")
    
    if request.endpoint:
        logger_bp_oura.info(f"- request.endpoint: {request.endpoint} ")

@bp_oura.route('/add_oura_token', methods=['POST'])
@token_required
def add_oura_token(current_user):
    logger_bp_oura.info(f"- add_oura_token endpoint pinged -")
    db_session = g.db_session
    logger_bp_oura.info(f"current user: {current_user}")
    
    try:
        request_json = request.json
        logger_bp_oura.info(f"request_json: {request_json}")
    except Exception as e:
        logger_bp_oura.info(f"failed to read json, error: {e}")
        response = jsonify({"error": str(e)})
        return make_response(response, 400)

    request_data = request.get_json()
    new_oura_token = request_data.get('oura_token')
    logger_bp_oura.info(f'new_oura_token: {new_oura_token}')
    new_token_record = OuraToken(token=new_oura_token, user_id=current_user.id)
    db_session.add(new_token_record)

    response_dict = {}
    response_dict["message"] = f"Successfully added token for {current_user.email} !"
    return jsonify(response_dict)


@bp_oura.route('/add_oura_sleep_sessions', methods=['POST'])
@token_required
def add_oura_sleep_sessions(current_user):
    logger_bp_oura.info(f"- add_oura_sleep_sessions endpoint pinged -")
    db_session = g.db_session
    response_dict = {}
    # try:
    #     request_json = request.json
    #     logger_bp_oura.info(f"request_json: {request_json}")
    # except Exception as e:
    #     logger_bp_oura.info(f"failed to read json, error: {e}")
    #     response = jsonify({"error": str(e)})
    #     return make_response(response, 400)

    current_date = datetime.now().strftime("%Y%m%d")
    # Construct the file_name_oura_json
    file_name_oura_json = f"oura_sleep-{current_date}-user_id{current_user.id}.json"

    if os.path.exists(os.path.join(current_app.config.get('DIR_DB_AUX_OURA_SLEEP_RESPONSES'),file_name_oura_json)):
        
        logger_bp_oura.info(f"- FOUND file named: {os.path.join(current_app.config.get('DIR_DB_AUX_OURA_SLEEP_RESPONSES'),file_name_oura_json)}")

        with open(os.path.join(current_app.config.get('DIR_DB_AUX_OURA_SLEEP_RESPONSES'),file_name_oura_json), 'r') as file:
            response_oura_sleep = json.load(file)
        
        response_dict = add_oura_sleep_to_OuraSleepDescriptions(current_user.id, current_user.oura_token_id[0].token, response_oura_sleep)
        response_dict['message']= f"Already have Oura download for today  {os.path.join(current_app.config.get('DIR_DB_AUX_OURA_SLEEP_RESPONSES'),file_name_oura_json)} !"
        return jsonify(response_dict)
        
    else:
        logger_bp_oura.info(f"No file named: {os.path.join(current_app.config.get('DIR_DB_AUX_OURA_SLEEP_RESPONSES'),file_name_oura_json)}")
        # get user's token
        OURA_API_TOKEN =  db_session.query(OuraToken).filter_by(user_id=current_user.id).first().token
        # call oura
        response_oura_sleep = requests.get(current_app.config.get('OURA_API_URL_BASE'), headers={"Authorization": "Bearer " + OURA_API_TOKEN})

        # save response to JSON file in DIR_DB_AUX_OURA_SLEEP_RESPONSES with name: oura_sleep-YYYYMMDDHHSS-user_id.json
        with open(os.path.join(current_app.config.get('DIR_DB_AUX_OURA_SLEEP_RESPONSES'),file_name_oura_json), 'w') as file:
            json.dump(response_oura_sleep.json(), file)

        response_dict = add_oura_sleep_to_OuraSleepDescriptions(current_user.id, current_user.oura_token_id[0].token, response_oura_sleep)
        response_dict['message']= f"Successfully saved oura json data  {os.path.join(current_app.config.get('DIR_DB_AUX_OURA_SLEEP_RESPONSES'),file_name_oura_json)} !"
        return jsonify(response_dict)


