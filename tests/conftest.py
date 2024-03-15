import os
import tempfile
import configparser

import pytest
from MobiDetailsApp import create_app
from MobiDetailsApp.db import init_db



@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    # load true config
    config = configparser.ConfigParser()
    with open('MobiDetailsApp/sql/md.cfg') as stream:
        config.read_string('[DEFAULT]\n' + stream.read())
    md_conf = dict(config.items('DEFAULT'))
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test',
        'WTF_CSRF_ENABLED': False,
        'ALLOWED_EXTENSIONS': '[txt]',
        'RUN_MODE': 'on',
        'TINY_URL_API_KEY': md_conf['tiny_url_api_key'].replace('"', ''),
        'VV_TOKEN': md_conf['vv_token'].replace('"', ''),
        'GENEBE_EMAIL': md_conf['genebe_email'].replace('"', ''),
        'GENEBE_API_KEY': md_conf['genebe_api_key'].replace('"', ''),
    })
    with app.app_context():
        init_db()

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

