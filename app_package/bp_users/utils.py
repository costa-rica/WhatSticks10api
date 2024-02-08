from flask import current_app, url_for
import json
from ws_models import sess, Users, Locations
from flask_mail import Message
from app_package import mail
import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from timezonefinder import TimezoneFinder
import pytz
import pandas as pd
import requests


#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

#initialize a logger
logger_bp_users = logging.getLogger(__name__)
logger_bp_users.setLevel(logging.DEBUG)


#where do we store logging information
file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),"logs",'users_routes.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

#where the stream_handler will print
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

# logger_sched.handlers.clear() #<--- This was useful somewhere for duplicate logs
logger_bp_users.addHandler(file_handler)
logger_bp_users.addHandler(stream_handler)


def send_reset_email(user):
    token = user.get_reset_token()
    logger_bp_users.info(f"current_app.config.get(MAIL_USERNAME): {current_app.config.get('MAIL_USERNAME')}")
    msg = Message('Password Reset Request',
                  sender=current_app.config.get('MAIL_USERNAME'),
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request, ignore email and there will be no change
'''
    mail.send(msg)


def send_confirm_email(email):
    if os.environ.get('FLASK_CONFIG_TYPE') != 'local':
        logger_bp_users.info(f"-- sending email to {email} --")
        msg = Message('Welcome to What Sticks!',
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[email])
        msg.body = 'You have succesfully been registered to What Sticks.'
        mail.send(msg)
        logger_bp_users.info(f"-- email sent --")
    else :
        logger_bp_users.info(f"-- Non prod mode so no email sent --")


def delete_user_data_files(current_user):
    
    # dataframe pickle - apple category & quantity
    user_apple_health_dataframe_pickle_file_name = f"user_{current_user.id:04}_apple_health_dataframe.pkl"
    pickle_data_path_and_name = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_health_dataframe_pickle_file_name)
    if os.path.exists(pickle_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_apple_health_dataframe_pickle_file_name} successfully -")
        os.remove(pickle_data_path_and_name)
    
    # dataframe pickle - apple workouts
    user_apple_health_workouts_dataframe_pickle_file_name = f"user_{current_user.id:04}_apple_workouts_dataframe.pkl"
    pickle_data_path_and_name = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_health_workouts_dataframe_pickle_file_name)
    if os.path.exists(pickle_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_apple_health_workouts_dataframe_pickle_file_name} successfully -")
        os.remove(pickle_data_path_and_name)

    # data source json
    user_data_source_json_file_name = f"data_source_list_for_user_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DATA_SOURCE_FILES_DIR'), user_data_source_json_file_name)
    if os.path.exists(json_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_data_source_json_file_name} successfully -")
        os.remove(json_data_path_and_name)

    # dashboard json
    # user_sleep_dash_json_file_name = f"dt_sleep01_{current_user.id:04}.json"
    user_sleep_dash_json_file_name = f"data_table_objects_array_{current_user.id:04}.json"
    json_data_path_and_name = os.path.join(current_app.config.get('DASHBOARD_FILES_DIR'), user_sleep_dash_json_file_name)
    if os.path.exists(json_data_path_and_name):
        logger_bp_users.info(f"- deleted: {user_sleep_dash_json_file_name} successfully -")
        os.remove(json_data_path_and_name)


def delete_user_from_table(current_user, table):
    count_deleted_rows = 0
    error = None
    try:
        if table.__tablename__ != "users":
            count_deleted_rows = sess.query(table).filter_by(user_id = current_user.id).delete()
        else:
            count_deleted_rows = sess.query(table).filter_by(id = current_user.id).delete()
        sess.commit()
        response_message = f"Successfully deleted {count_deleted_rows} records from {table.__tablename__}"
    except Exception as e:
        sess.rollback()
        error_message = f"Failed to delete data from {table.__tablename__}, error: {e}"
        logger_bp_users.info(error_message)
        error = e
    
    return count_deleted_rows, error


def convert_lat_lon_to_timezone_string(latitude, longitude):
    # Note: latitude and longitude must be float
    tf = TimezoneFinder()
    try:
        # Find the timezone
        timezone_str = tf.timezone_at(lat=latitude, lng=longitude)
    except Exception as e:
        logger_bp_users.info(f"-- Timezone threw Exception, e: {e} \n\n setting to timezone: Etc/GMT --")
        timezone_str = "Etc/GMT"

    # Check if the timezone is found
    if timezone_str:
        logger_bp_users.info(f"-- found timezone: {timezone_str} --")
        return timezone_str
    else:
        logger_bp_users.info(f"-- Timezone could not be determined, timezone_str: {timezone_str} --")
        # return "Timezone could not be determined"
        return "Etc/GMT"

def convert_lat_lon_to_city_country(latitude, longitude):
    # url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
    url = f"{current_app.config.get('NOMINATIM_API_URL')}/reverse?lat={latitude}&lon={longitude}&format=json"

    # Send the request
    response = requests.get(url, headers={"User-Agent": "What Sticks"})

    # Parse the JSON response
    data = response.json()

    # Extract city and country
    city = data.get('address', {}).get('city', 'Not found')
    country = data.get('address', {}).get('country', 'Not found')
    state = data.get('address', {}).get('state', 'Not found')
    boundingbox = data.get('boundingbox', 'Not found')
    lat = data.get('lat', 'Not found')
    lon = data.get('lon', 'Not found')

    location_dict = {
        "city": city, "country":country, "state":state,"boundingbox":boundingbox,
        "lat":lat,"lon":lon
    }

    return location_dict


def find_user_location(user_latitude: float, user_longitude: float) -> str:
    print("find_user_location")
    # Query all locations from the database
    locations = sess.query(Locations).all()
    
    for location in locations:
        print(f"Checking {location.city}")
        # Assuming boundingbox format is [min_lat, max_lat, min_lon, max_lon]
        boundingbox = location.boundingbox
        min_lat, max_lat, min_lon, max_lon = boundingbox
        
        # add buffer
        min_lat = min_lat - 0.15
        max_lat = max_lat + 0.15
        min_lon = min_lon - 0.25
        max_lon = max_lon + 0.25
        # NOTE: Buffer magnitude in kilometers:
        # - 0.15 lat is approx 16.5km
        # - 0.25 lon is approx 20km

        # Check if user's coordinates are within the bounding box
        if min_lat <= user_latitude <= max_lat and min_lon <= user_longitude <= max_lon:
            print(f"*** Found coords in location: {location.city}")
            return str(location.id)  # Return the location ID if within the bounding box
    
    return "no_location_found"  # Return this if no location matches the user's coordinates



def get_apple_health_count_date(user_id):
    user_apple_qty_cat_dataframe_pickle_file_name = f"user_{int(user_id):04}_apple_health_dataframe.pkl"
    user_apple_workouts_dataframe_pickle_file_name = f"user_{int(user_id):04}_apple_workouts_dataframe.pkl"
    pickle_data_path_and_name_qty_cat = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_qty_cat_dataframe_pickle_file_name)
    pickle_data_path_and_name_workouts = os.path.join(current_app.config.get('DATAFRAME_FILES_DIR'), user_apple_workouts_dataframe_pickle_file_name)
    df_apple_qty_cat = pd.read_pickle(pickle_data_path_and_name_qty_cat)
    df_apple_workouts = pd.read_pickle(pickle_data_path_and_name_workouts)

    # get count of qty_cat and workouts
    apple_health_record_count = "{:,}".format(len(df_apple_qty_cat) + len(df_apple_workouts))

    # Convert startDate to datetime
    df_apple_qty_cat['startDate'] = pd.to_datetime(df_apple_qty_cat['startDate'])
    earliest_date_qty_cat = df_apple_qty_cat['startDate'].min()

    df_apple_workouts['startDate'] = pd.to_datetime(df_apple_workouts['startDate'])
    earliest_date_workouts = df_apple_workouts['startDate'].min()
    earliest_date_str = ""
    if earliest_date_workouts < earliest_date_qty_cat:
        # formatted_date_workouts = earliest_date_workouts.strftime('%b %d, %Y')
        # print(f"workouts are older: {formatted_date_workouts}")
        earliest_date_str = earliest_date_workouts.strftime('%b %d, %Y')
    else:
        # formatted_date_qty_cat = earliest_date_qty_cat.strftime('%b %d, %Y')
        # print(f"qty_cat are older: {formatted_date_qty_cat}")
        earliest_date_str = earliest_date_qty_cat.strftime('%b %d, %Y')

    return apple_health_record_count, earliest_date_str


