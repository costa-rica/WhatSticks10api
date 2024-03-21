from functools import wraps
from flask import request, jsonify,current_app
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous.url_safe import URLSafeTimedSerializer#new 2023
from ws_models import session_scope, Users
import logging
import os
from logging.handlers import RotatingFileHandler


formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_utilDecorators = logging.getLogger(__name__)
logger_utilDecorators.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(os.environ.get('API_ROOT'),'logs','utilDecorators.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_utilDecorators.addHandler(file_handler)
logger_utilDecorators.addHandler(stream_handler)



def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        logger_utilDecorators.info(f'- token_required decorator accessed -')
        # print('**in decorator**')
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
            # print('x-access-token exists!!')
            logger_utilDecorators.info(f'- x-access-token exists!! -')
            
        if not token:
            logger_utilDecorators.info(f'- no token -')
            return jsonify({'message': 'Token is missing'}), 401
        with session_scope() as session:
            try:
                serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
                decrypted_token_dict = serializer.loads(token)
                logger_utilDecorators.info(f'- decrypted_token_dict: {decrypted_token_dict} -')
                logger_utilDecorators.info('----')
                logger_utilDecorators.info(decrypted_token_dict['user_id'])
                logger_utilDecorators.info(f"type: {type(decrypted_token_dict['user_id'])}")
                # with session_scope() as session:
                # logger_utilDecorators.info(session.get(Users,int(decrypted_token_dict['user_id'])))
                logger_utilDecorators.info(session.get(Users,decrypted_token_dict['user_id']))
                logger_utilDecorators.info('----')
                current_user = session.get(Users,int(decrypted_token_dict['user_id']))
                logger_utilDecorators.info(f'- token decrypted correctly -')
            # except:
            #     logger_utilDecorators.info(f'- token NOT decrypted correctly -')
            #     return jsonify({'message': 'Token is invalid'}), 401
            except Exception as e:
                logger_utilDecorators.info(f"- token NOT decrypted correctly -")
                logger_utilDecorators.info(f"- {type(e).__name__}: {e} -")
                return jsonify({'message': 'Token is invalid'}), 401
            
            return f(current_user, *args, **kwargs)
    
    return decorated


def response_dict_tech_difficulties_alert(response_dict):
    
    if current_app.config.get('ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT'):
        logger_utilDecorators.info('######################################################################################')
        logger_utilDecorators.info('###########   ACTIVATE_TECHNICAL_DIFFICULTIES_ALERT is restricting users   ###########')
        logger_utilDecorators.info('######################################################################################')
        response_dict['alert_title'] = "Temporary Service Interruption"
        response_dict['alert_message'] = (
            "We're currently experiencing some technical difficulties and are unable to process your request. "
            "As a small team committed to your wellness journey, we're working tirelessly to resolve this. "
            "Thank you for your patience and support. "
        )
    return response_dict
