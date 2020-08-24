import pytest
import psycopg2
from io import BytesIO
from MobiDetailsApp.db import get_db
# test file upload

test_vars = b'NM_206933.2:c.2276G>T\nNC_000001.11:g.40817273del;KCNQ4'


def test_file_upload(client, app):
    with app.app_context():
        response = client.post('/file_upload',
                           buffered=True,
                           content_type='multipart/form-data',
                           data={
                                'file': (BytesIO(test_vars), 'test.txt'),
                           }
                        )
        print(response.get_data())
        assert response.status_code == 200