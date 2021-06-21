import pytest
import psycopg2
import json
from MobiDetailsApp.db import get_db

# test api key


@pytest.mark.parametrize(('api_key', 'api_key_pass_check', 'api_key_status'), (
    ('', True, 'active'),
    ('xLeeX6_tD3flHnI__Rc4P1PqklR2Sm8aFsPXrMrE6s', False, 'irrelevant'),
    (1234, False, 'irrelevant'),
    (None, False, 'irrelevant'),
    ('nxLeeX6_tD3flHnI__Rc4P1PqkpR2Sm8aFs8PXrMrE6s', False, 'irrelevant'),
))
def test_check_api_key(client, app, api_key, api_key_pass_check, api_key_status):
    with app.app_context():
        if api_key == '':
            api_key = get_generic_api_key()
    json_response = json.loads(
        client.post('/api/service/check_api_key', data={'api_key':api_key}).data.decode('utf8')
    )
    print(json_response)
    assert api_key_pass_check == json_response['api_key_pass_check']
    assert api_key_status == json_response['api_key_status']

# test vv instance


def test_check_vv_instance(client):
    json_response = json.loads(client.get('/api/service/vv_instance').data.decode('utf8'))
    print(json_response)
    assert json_response['variant_validator_instance'] in \
        ['No VV running', 'Running our own emergency VV server', 'Running genuine VV server']

# test variant exists


@pytest.mark.parametrize(('variant', 'key', 'response'), (
    ('NC_000001.10:g.216595579G>A', 'mobidetails_id', '5'),
    ('NC_000001.11:g.216422237G>A', 'mobidetails_id', '5'),
    ('nc_000001.11:g.216422237G>A', 'mobidetails_id', '5'),
    ('NC_000001.11:g.2164222', 'mobidetails_warning', 'does not exist'),
    ('nc_000001.11:g.2164222', 'mobidetails_warning', 'does not exist'),
    ('C_000001.11:g.216422237G>A', 'mobidetails_error', 'Malformed query')
))
def test_api_variant_exists(client, variant, key, response):
    json_response = json.loads(client.get('/api/variant/exists/{}'.format(variant)).data.decode('utf8'))
    assert response in str(json_response[key])

# test gene


@pytest.mark.parametrize(('gene', 'key', 'response'), (
    ('USH2A', 'HGNC Name', 'USH2A'),
    (12601, 'HGNC Name', 'USH2A'),
    ('USH2', 'mobidetails_warning', 'Unknown gene'),
    ('--%USH2A', 'mobidetails_error', 'Invalid gene submitted')
))
def test_api_gene(client, gene, key, response):
    json_response = json.loads(client.get('/api/gene/{}'.format(gene)).data.decode('utf8'))
    print(json_response)
    assert response in str(json_response[key])

# get generic mobidetails api_key


def get_generic_api_key():
    db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        "SELECT api_key FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
    )
    res = curs.fetchone()
    if res is not None:
        return res['api_key']


# test variant creation
@pytest.mark.parametrize(('variant_id', 'key', 'value'), (
    (220783, 'cName', 'c.1771T>C'),
    (8, 'hg19PseudoVCF', '1-216420460-C-A'),
))
def test_api_variant(client, variant_id, key, value):
    json_response = json.loads(client.get('/api/variant/{}/clispip/'.format(variant_id)).data.decode('utf8'))
    assert json_response['nomenclatures'][key] == value

# 2nd test variant creation


def test_api_variant2(app, client):
    with app.app_context():
        db = get_db()
        curs = db.cursor()
        curs.execute(
            "SELECT id FROM variant_feature WHERE c_name <> 'c.1A>T' ORDER BY random() LIMIT 100"  #  LIMIT 100  WHERE prot_type = 'missense'",  #  ORDER BY random() LIMIT 500
        )
        res = curs.fetchall()
        for variant_id in res:
            print(variant_id)
            json_response = json.loads(client.get('/api/variant/{}/cli/'.format(variant_id[0])).data.decode('utf8'))
            assert 'nomenclatures' in json_response


@pytest.mark.parametrize(('new_variant', 'api_key', 'return_key', 'message'), (
    ('NM_206933.0:c.100C>T', 'random', 'mobidetails_error', 'Invalid API key'),
    ('NM_206933.2:c.100C>T', '', 'mobidetails_id', 5),
    ('NM_206933.10:c.100C>T', 'ahkgs6!jforjsge%hefqvx,v;:dlzmpdtshenicldje', 'mobidetails_error', 'Unknown API key'),
    ('M_206933.2:c.100C>T', '', 'mobidetails_error', 'Malformed query'),
    ('NM_206933.3:c.10000C>T', '', 'mobidetails_error', 'The RefSeq accession number submitted'),
))
def test_api_create(client, app, new_variant, api_key, return_key, message):
    with app.app_context():
        if api_key == '':
            api_key = get_generic_api_key()
        # print('/api/variant/create/{0}/{1}'.format(new_variant, api_key))
        data = {
            'variant_chgvs': new_variant,
            'caller': 'cli',
            'api_key': api_key
        }
        json_response = json.loads(client.post('/api/variant/create', data=data).data.decode('utf8'))
        # json_response = json.loads(client.get('/api/variant/create/{0}/{1}'.format(new_variant, api_key)).data.decode('utf8'))
        print(json_response)
        if isinstance(json_response[return_key], int):
            assert json_response[return_key] == message
        else:
            assert message in json_response[return_key]

