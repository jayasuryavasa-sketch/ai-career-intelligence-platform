from functools import wraps
from flask import session
from utils.error_handler import ApiError

def current_user_id():
    uid = session.get("user_id")
    if not uid: raise ApiError("Please sign in to continue.", 401, "unauthorized")
    return uid

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        current_user_id()
        return fn(*args, **kwargs)
    return wrapped
