import os
import json
import requests
from flask import current_app
from ws_models import DatabaseSession, inspect, Users, OuraToken, OuraSleepDescriptions
from app_package._common.utilities import custom_logger, wrap_up_session

logger_bp_oura = custom_logger('bp_oura.log')


def add_oura_sleep_to_OuraSleepDescriptions(user_id, token_id, response_oura_sleep):
    db_session = DatabaseSession()
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

    for session in list_oura_sleep_sessions:
        # Adjust the filter criteria based on your specific columns and values
        exists = db_session.query(OuraSleepDescriptions).filter_by(
            summary_date=session['summary_date'],
            user_id=user_id
        ).scalar() is not None

        if not exists:
            
            session['token_id'] = token_id
            session['user_id'] = user_id
            
            # Get the column names from the OuraSleepDescriptions model
            columns = [c.key for c in inspect(OuraSleepDescriptions).mapper.column_attrs]
            # Filter the dictionary to only include keys that match the column names
            filtered_dict = {k: session[k] for k in session if k in columns}
            # Create a new OuraSleepDescriptions instance with the filtered dictionary
            new_oura_session = OuraSleepDescriptions(**filtered_dict)
            
            # new_oura_session = OuraSleepDescriptions(**session)
            db_session.add(new_oura_session)
            wrap_up_session(logger_bp_oura, db_session)
            count_added += 1
        else:
            count_already_existing += 1
    
    user_oura_sessions = db_session.query(OuraSleepDescriptions).filter_by(user_id=user_id).all()

    logger_bp_oura.info(f"Sleep sessions count: {count_of_sleep}, added: {count_added}, already existed: {count_already_existing}")
    dict_summary = {}
    dict_summary["sleep_sessions_added"] = "{:,}".format(count_added)
    dict_summary["record_count"] = "{:,}".format(len(user_oura_sessions))

    wrap_up_session(logger_bp_oura, db_session)
    return dict_summary
    