# test variant_g creation


@pytest.mark.parametrize(('variant_ghgvs', 'api_key', 'gene', 'caller', 'return_key', 'message'), (
    ('NC_000001.11:g.40817273T>G', 'random', 'KCNQ4', 'cli', 'mobidetails_error', 'Invalid API key'),
    ('NC_000001.11:g.40817273T>G', '', 'KCNQ4', 'cli', 'mobidetails_id', 117),
    ('NC_000001.11:g.40817273T>G', '', 6298, 'cli', 'mobidetails_id', 117),
    # ('NC_000001.11:g.40817273T>G', 'ahkgs6!jforjsge%hefqvx,v;:dlzmpdtshenicldje', 'KCNQ4', 'browser', 'mobidetails_error', 'Unknown API key'),
    # ('NC_000001.11:g.40817273T>G', '', 'KCNQ4', 'clic', 'mobidetails_error', 'Invalid caller submitted'),
    ('NC_000001.10:g.41282945T>G', '', 'KCNQ4', 'cli', 'mobidetails_id', 117),
    ('NC_000035.11:g.40817273T>G', '', 'KCNQ4', 'cli', 'mobidetails_error', 'Unknown chromosome'),
    ('NG_000001.11:g.40817273T>G', '', 'KCNQ4', 'cli', 'mobidetails_error', 'Malformed query'),
    ('NC_000001.11:g.40817273T>G', '', 'KCNQ4111', 'cli', 'mobidetails_error', 'is currently not available for variant annotation in MobiDetails'),
))
def test_api_variant_g_create(client, app, variant_ghgvs, api_key, gene, caller, return_key, message):
    with app.app_context():
        if api_key == '':
            api_key = get_generic_api_key()
        data = {
            'variant_ghgvs': variant_ghgvs,
            'gene_hgnc': gene,
            'caller': caller,
            'api_key': api_key
        }
        json_response = json.loads(client.post('/api/variant/create_g', data=data).data.decode('utf8'))
        print(json_response)
        if isinstance(json_response[return_key], int):
            assert json_response[return_key] == message
        else:
            assert message in json_response[return_key]

# test variant rs creation


@pytest.mark.parametrize(('rs_id', 'api_key', 'caller', 'return_key', 'message'), (
    ('rs10012946', 'random', 'cli', 'mobidetails_error', 'Invalid API key'),
    ('rs10012946', '', 'cli', 'NM_006005.3:c.631+256T>C', 1672),
    # ('rs10012946', 'ahkgs6!jforjsge%hefqvx,v;:dlzmpdtshenicldje', 'browser', 'mobidetails_error', 'Invalid API key'),
    # ('rs10012946', '', 'clic', 'mobidetails_error', 'Invalid caller submitted'),
    ('sdgg5456', '', 'cli', 'mobidetails_error', 'Invalid rs id provided'),
    ('rs99195525555555', '', 'cli', 'mobidetails_error', 'Using Mutalyzer, we did not find any suitable variant')
))
def test_api_variant_create_rs(client, app, rs_id, api_key, caller, return_key, message):
    with app.app_context():
        if api_key == '':
            api_key = get_generic_api_key()
        data = {
            'rs_id': rs_id,
            'caller': caller,
            'api_key': api_key
        }
        try:
            json_response = json.loads(client.post('/api/variant/create_rs', data=data).data.decode('utf8'))
            print(json_response)
            if 'mobidetails_id' in json_response[return_key] and \
                    isinstance(json_response[return_key]['mobidetails_id'], int):
                assert json_response[return_key]['mobidetails_id'] == message
            else:
                assert message in json_response[return_key]
        except Exception:
            assert message in client.post('/api/variant/create_rs', data=data).get_data()

# test variant acmg class update


@pytest.mark.parametrize(('variant_id', 'acmg_class', 'api_key', 'return_key', 'message'), (
    (1, 0, 'test', 'mobidetails_error', 'Invalid API key'),
    (1, 1, '', 'mobidetails_error', 'Invalid variant id submitted'),
    (8, 0, '', 'mobidetails_error', 'Invalid ACMG class submitted'),
    (8, 3, '', 'mobidetails_error', 'ACMG class already submitted by this user for this variant'),
))
def test_api_update_acmg(client, app, variant_id, acmg_class, api_key, return_key, message):
    with app.app_context():
        if api_key == '':
            api_key = get_generic_api_key()
        data = {
            'variant_id': variant_id,
            'acmg_id': acmg_class,
            'api_key': api_key
        }
        # print('/api/variant/update_acmg/{0}/{1}/{2}'.format(variant_id, acmg_class, api_key))
        json_response = json.loads(client.post('/api/variant/update_acmg', data=data).data.decode('utf8'))
        # json_response = json.loads(client.get('/api/variant/update_acmg/{0}/{1}/{2}'.format(variant_id, acmg_class, api_key)).data.decode('utf8'))

        if isinstance(json_response[return_key], int):
            assert json_response[return_key] == message
        else:
            assert message in json_response[return_key]
