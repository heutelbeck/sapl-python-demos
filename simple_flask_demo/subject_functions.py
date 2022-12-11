import jwt
from flask import request

PREFIX = 'Bearer '

"""
SAPL_flask needs functions which evaluate how a subject for the AuthorizationSubscription is created.

These functions are all called, when an AuthorizationSubscription is created with a dict as argument, which contains
the decorated function itself as  'function', the class of the decorated method as 'class' and the args and kwargs 
zipped in a dict as 'args'.

The return value of the functions need to be a dict, which updates the dict of the subject.
It is possible to add multiple functions, which all update the dict of the subject.
This is useful if you want to add multiple methods how a user is authorized.
Authorization methods which are not used in a current request can return an empty dict.

If you want to add your own subject function, you can create a function, which has 1 parameter of type dict and returns 
a dict. This function needs to be added to the list of functions in the call of 
sapl_flask.init_sapl(app.config,[jwt_as_subject]) in the app.py file.
"""


def jwt_as_subject(values: dict):
    """
    A function which is added to the FlaskAuthorizationSubscriptionFactory Singleton on startup.
    This function retrieves the JWT from the authorization header, if one is present and adds a dict of the decoded token
    to the subject.
    """
    if not request.headers.get('Authorization'):
        return {}
    try:
        token = get_token(request.headers.get('Authorization'))
        decoded_token = jwt.decode(token, options={"verify_signature": False}, algorithms="HS256")
        decoded_token.update({"token": token})
        return decoded_token
    except ValueError:
        return {}


def get_token(header):
    """
    Helperfunction to check, if the Authorization Header contains a JWT
    """
    if not header.startswith(PREFIX):
        raise ValueError('Invalid token')

    return header[len(PREFIX):]
