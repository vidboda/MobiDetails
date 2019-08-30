import os
import tempfile

import pytest
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
    })

    with app.app_context():
        init_db()
        db =get_db()
        cuss = db.cursor.execute(_data_sql)

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
    
    