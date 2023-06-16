import pytest
import psycopg2
import json
import urllib.parse
from test_ajax import get_db


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
        client.post(
            '/api/service/check_api_key',
            data={'api_key':api_key}
        ).data.decode('utf8')
    )
    print(json_response)
    assert api_key_pass_check == json_response['api_key_pass_check']
    assert api_key_status == json_response['api_key_status']

# test vv instance


def test_check_vv_instance(client):
    json_response = json.loads(client.get('/api/service/vv_instance').data.decode('utf8'))
    print(json_response)
    assert json_response['variant_validator_instance'] in \
        ['No VV running', 'Running internal VV server dedicated to web UI (can be used as a backup for API calls)', 'Running internal VV server dedicated to API calls (can be used as a backup for web UI)', 'Running genuine english VV server, as a backup - this means that both internal VV servers are down! Please warn me asap']

# test variant exists


@pytest.mark.parametrize(('variant', 'key', 'response'), (
    ('NC_000001.10:g.216595579G>A', 'mobidetails_id', '5'),
    ('NC_000001.11:g.216422237G>A', 'mobidetails_id', '5'),
    # ('nc_000001.11:g.216422237G>A', 'mobidetails_id', '5'),
    ('NC_000001.11:g.2164222', 'mobidetails_warning', 'does not exist'),
    # ('nc_000001.11:g.2164222', 'mobidetails_warning', 'does not exist'),
    ('NC_000007.11:g.216422237G>A', 'mobidetails_error', 'does not exist'),
    ('C_000001.11:g.216422237G>A', 'mobidetails_error', 'Malformed query')
))
def test_api_variant_exists(client, variant, key, response):
    json_response = json.loads(client.get('/api/variant/exists/{}'.format(variant)).data.decode('utf8'))
    assert response in str(json_response[key])

# test gene


@pytest.mark.parametrize(('gene', 'key', 'response'), (
    ('USH2A', 'HGNCSymbol', 'USH2A'),
    (12601, 'HGNCSymbol', 'USH2A'),
    ('USH2', 'mobidetails_warning', 'Unknown gene'),
    ('--%USH2A', 'mobidetails_error', 'Invalid gene submitted')
))
def test_api_gene(client, gene, key, response):
    json_response = json.loads(client.get('/api/gene/{}'.format(gene)).data.decode('utf8'))
    print(json_response)
    assert response in str(json_response[key])

# get generic mobidetails api_key


def get_generic_api_key():
    db_pool, db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        """
        SELECT api_key
        FROM mobiuser
        WHERE email = 'mobidetails.iurc@gmail.com'
        """
    )
    res = curs.fetchone()
    if res is not None:
        db_pool.putconn(db)
        return res['api_key']
    db_pool.putconn(db)
    return None

# test variant data


@pytest.mark.parametrize(('variant_id', 'key', 'value'), (
    (220783, 'cName', 'c.1771T>C'),
    (8, 'hg19PseudoVCF', '1-216420460-C-A'),
))
def test_api_variant(client, variant_id, key, value):
    json_response = json.loads(client.get('/api/variant/{}/clispip/'.format(variant_id)).data.decode('utf8'))
    assert json_response['nomenclatures'][key] == value

# 2nd test variant data


def test_api_variant2(app, client):
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor()
        curs.execute(
            """
            SELECT id
            FROM variant_feature
            WHERE c_name <> 'c.2del'
            ORDER BY random()
            LIMIT 100
            """  # LIMIT 100  WHERE prot_type = 'missense'",  #  ORDER BY random() LIMIT 500
        )
        res = curs.fetchall()
        db_pool.putconn(db)
        for variant_id in res:
            print(variant_id)
            json_response = json.loads(client.get('/api/variant/{}/cli/'.format(variant_id[0])).data.decode('utf8'))
            assert 'nomenclatures' in json_response

# test variant creation


