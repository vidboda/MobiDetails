import os
import tempfile

import pytest
from MobiDetailsApp import create_app
from MobiDetailsApp.db import init_db



@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test',
        'WTF_CSRF_ENABLED': False,
        'ALLOWED_EXTENSIONS': '[txt]',
        'RUN_MODE': 'on',
        'TINY_URL_API_KEY': '19d5ze3g8e4a68t4s699s4ed42e6r2t8yf7z8r9t5y4h7g8d5z2e1r4f87f6',
        'VV_TOKEN': 'eXObqceEgR2l4W6bNl9lkb.ruhyWVE3hBnrkL85qWFpyqU3mdD790ctIP6r4e-FakowUjFxuEp4CwpA7apILdGdjLOJVXeEpkKuFpNeV6wiSiiROfk0CbFD'
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

