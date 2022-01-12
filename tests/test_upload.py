# import pytest
from io import BytesIO
# test file upload

test_vars = b'NM_206933.2:c.2276G>T\nNC_000001.11:g.40817273del;KCNQ4\nrs1052030\nrs10520305\nNM_206933.2:c.2276C>T\nlhdsfqirhg\nrs534370897'


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
