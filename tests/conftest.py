import os
import tempfile

import pytest
import flask
from flask_wtf.csrf import generate_csrf
from flask.testing import FlaskClient as BaseFlaskClient
from MobiDetailsApp import create_app
from MobiDetailsApp.db import get_db, init_db

with open(os.path.join(os.path.dirname(__file__), 'md_test.sql'), 'rb') as f:
    _data_sql = f.read().decode('utf8')




@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test',
        'WTF_CSRF_ENABLED' : False,
        'ALLOWED_EXTENSIONS': '[txt]'
    })
    # app.test_client_class = FlaskClient
    with app.app_context():
        init_db()
        # db = get_db()
        # curs = db.cursor.execute(_data_sql)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self, email='test', password='test'):
        return self._client.post(
            '/auth/login',
            data={'email': email, 'password': password}
        )

    def logout(self):
        return self._client.get('/auth/logout')


@pytest.fixture
def auth(client):
    return AuthActions(client)
# 
# 
# # https://gist.github.com/singingwolfboy/2fca1de64950d5dfed72
# # classes to simulate csrf
# # Flask's assumptions about an incoming request don't quite match up with
# # what the test client provides in terms of manipulating cookies, and the
# # CSRF system depends on cookies working correctly. This little class is a
# # fake request that forwards along requests to the test client for setting
# # cookies.
# class RequestShim(object):
#     """
#     A fake request that proxies cookie-related methods to a Flask test client.
#     """
#     def __init__(self, client):
#         self.vary = set({})
#         self.client = client
# 
#     def set_cookie(self, key, value='', *args, **kwargs):
#         "Set the cookie on the Flask test client."
#         server_name = flask.current_app.config["SERVER_NAME"] or "localhost"
#         return self.client.set_cookie(
#             server_name, key=key, value=value, *args, **kwargs
#         )
# 
#     def delete_cookie(self, key, *args, **kwargs):
#         "Delete the cookie on the Flask test client."
#         server_name = flask.current_app.config["SERVER_NAME"] or "localhost"
#         return self.client.delete_cookie(
#             server_name, key=key, *args, **kwargs
#         )
# 
# # We're going to extend Flask's built-in test client class, so that it knows
# # how to look up CSRF tokens for you!
# class FlaskClient(BaseFlaskClient):
#     @property
#     def csrf_token(self):
#         # First, we'll wrap our request shim around the test client, so that
#         # it will work correctly when Flask asks it to set a cookie.
#         request = RequestShim(self) 
#         # Next, we need to look up any cookies that might already exist on
#         # this test client, such as the secure cookie that powers `flask.session`,
#         # and make a test request context that has those cookies in it.
#         environ_overrides = {}
#         self.cookie_jar.inject_wsgi(environ_overrides)
#         with flask.current_app.test_request_context(
#                 "/login", environ_overrides=environ_overrides,
#             ):
#             # Now, we call Flask-WTF's method of generating a CSRF token...
#             csrf_token = generate_csrf()
#             # ...which also sets a value in `flask.session`, so we need to
#             # ask Flask to save that value to the cookie jar in the test
#             # client. This is where we actually use that request shim we made!
#             #flask.current_app.session_interface.save_session(flask.session, request, self)
#             flask.current_app.save_session(flask.session, request)
#             # And finally, return that CSRF token we got from Flask-WTF.
#             return csrf_token