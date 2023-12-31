from flask import Blueprint
from flask import request, jsonify, make_response, current_app
from ws_models import sess, Users, AppleHealthQuantityCategory, AppleHealthWorkout
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
from app_package.bp_apple_health.utils import add_apple_health_to_database, \
    send_confirm_email, apple_health_qty_cat_json_filename, apple_health_workouts_json_filename
from app_package.bp_users.utils import delete_user_data_files, delete_user_from_table
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

    deleted_records = 0

    delete_apple_health = delete_user_from_table(current_user, AppleHealthQuantityCategory)
    delete_apple_health = delete_user_from_table(current_user, AppleHealthWorkout)
    if delete_apple_health[1]:
        response_message = f"failed to delete, error {delete_apple_health[1]} "
        return make_response(jsonify({"error":response_message}), 500)
    
    count_deleted_rows = delete_apple_health[0]


    # delete: dataframe pickle, data source json, and dashboard json
    delete_user_data_files(current_user)

    response_dict = {}
    response_dict['message'] = "successfully deleted apple health data."
    response_dict['count_deleted_rows'] = "{:,}".format(count_deleted_rows)
    response_dict['count_of_entries'] = "0"

    logger_bp_apple_health.info(f"- response_dict: {response_dict} -")
    return jsonify(response_dict)


@bp_apple_health.route('/receive_apple_qty_cat_data', methods=['POST'])
@token_required
def receive_apple_qty_cat_data(current_user):
    logger_bp_apple_health.info(f"- accessed  receive_apple_qty_cat_data endpoint-")
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
    

    # last chunk
    last_chunk = request_json.get("last_chunk") == "True"
    # filename example: AppleHealthQuantityCategory-user_id1-20231229-1612.json
    # let filename = "AppleHealthQuantityCategory-user_id\(userId)-\(dateStringTimeStamp).json"
    # apple_health_data_request_json_file_name = request_json.get("filename")
    # apple_health_data_request_json_file_name = request_json.get("dateStringTimeStamp")
    time_stamp_str_for_json_file_name = request_json.get("dateStringTimeStamp")
    apple_health_data_json = request_json.get("arryAppleHealthQuantityCategory")
    count_of_entries_sent_by_ios = len(apple_health_data_json)

    # timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    # apple_health_data_request_json_file_name = f"AppleHealth-user_id{current_user.id}-{timestamp}.json"
    # apple_health_data_request_json_file_name = f"{current_app.config.get('APPLE_HEALTH_QUANTITY_CATEGORY_FILENAME_PREFIX')}-user_id{current_user.id}-{time_stamp_str_for_apple_health_data_request_json_file_name}.json"
    apple_health_workouts_json_filename_str = apple_health_workouts_json_filename(current_user.id, time_stamp_str_for_json_file_name)
    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),apple_health_workouts_json_filename_str)

    logger_bp_apple_health.info(f"- count_of_entries_sent_by_ios (this time): {count_of_entries_sent_by_ios} -")

    new_data_dict = {}

    # Create .json file 
    if os.path.exists(json_data_path_and_name):

        with open(json_data_path_and_name, 'r') as data_to_add:
            existing_data_to_add_from_same_call = json.load(data_to_add)
            # df_new_user_data = pd.read_json(new_user_data_path_and_filename)

        new_data_dict = existing_data_to_add_from_same_call + apple_health_data_json
        count_of_entries_sent_by_ios = len(new_data_dict)
        with open(json_data_path_and_name, 'w') as file:
            json.dump(new_data_dict, file, indent=4)

    else:
        with open(json_data_path_and_name, 'w') as file:
            json.dump(apple_health_data_json, file, indent=4)


    # Check for last chunk
    if not last_chunk:
        # create reponse for WSiOS that it knows to keep going with chunks
        response_dict = {"chunk_response":"keep going"}
        return jsonify(response_dict)
    else:
        logger_bp_apple_health.info(f"- successfully saved apple health data in: {json_data_path_and_name} -")
        user_id_string = str(current_user.id)
        logger_bp_apple_health.info(f"- user_id string passed to subprocess: {user_id_string} -")

        # Filename and path to subproces (WSAS)
        path_sub = os.path.join(current_app.config.get('APPLE_SERVICE_ROOT'), 'apple_health_service.py')

        if count_of_entries_sent_by_ios == 0:
            logger_bp_apple_health.info(f"- Not processing count_of_entries_sent_by_ios == 0: -")
            response_dict = {
                'message': "No data sent",
                'count_of_entries_sent_by_ios': f"{count_of_entries_sent_by_ios:,}",
                'count_of_user_apple_health_records': "0",
                'count_of_added_records': "0"
            }
            return jsonify(response_dict)

        # elif count_of_entries_sent_by_ios > 4000:
        else:
            # logger_bp_apple_health.info(f"- processing via WSAS, elif count_of_entries_sent_by_ios > 4000:-")
            logger_bp_apple_health.info(f"- processing via WSAS -")
            response_dict = {
                'message': "No data sent",
                'alertMessage':f"Apple Health Data contains {count_of_entries_sent_by_ios:,} records. \nYou will receive an email when all your data is added to the database."
            }

            # run WSAS subprocess
            # process = subprocess.Popen(['python', path_sub, user_id_string, apple_health_data_request_json_file_name, 'True', 'True'])
            process = subprocess.Popen(['python', path_sub, user_id_string, time_stamp_str_for_json_file_name, 'True', 'True'])
            logger_bp_apple_health.info(f"---> successfully started subprocess PID:: {process.pid} -")

        # else:
        #     logger_bp_apple_health.info(f"- processing via API elif count_of_entries_sent_by_ios < 4000:-")
        #     response_dict = add_apple_health_to_database(current_user.id, apple_health_data_request_json_file_name)
        #     count_of_records_added_to_db = response_dict.get('count_of_added_records')
        #     # run WSAS subprocess for correlation (i.e. dashboard json file only)
        #     # process = subprocess.Popen(['python', path_sub, user_id_string, apple_health_data_request_json_file_name, 'False', 'True',count_of_records_added_to_db])
        #     process = subprocess.Popen(['python', path_sub, user_id_string, time_stamp_str_for_apple_health_data_request_json_file_name, 'False', 'True',count_of_records_added_to_db])

        logger_bp_apple_health.info(f"---> WSAPI > receive_apple_health_data respone for <-----")
        logger_bp_apple_health.info(f"{response_dict}")
        return jsonify(response_dict)


