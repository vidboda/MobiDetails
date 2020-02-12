import pytest
import psycopg2
import json
from MobiDetailsApp.db import get_db

# test variant exists


@pytest.mark.parametrize(('variant', 'key', 'response'), (
    ('NC_000001.10:g.216595579G>A', 'mobidetails_id', '5'),
    ('NC_000001.11:g.216422237G>A', 'mobidetails_id', '5'),
    ('nc_000001.11:g.216422237G>A', 'mobidetails_id', '5'),
    ('NC_000001.11:g.2164222', 'mobidetails_warning', 'does not exist'),
    ('nc_000001.11:g.2164222', 'mobidetails_warning', 'does not exist'),
    ('C_000001.11:g.216422237G>A', 'mobidetails_error', 'malformed query')
))
def test_api_variant_exists(client, app, variant, key, response):
    json_response = json.loads(client.get('/api/variant/exists/{}'.format(variant)).data.decode('utf8'))
    assert response in str(json_response[key])

# test gene


@pytest.mark.parametrize(('gene', 'key', 'response'), (
    ('USH2A', 'HGNC', 'USH2A'),
    ('USH2', 'mobidetails_warning', 'Unknown gene'),
    ('--%USH2A', 'mobidetails_error', 'Invalid gene submitted')
))
def test_api_gene(client, app, gene, key, response):
    json_response = json.loads(client.get('/api/gene/{}'.format(gene)).data.decode('utf8'))
    print(json_response)
    assert response in str(json_response[key])


# test variant creation


@pytest.mark.parametrize(('new_variant', 'api_key', 'return_key', 'message'), (
    ('NM_206933.2:c.100C>T', 'random', 'mobidetails_error', 'Invalid API key'),
    ('NM_206933.2:c.100C>T', '', 'mobidetails_id', 5),
    ('NM_206933.2:c.100C>T', 'ahkgs6!jforjsge%hefqvx,v;:dlzmpdtshenicldje', 'mobidetails_error', 'Unknown API key'),
    ('M_206933.2:c.100C>T', '', 'mobidetails_error', 'malformed query'),
))
def test_api_create(client, app, new_variant, api_key, return_key, message):
    with app.app_context():
        if api_key == '':
            db = get_db()
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                "SELECT api_key FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
            )
            res = curs.fetchone()
            if res is not None:
                api_key = res['api_key']
        print('/api/variant/create/{0}/{1}'.format(new_variant, api_key))
        json_response = json.loads(client.get('/api/variant/create/{0}/{1}'.format(new_variant, api_key)).data.decode('utf8'))

        if isinstance(json_response[return_key], int):
            assert json_response[return_key] == message
        else:
            assert message in json_response[return_key]
