from functools import wraps
from flask import request, jsonify,current_app
# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous.url_safe import URLSafeTimedSerializer#new 2023
from ws_models import sess, Users
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


# users = Blueprint('users',__name__)



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
        
        try:
            serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            decrypted_token_dict = serializer.loads(token)
            logger_utilDecorators.info(f'- decrypted_token_dict: {decrypted_token_dict} -')
            logger_utilDecorators.info('----')
            logger_utilDecorators.info(decrypted_token_dict['user_id'])
            logger_utilDecorators.info(sess.query(Users).filter_by(id = decrypted_token_dict['user_id']).first())
            logger_utilDecorators.info('----')
            current_user = sess.query(Users).filter_by(id = decrypted_token_dict['user_id']).first()
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