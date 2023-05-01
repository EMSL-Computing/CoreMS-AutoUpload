from functools import wraps
import jwt
from flask import Blueprint, request
from flask.globals import current_app
from api.models.auth_model import User

auth = Blueprint('auth', __name__)


def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):

        token = None

        if 'token' in request.form:
            token = request.form['token']

        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']

        if not token:
            return {'message': 'a valid token is missing'}, 500

        try:
            payload = jwt.decode(token,
                                 current_app.config["SECRET_KEY"],
                                 algorithms="HS256")
            current_user = User(id=payload['id'],
                                first_name=payload['first_name'],
                                last_name=payload['last_name'],
                                email=payload['email'],
                                auth_token=token)

        except jwt.ExpiredSignatureError:
            print(token, f)
            return {'message': 'Signature expired. Please log in again.'}, 500

        except jwt.InvalidTokenError:
            print(token, f)
            return {'message': 'Invalid token. Please log in again.'}, 500

        except Exception as err:
            return {'message': str(err)}, 500

        return f(current_user, *args, **kwargs)
    return decorator
