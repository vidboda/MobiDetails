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

# test modif_class


@pytest.mark.parametrize(('vf_id', 'acmg', 'acmg_com', 'return_value', 'status_code2'), (
    (5, 4, 'Variant pathogenic because of its pathogenicity:;,-', b'1-1-5', 200),
    (5, 1, 'Variant  not pathogenic because of its non-pathogenicity:;,-', b'1-1-5', 200),
    (5, 7, 'Fake acmg', b'notok', 200),
    (-5, 7, 'Fake variant', b'notok', 200),
    ('ebc', 7, 'impossible variant', b'notok', 200),
))
def test_modif_class(client, app, auth, vf_id, acmg, acmg_com, return_value, status_code2):
    assert client.get('/modif_class').status_code == 405
    with app.app_context():
        response = client.post('/modif_class',
                           data=dict(
                                variant_id=vf_id,
                                acmg_select=acmg,
                                acmg_comment=acmg_com
                            ), follow_redirects=True
                           )
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
        )
        res = curs.fetchone()
        # login(client, 'mobidetails.iurc@gmail.com', res['password'])
        auth.login('mobidetails.iurc@gmail.com', res['password'])
        response = client.post('/modif_class',
                                data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg,
                                    acmg_comment=acmg_com
                                 ), follow_redirects=True
                                )
        assert response.status_code == status_code2
        # print(response.get_data())
        # assert return_value in response.get_data()

# test remove_class


@pytest.mark.parametrize(('vf_id', 'acmg', 'return_value', 'status_code'), (
    (5, 4, b'ok', 200),
    (5, 1, b'ok', 200),
    (5, 7, b'ok', 200),
    (5, 7, b'notok', 200),
    (-5, 7, b'notok', 200),
))
def test_remove_class(client, app, auth, vf_id, acmg, return_value, status_code):
    assert client.get('/modif_class').status_code == 405
    with app.app_context():
        response = client.post('/remove_class',
                           data=dict(
                                variant_id=vf_id,
                                acmg_select=acmg,
                            ), follow_redirects=True
                           )
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
        )
        res = curs.fetchone()
        auth.login('mobidetails.iurc@gmail.com', res['password'])
        response = client.post('/remove_class',
                                data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg,
                                 ), follow_redirects=True
                                )
        assert response.status_code == status_code
        # print(response.get_data())
        # assert return_value in response.get_data()

# test send message


@pytest.mark.parametrize(('receiver_id', 'message_object', 'message', 'status_code'), (
    (1, 'test object', 'test message', 200),
    (10, 'test object', 'test message', 200),
))
def test_send_var_message(client, app, auth, receiver_id, message_object, message, status_code):
    assert client.get('/send_var_message').status_code == 405
    with app.app_context():
        response = client.post('/send_var_message',
                           data=dict(
                                receiver_id=receiver_id,
                                message_object=message_object,
                                message=message
                            ), follow_redirects=True
                           )
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
        )
        res = curs.fetchone()
        # login(client, 'mobidetails.iurc@gmail.com', res['password'])
        auth.login('mobidetails.iurc@gmail.com', res['password'])
        response = client.post('/send_var_message',
                                data=dict(
                                    receiver_id=receiver_id,
                                    message_object=message_object,
                                    message=message
                                 ), follow_redirects=True
                                )
        assert response.status_code == status_code

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


# test toggle_email_prefs


@pytest.mark.parametrize(('pref','status_code'), (
    ('t', 200),
    (None, 200),
    ('f', 200)
))
def test_toggle_email_prefs(client, app, auth, pref, status_code):
    assert client.get('/toggle_email_prefs').status_code == 405
    with app.app_context():
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
        )
        res = curs.fetchone()
        response = client.post('/toggle_email_prefs', data=dict(pref_value=pref), follow_redirects=True)
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login('mobidetails.iurc@gmail.com', res['password'])
        assert client.post('/toggle_email_prefs', data=dict(pref_value=pref), follow_redirects=True).status_code == status_code


# test favourite


@pytest.mark.parametrize(('vf_id','status_code'), (
    (5, 200),
    (None, 200),
    ('', 200)
))
def test_favourite(client, app, auth, vf_id, status_code):
    assert client.get('/favourite').status_code == 405
    with app.app_context():
        db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            "SELECT password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
        )
        res = curs.fetchone()
        response = client.post('/favourite', data=dict(vf_id=vf_id), follow_redirects=True)
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login('mobidetails.iurc@gmail.com', res['password'])
        assert client.post('/favourite', data=dict(vf_id=vf_id), follow_redirects=True).status_code == status_code



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
