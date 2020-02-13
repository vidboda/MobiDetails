import pytest
import psycopg2
from MobiDetailsApp.db import get_db

# test litvar


def test_litvar(client, app):
    assert client.get('/litVar').status_code == 405
    with app.app_context():
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT dbsnp_id FROM variant_feature WHERE dbsnp_id IS NOT NULL ORDER BY random() LIMIT 5"
        )
        # https://stackoverflow.com/questions/5297396/quick-random-row-selection-in-postgres
        # discussion on how to select random rows in postgresql
        res = curs.fetchall()
        for values in res:
            response = client.post('/litVar', data=dict(rsid=values['dbsnp_id']))
            assert response.status_code == 200
            possible = [
                b'<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>',
                b'PubMed IDs of articles citing this variant'
            ]
            # https://stackoverflow.com/questions/6531482/how-to-check-if-a-string-contains-an-element-from-a-list-in-python/6531704#6531704
            assert any(test in response.get_data() for test in possible)
            # assert b'<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>' \
            # in response.get_data() or b'PubMed IDs of articles citing this variant' in response.get_data()

# test defgen


def test_defgen(client, app):
    assert client.get('/defgen').status_code == 405
    with app.app_context():
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT feature_id, genome_version FROM variant OFFSET RANDOM() * (SELECT COUNT(*) FROM variant) LIMIT 50"
        )
        res = curs.fetchall()
        for values in res:
            data_dict = dict(vfid=values['feature_id'], genome=values['genome_version'])
            response = client.post('/defgen', data=data_dict)
            assert response.status_code == 200
            assert b'Export Variant data to DEFGEN' in response.get_data()

# test intervar


def test_intervar(client, app):
    assert client.get('/intervar').status_code == 405
    with app.app_context():
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT a.genome_version, a.chr, a.pos, a.pos_ref, a.pos_alt FROM variant a, variant_feature b WHERE \
            a.feature_id = b.id AND a.genome_version = 'hg19' AND b.dna_type = 'substitution' AND \
            b.start_segment_type = 'exon' AND c_name !~ '^[\*-]' AND p_name !~ '\?' ORDER BY random() LIMIT 5"
        )
        res = curs.fetchall()
        for values in res:
            data_dict = dict(genome=values['genome_version'], chrom=values['chr'], pos=values['pos'], ref=values['pos_ref'], alt=values['pos_alt'])
            response = client.post('/intervar', data=data_dict)
            assert response.status_code == 200
            possible = [b'athogenic', b'lassified', b'enign', b'ncertain']
            # https://stackoverflow.com/questions/6531482/how-to-check-if-a-string-contains-an-element-from-a-list-in-python/6531704#6531704
            assert any(test in response.get_data() for test in possible)
            # assert b'athogenic' in response.get_data() or b'lassified' in response.get_data() or b'enign' in \
            # response.get_data() or b'ncertain' in response.get_data()

# test lovd


def test_lovd(client, app):
    assert client.get('/lovd').status_code == 405
    with app.app_context():
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT a.genome_version, a.chr, a.g_name, b.c_name FROM variant a, variant_feature b WHERE \
            a.feature_id = b.id AND a.genome_version = 'hg19' ORDER BY random() LIMIT 5"
        )
        res = curs.fetchall()
        for values in res:
            data_dict = dict(genome=values['genome_version'], chrom=values['chr'], g_name=values['g_name'], c_name=values['c_name'])
            assert client.post('/lovd', data=data_dict).status_code == 200

# test variant creation


@pytest.mark.parametrize(('new_variant', 'gene', 'acc_no', 'acc_version', 'message1', 'message2'), (
    ('c.1A>T', 'USH2A', 'NM_206933', '2', b'already', b'successfully'),
    ('', 'USH2A', 'NM_206933', '2', b'fill in the form', b'fill in the form'),
))
def test_create(client, app, new_variant, gene, acc_no, acc_version, message1, message2):
    assert client.get('/create').status_code == 405
    data_dict = dict(new_variant=new_variant, gene=gene, acc_no=acc_no, acc_version=acc_version)
    response = client.post('/create', data=data_dict)
    assert response.status_code == 200
    possible = [message1, message2]
    assert any(test in response.get_data() for test in possible)
    # assert message1 in response.get_data() or message2 in response.get_data()

# test favourite - login required - to be developped?


def login(client, email, password):
    return client.post('/login', data=dict(
            email=email,
            password=password
        ),
        follow_redirects=True
    )


def logout(client):
    return client.get('/logout', follow_redirects=True)


def test_favourite(client, app):
    assert client.get('/favourite').status_code == 405
    with app.app_context():
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
        )
        res = curs.fetchone()
        assert client.post('/favourite', data=dict(vf_id=5)).status_code == 302
        login(client, 'mobidetails.iurc@gmail.com', res['password'])
        # print(client.post('/favourite', data=dict(vf_id=5), follow_redirects=True).get_data())
        assert client.post('/favourite', data=dict(vf_id=5), follow_redirects=True).status_code == 200
        assert client.post('/favourite', data=dict(vf_id=None), follow_redirects=True).status_code == 200
        assert client.post('/favourite', data=dict(vf_id=''), follow_redirects=True).status_code == 200


# test autocomplete


@pytest.mark.parametrize(('query', 'return_value'), (
    ('c.100C>', b'["c.100C>T"]'),
    ('USH2', b'["USH2A"]'),
    ('blabla', b'[]'),
    ('c.blabla', b'[]')
))
def test_autocomplete(client, app, query, return_value):
    assert client.get('/autocomplete').status_code == 405
    response = client.post('/autocomplete', data=dict(query_engine=query))
    print(response.get_data())
    assert return_value == response.get_data()

# test autocomplete_var


@pytest.mark.parametrize(('query', 'gene', 'return_value', 'http_code'), (
    ('c.100C>', 'USH2A', b'["c.100C>T"]', 200),
    ('USH2', 'USH2A', b'', 204),
    ('blabla', 'USH2A', b'', 204),
    ('c.blabla', 'USH2A', b'[]', 200)
))
def test_autocomplete_var(client, app, query, gene, return_value, http_code):
    assert client.get('/autocomplete_var').status_code == 405
    data_dict = dict(query_engine=query, gene=gene)
    response = client.post('/autocomplete_var', data=data_dict)
    print(response.status_code)
    assert return_value == response.get_data()
    assert http_code == response.status_code
