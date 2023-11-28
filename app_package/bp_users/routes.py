from flask import Blueprint
from flask import request, jsonify, make_response, current_app
from ws_models import sess, Users
from werkzeug.security import generate_password_hash, check_password_hash #password hashing
import bcrypt
#import jwt #token creating thing
import datetime
# import base64
# from functools import wraps
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
# from app_package.utilsDecorators import token_required
from itsdangerous.url_safe import URLSafeTimedSerializer#new 2023
import logging
import os
from logging.handlers import RotatingFileHandler
import json
import socket


formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_bp_users = logging.getLogger(__name__)
logger_bp_users.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','users.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_bp_users.addHandler(file_handler)
logger_bp_users.addHandler(stream_handler)

bp_users = Blueprint('bp_users', __name__)
logger_bp_users.info(f'- WhatSticks10 API users Bluprints initialized')

salt = bcrypt.gensalt()

@bp_users.route('/are_we_working', methods=['GET'])
def are_we_working():
    logger_bp_users.info(f"are_we_working endpoint pinged")

    logger_bp_users.info(f"{current_app.config.get('WS_API_PASSWORD')}")

    hostname = socket.gethostname()

    # print(dir(current_app.config))
    # print(current_app.config.items())

    return jsonify(f"Yes! We're up! in the {hostname} machine")


@bp_users.route('/login',methods=['POST'])
def login():
    logger_bp_users.info(f"- login endpoint pinged -")
    ws_api_password = request.json.get('WS_API_PASSWORD')
    logger_bp_users.info(f"All Headers: {request.headers}")

    if current_app.config.get('WS_API_PASSWORD') == ws_api_password:
        logger_bp_users.info(f"- sender password verified -")

        auth = request.authorization
        logger_bp_users.info(f"- auth.username: {auth.username} -")

        if not auth or not auth.username or not auth.password:
            return make_response('Could not verify', 401)

        user = sess.query(Users).filter_by(email= auth.username).first()

        if not user:
            return make_response('Could not verify - user not found', 401)

        logger_bp_users.info(f"- checking password -")


        if auth.password:
            if bcrypt.checkpw(auth.password.encode(), user.password):
                # login_user(user)
                serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
                # return serializer.dumps({'user_id': self.id})
                return serializer.dumps({'user_id': user.id})

        return make_response('Could not verify', 401)
    else:
        return make_response('Could note verify sender', 401)


@bp_users.route('/add_user', methods=['POST'])
def add_user():
    logger_bp_users.info(f"- add_user endpoint pinged -")
    # ws_api_password = request.form.get('WS_API_PASSWORD')
    ws_api_password = request.json.get('WS_API_PASSWORD')
    print(ws_api_password)
    print(request.json)
    if current_app.config.get('WS_API_PASSWORD') == ws_api_password:

        request_data = request.get_json()

        if request_data.get('email') in ("", None) or request_data.get('password') in ("" , None):
            return make_response('User must have email and password', 409)

        user_exists = sess.query(Users).filter_by(email= request_data.get('email')).first()

        if user_exists:
            return make_response('User already exists', 409)

        hash_pw = bcrypt.hashpw(request_data.get('password').encode(), salt)
        new_user = Users()

        for key, value in request_data.items():
            if key == "password":
                setattr(new_user, "password", hash_pw)
            elif key in Users.__table__.columns.keys():
                setattr(new_user, key, value)

        sess.add(new_user)
        sess.commit()
        return jsonify({"message": f"new user created: {request_data.get('email')}"})
    else:
        return make_response('Could not verify sender', 401)




