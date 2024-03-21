import os
import json
import requests
from flask import current_app
from ws_models import session_scope, inspect, Users, OuraToken, OuraSleepDescriptions
import logging
from logging.handlers import RotatingFileHandler

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_bp_oura = logging.getLogger(__name__)
logger_bp_oura.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','oura.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_bp_oura.addHandler(file_handler)
logger_bp_oura.addHandler(stream_handler)


def add_oura_sleep_to_OuraSleepDescriptions(user_id, token_id, response_oura_sleep):
    if isinstance(response_oura_sleep, dict):
        list_oura_sleep_sessions = response_oura_sleep.get('sleep')
        print("- oura file read here -")
    else:
        print("***** oura coming from OURA API response")
        # with open(response_oura_sleep, 'r') as file:
        #     list_oura_sleep_sessions = json.load(file).get('sleep')
        list_oura_sleep_sessions = response_oura_sleep.json().get('sleep')
    # if type(response_oura_sleep) == "dict":
    #     list_oura_sleep_sessions = response_oura_sleep.get('sleep')
    # else:
    #     list_oura_sleep_sessions = json.load(response_oura_sleep).get('sleep')

    count_of_sleep = len(list_oura_sleep_sessions)
    count_added = 0
    count_already_existing = 0

    for sleep_session in list_oura_sleep_sessions:
        # Adjust the filter criteria based on your specific columns and values
        with session_scope() as session:
            exists = session.query(OuraSleepDescriptions).filter_by(
                summary_date=sleep_session['summary_date'],
                user_id=user_id
            ).scalar() is not None

        if not exists:
            
            sleep_session['token_id'] = token_id
            sleep_session['user_id'] = user_id
            
            # Get the column names from the OuraSleepDescriptions model
            columns = [c.key for c in inspect(OuraSleepDescriptions).mapper.column_attrs]
            # Filter the dictionary to only include keys that match the column names
            filtered_dict = {k: sleep_session[k] for k in sleep_session if k in columns}
            # Create a new OuraSleepDescriptions instance with the filtered dictionary
            new_oura_session = OuraSleepDescriptions(**filtered_dict)
            
            with session_scope() as session:
                session.add(new_oura_session)
            
            count_added += 1
        else:
            count_already_existing += 1
    

    with session_scope() as session:
        user_oura_sessions = session.query(OuraSleepDescriptions).filter_by(user_id=user_id).all()

    logger_bp_oura.info(f"Sleep sessions count: {count_of_sleep}, added: {count_added}, already existed: {count_already_existing}")
    dict_summary = {}
    dict_summary["sleep_sessions_added"] = "{:,}".format(count_added)
    dict_summary["record_count"] = "{:,}".format(len(user_oura_sessions))

    return dict_summary
    