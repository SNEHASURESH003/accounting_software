# Single source of truth for "who is the current request user?"
from contextvars import ContextVar

_current_user = ContextVar("current_user", default=None)

def set_current_user(user):
    return _current_user.set(user)  # returns a token

def reset_current_user(token):
    _current_user.reset(token)

def get_current_user():
    return _current_user.get()