@bp_apple_health.route('/receive_apple_workouts_data', methods=['POST'])
@token_required
def receive_apple_workouts_data(current_user):
    logger_bp_apple_health.info(f"- accessed  receive_apple_workouts_data endpoint-")
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

    # apple_health_workouts_request_json_file_name = request_json.get("filename")
    time_stamp_str_for_json_file_name = request_json.get("dateStringTimeStamp")
    apple_health_workouts_json = request_json.get("arryAppleHealthWorkout")
    count_of_entries_sent_by_ios = len(apple_health_workouts_json)
    # apple_health_workouts_data_request_json_file_name = f"{current_app.config.get('APPLE_HEALTH_WORKOUTS_FILENAME_PREFIX')}-user_id{current_user.id}-{time_stamp_str_for_apple_health_workouts_request_json_file_name}.json"
    apple_health_workouts_json_filename_str = apple_health_workouts_json_filename(current_user.id, time_stamp_str_for_json_file_name)
    # json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),apple_health_workouts_request_json_file_name)
    json_data_path_and_name = os.path.join(current_app.config.get('APPLE_HEALTH_DIR'),apple_health_workouts_json_filename_str)
    logger_bp_apple_health.info(f"- count_of_entries_sent_by_ios (this time): {count_of_entries_sent_by_ios} -")

    # new_data_dict = {}

    with open(json_data_path_and_name, 'w') as file:
        json.dump(apple_health_workouts_json, file, indent=4)

    #############################
    # Since the data process flow makes apple workouts first this is the end of the processing for this endpoint;
    # receive_apple_health_data endpoint will kickoff What Sticks Apple Service
    # What Sticks Apple Service will look for "AppleWorkouts-user_id\(userId)-\(dateString).json" file for current user
    ####################################
    response_dict = {
        'message': "AppleWorkouts .json file stored for user",
    }

    logger_bp_apple_health.info(f"---> WSAPI > receive_apple_workouts_data respone for <-----")
    logger_bp_apple_health.info(f"{response_dict}")
    return jsonify(response_dict)



@bp_apple_health.route('/apple_health_subprocess_complete', methods=['POST'])
# @token_required
def apple_health_subprocess_complete():
    logger_bp_apple_health.info(f"- accessed apple_health_subprocess_complete -")
    ws_api_password = request.json.get('WS_API_PASSWORD')
    logger_bp_apple_health.info(f"All Headers: {request.headers}")


    if current_app.config.get('WS_API_PASSWORD') == ws_api_password:
        logger_bp_apple_health.info(f"- sender password verified -")
        logger_bp_apple_health.info(f"- request.json: {request.json} -")


        count_of_records_added_to_db = request.json.get('count_of_records_added_to_db')
        user_id = request.json.get('user_id')
        user_obj = sess.get(Users,int(user_id))
        
        if user_obj.email != "nrodrig1@gmail.com":
            send_confirm_email(user_obj.email, count_of_records_added_to_db)
        logger_bp_apple_health.info(f"- WSAPI finished sending email to user informing data added to db -")
    
    return jsonify({"message":"WSAPI sent email to user that data added to db."})