@pytest.mark.parametrize(('new_variant', 'api_key', 'return_key', 'message'), (
    ('NM_206933.0:c.100C>T', 'random', 'mobidetails_error', 'Invalid API key'),
    ('NM_206933.4:c.100C>T', '', 'mobidetails_id', 334419),
    ('NM_206933.10:c.100C>T', 'ahkgs60jforjsge0hefqvx0v00dlzmpdtshenicldje', 'mobidetails_error', 'Unknown API key'),
    ('M_206933.4:c.100C>T', '', 'mobidetails_error', 'Invalid parameters'),
    ('NM_206933.9:c.10000C>T', '', 'mobidetails_error', 'It seems that your transcript version'),
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
    ('NC_000001.11:g.40817273T>G', '', 'KCNQ4', 'cli', 'mobidetails_id', 334420),
    ('NC_000001.11:g.40817273T>G', '', 6298, 'cli', 'mobidetails_id', 334420),
    # ('NC_000001.11:g.40817273T>G', 'ahkgs6!jforjsge%hefqvx,v;:dlzmpdtshenicldje', 'KCNQ4', 'browser', 'mobidetails_error', 'Unknown API key'),
    # ('NC_000001.11:g.40817273T>G', '', 'KCNQ4', 'clic', 'mobidetails_error', 'Invalid caller submitted'),
    ('NC_000001.10:g.41282945T>G', '', 'KCNQ4', 'cli', 'mobidetails_id', 334420),
    ('NC_000035.11:g.40817273T>G', '', 'KCNQ4', 'cli', 'mobidetails_error', 'Unknown chromosome'),
    ('NG_000001.11:g.40817273T>G', '', 'KCNQ4', 'cli', 'mobidetails_error', 'Invalid parameters'),
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
    ('sdgg5456', '', 'cli', 'mobidetails_error', 'Invalid parameter'),
    ('rs99195525555555', '', 'cli', 'mobidetails_error', 'The NCBI API returned an error for the variant')
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


@pytest.mark.parametrize(('vcf_str', 'genome_version', 'api_key', 'caller', 'return_key', 'message'), (
    ('1-216247118-C-TAGCTA', 'GRCh38', 'random', 'cli', 'mobidetails_error', 'Invalid API key'),
    ('1-216247118-C-TAGCTA', 'hg38', 'random', 'cli', 'mobidetails_error', 'Invalid API key'),
    ('1-216247118-C-TAGCTA', 'GRCh38', '', 'cli', 'NM_206933.4:c.2276delinsTAGCTA', 334683),
    ('1-216247118-C-TAGCTA', 'hg38', '', 'cli', 'NM_206933.4:c.2276delinsTAGCTA', 334683),
    ('1-216420460-C-TAGCTA', 'hg19', '', 'cli', 'NM_206933.4:c.2276delinsTAGCTA', 334683),
))
def test_api_variant_create_vcf_str(client, app, genome_version, vcf_str, api_key, caller, return_key, message):
    with app.app_context():
        if api_key == '':
            api_key = get_generic_api_key()
        data = {
            'genome_version': genome_version,
            'vcf_str': vcf_str,
            'caller': caller,
            'api_key': api_key
        }
        try:
            json_response = json.loads(client.post('/api/variant/create_vcf_str', data=data).data.decode('utf8'))
            print(json_response)
            if 'mobidetails_id' in json_response[return_key] and \
                    isinstance(json_response[return_key]['mobidetails_id'], int):
                assert json_response[return_key]['mobidetails_id'] == message
            else:
                assert message in json_response[return_key]
        except Exception:
            assert message in client.post('/api/variant/create_vcf_str', data=data).get_data()

# test GET create API


@pytest.mark.parametrize(('endpoint', 'to_find', 'http_code'), (
        # the API key is working on the dev server only
        ('create?variant_chgvs=NM_001429.4:c.3069A>G&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 'api/variant/335464/browser/', 302), # full create url
        ('create?variant_chgvs=NM_001429.4:c.3069A>G&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 'api/variant/335464/browser/', 302), # no caller
        ('create?variant_chgvs=NM_001429.4:c.3069A>G&caller=cli&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 335464, 200), # cli caller
        ('create_g?variant_ghgvs=NC_000022.11:g.41152277A>G&gene_hgnc=EP300&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 'api/variant/335464/browser/', 302), # full create_g hg38
        ('create_g?variant_ghgvs=NC_000022.11:g.41152277A>G&gene_hgnc=EP300&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 'api/variant/335464/browser/', 302), # no caller
        ('create_g?variant_ghgvs=NC_000022.11:g.41152277A>G&gene_hgnc=EP300&caller=cli&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 335464, 200), # cli caller
        ('create_g?variant_ghgvs=NC_000022.10:g.41548281A>G&gene_hgnc=EP300&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 'api/variant/335464/browser/', 302), # full create_g hg19
        ('create_rs?rs_id=rs80338902&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', b'NM_206933.4:c.2276G', 200), # full create_rs
        ('create_rs?rs_id=rs80338902&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', b'NM_206933.4:c.2276G', 200), # no caller
        ('create_rs?rs_id=rs80338902&caller=cli&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', b'NM_206933.4:c.2276G', 200), # cli caller
        ('create_vcf_str?vcf_str=17-7673822-T-TC&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', b'NM_000546.6:c.797dup', 200), # full vcf_str
        ('create_vcf_str?vcf_str=17-7673822-T-TC&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', b'NM_000546.6:c.797dup', 200), # no caller
        ('create_vcf_str?vcf_str=17-7673822-T-TC&caller=cli&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', b'NM_000546.6:c.797dup', 200), # cli caller
        ('create?variant_chgvse=NM_001429.4:c.3069A>G&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create bad param
        ('create?caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create no param
        ('create?variant_chgvs=NM_000546.5:c.797dupG', '', 302), # create no caller no api key
        ('create?variant_chgvs=NM_001429.4:c.3069A>G&caller=browser&api_key=lWjH_Y2Za-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create invalid api key
        ('create?variant_chgvs=NM_000546.5:c.797dupG&caller=cli', b'No API key provided', 200), # create cli caller no api key
        ('create_g?variant_ghgvss=NC_000017.11:g.7673825dup&gene_hgnc=TP53&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_g no caller bad param hg38
        ('create_g?variant_ghgvs=NC_000017.41:g.7673825dup&gene_hgnc=TP53&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_g no caller invalid chr hg38
        ('create_g?variant_ghgvs=NC_000017.10:g.7577143dup&gene_gnc=TP53&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_g no caller bad param hg19
        ('create_g?variant_ghgvs=NC_000017.10:g.7577143dup&gene_hgnc=TP53', '', 302), # create_g no caller no api key hg19
        ('create_g?variant_ghgvs=NC_000017.11:g.7673825dup&gene_hgnc=TP53&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYfCs', '', 302), # create_g no caller invalid api key
        ('create_rs?api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_rs no caller no rsid
        ('create_rs?rs_idz=rs80338902&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_rs no caller bad param
        ('create_rs?rs_id=rs8033s8902&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_rs no caller invalid rsid
        ('create_rs?rs_id=rs8033s8902', '', 302), # create_rs no caller no api key
        ('create_rs?rs_id=rs8033s8902?api_key=lWjH_YMZa-NuKVAiH', '', 302), # create_rs no caller invalid api key
        ('create_vcf_str?vcf_strs=17-7673822-T-TC&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_vcf_str no caller no genome bad param
        ('create_vcf_str?genome_version=hg39&vcf_str=hg39:17-7577140-T-TC&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_vcf_str no caller bad genome
        ('create_vcf_str?vcf_str=17-7673822-T-TC', '', 302), # create_vcf_str no caller no genome no api key
        ('create_vcf_str?vcf_str=17-7673822-T-TC&api_key=lWjH_YMZb-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', '', 302), # create_vcf_str no caller no genome invalid api key
))
def test_get_create_api(client, app, endpoint, to_find, http_code):
     with app.app_context():
        response = client.get('/api/variant/{0}'.format(endpoint))
        assert response.status_code == http_code
        if http_code == 302:
            print(response.headers['Location'] + 'http://localhost/{}'.format(to_find))
            assert 'http://localhost/{}'.format(to_find) == response.headers['Location']
        elif isinstance(to_find, int):
            json_response = json.loads(response.get_data().decode('utf-8'))
            print(json_response)
            assert 335464 == json_response['mobidetails_id']
        else:
            print(response.get_data()) 
            assert to_find in response.get_data() 
        

# test variant acmg class update


@pytest.mark.parametrize(('variant_id', 'acmg_class', 'api_key', 'return_key', 'message'), (
    (1, 0, 'test', 'mobidetails_error', 'Invalid API key'),
    (1, 1, '', 'mobidetails_error', 'Invalid variant id submitted'),
    (8, 0, '', 'mobidetails_error', 'Invalid parameters'),
    (8, -2, '', 'mobidetails_error', 'Invalid parameters'),
    (8, 8, '', 'mobidetails_error', 'Invalid ACMG class submitted'),
    (323866, 5, '', 'mobidetails_error', 'ACMG class already submitted by this user for this variant'),
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
