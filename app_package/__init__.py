from flask import Flask
# from ws_config import ConfigLocal, ConfigDev, ConfigProd
from app_package.config import config
import os
import logging
from logging.handlers import RotatingFileHandler
from pytz import timezone
from datetime import datetime
from flask_mail import Mail
from ws_models import Base, engine

if not os.path.exists(os.path.join(os.environ.get('API_ROOT'),'logs')):
    os.makedirs(os.path.join(os.environ.get('API_ROOT'), 'logs'))

# timezone 
def timetz(*args):
    return datetime.now(timezone('Europe/Paris') ).timetuple()

logging.Formatter.converter = timetz

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_init = logging.getLogger('__init__')
logger_init.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','__init__.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

stream_handler_tz = logging.StreamHandler()

logger_init.addHandler(file_handler)
logger_init.addHandler(stream_handler)

logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('werkzeug').addHandler(file_handler)

logger_init.info(f'--- Starting WhatSticks10 API ---')

mail = Mail()

def create_app(config_for_flask = config):
    logger_init.info("- WhatSticks10Api/app_package/__init__.py create_app() -")
    app = Flask(__name__)   
    app.config.from_object(config_for_flask)
    mail.init_app(app)

    ############################################################################
    ## create folders for DB_ROOT
    create_folder(config_for_flask.DB_ROOT)
    # database helper files
    create_folder(config_for_flask.DATABASE_HELPER_FILES)
    create_folder(config_for_flask.APPLE_HEALTH_DIR)
    create_folder(config_for_flask.DATAFRAME_FILES_DIR)
    create_folder(config_for_flask.OURA_SLEEP_RESPONSES)
    create_folder(config_for_flask.USER_LOCATION_JSON)
    # ios helper files
    create_folder(config_for_flask.WS_IOS_HELPER_FILES)
    create_folder(config_for_flask.DASHBOARD_FILES_DIR)
    create_folder(config_for_flask.DATA_SOURCE_FILES_DIR)
    # user files
    create_folder(config_for_flask.USER_FILES)
    create_folder(config_for_flask.DAILY_CSV)
    create_folder(config_for_flask.RAW_FILES_FOR_DAILY_CSV)
    # # auxiliary
    # create_folder(config_for_flask.DIR_DB_AUXILIARY)
    # create_folder(config_for_flask.DIR_DB_BLOG)
    # create_folder(config_for_flask.DIR_DB_NEWS)
    # create_folder(config_for_flask.DIR_DB_AUX_IMAGES_PEOPLE)
    # create_folder(config_for_flask.DIR_DB_AUX_FILES_UTILITY)
    ############################################################################
    ## Build Sqlite database
    if os.path.exists(os.path.join(config_for_flask.DB_ROOT,os.environ.get('DB_NAME_WHAT_STICKS'))):
        logger_init.info(f"db already exists: {os.path.join(config_for_flask.DB_ROOT,os.environ.get('DB_NAME_WHAT_STICKS'))}")
    else:
        Base.metadata.create_all(engine)
        logger_init.info(f"NEW db created: {os.path.join(config_for_flask.DB_ROOT,os.environ.get('DB_NAME_WHAT_STICKS'))}")

    from app_package.bp_users.routes import bp_users
    from app_package.bp_oura.routes import bp_oura
    from app_package.bp_apple_health.routes import bp_apple_health

    app.register_blueprint(bp_users)
    app.register_blueprint(bp_oura)
    app.register_blueprint(bp_apple_health)

    return app

def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        logger_init.info(f"created: {folder_path}")
