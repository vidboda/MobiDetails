import pytest
import psycopg2
from MobiDetailsApp import configuration
# from MobiDetailsApp import md_utilities


def get_db():
    # db = None
    try:
        # read connection parameters
        params = configuration.mdconfig()
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            1,
            5,
            user=params['user'],
            password=params['password'],
            host=params['host'],
            port=params['port'],
            database=params['database']
        )
        # db = psycopg2.connect(**params)
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return db_pool, db_pool.getconn()
    # db = psycopg2.connect(**params)
    # except (Exception, psycopg2.DatabaseError) as error:
    #     print(error)
    # return db


# get generic mobidetails password


def get_generic_password():
    db_pool, db = get_db()
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        "SELECT email, password FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
    )
    res = curs.fetchone()
    if res is not None:
        db_pool.putconn(db)
        return res['email'], res['password']
    db_pool.putconn(db)


email, password = get_generic_password()
# test litvar


def test_litvar(client, app):
    assert client.get('/litVar').status_code == 405
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT dbsnp_id
            FROM variant_feature
            WHERE dbsnp_id IS NOT NULL
            ORDER BY random()
            LIMIT 5
            """
        )
        # https://stackoverflow.com/questions/5297396/quick-random-row-selection-in-postgres
        # discussion on how to select random rows in postgresql
        res = curs.fetchall()
        db_pool.putconn(db)
        for values in res:
            response = client.post(
                '/litVar',
                data=dict(rsid='rs{0}'.format(values['dbsnp_id']))
            )
            assert response.status_code == 200
            possible = [
                b'No match in Pubmed using LitVar API',
                b'PubMed links of articles citing this variant',
                b'The Litvar query failed'
            ]
            # https://stackoverflow.com/questions/6531482/how-to-check-if-a-string-contains-an-element-from-a-list-in-python/6531704#6531704
            print(values['dbsnp_id'])
            print(response.get_data())
            assert any(test in response.get_data() for test in possible)
            # assert b'<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>' \
            # in response.get_data() or b'PubMed IDs of articles citing this variant' in response.get_data()

# test litvar2


def test_litvar2(client, app):
    assert client.get('/litvar2').status_code == 405
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT dbsnp_id
            FROM variant_feature
            WHERE dbsnp_id IS NOT NULL
            ORDER BY random()
            LIMIT 5
            """
        )
        # https://stackoverflow.com/questions/5297396/quick-random-row-selection-in-postgres
        # discussion on how to select random rows in postgresql
        res = curs.fetchall()
        db_pool.putconn(db)
        for values in res:
            response = client.post(
                '/litvar2',
                data=dict(rsid='rs{0}'.format(values['dbsnp_id']))
            )
            assert response.status_code == 200
            possible = [
                b'No match in Pubmed using LitVar2 API',
                b'PubMed links of articles citing this variant',
                b'The Litvar2 query failed'
            ]
            # https://stackoverflow.com/questions/6531482/how-to-check-if-a-string-contains-an-element-from-a-list-in-python/6531704#6531704
            print(values['dbsnp_id'])
            print(response.get_data())
            assert any(test in response.get_data() for test in possible)
            # assert b'<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>' \
            # in response.get_data() or b'PubMed IDs of articles citing this variant' in response.get_data()

# test defgen


def test_defgen(client, app):
    assert client.get('/defgen').status_code == 405
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT feature_id, genome_version
            FROM variant OFFSET RANDOM() * (SELECT COUNT(*) FROM variant)
            LIMIT 50
            """
        )
        res = curs.fetchall()
        db_pool.putconn(db)
        for values in res:
            data_dict = dict(vfid=values['feature_id'], genome=values['genome_version'])
            response = client.post('/defgen', data=data_dict)
            assert response.status_code == 200
            assert b'Export Variant data to DEFGEN' in response.get_data()

# test intervar


def test_intervar(client, app):
    assert client.get('/intervar').status_code == 405
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            r"""
            SELECT a.genome_version, a.chr, a.pos, a.pos_ref, a.pos_alt, b.gene_symbol FROM variant a,
            variant_feature b WHERE a.feature_id = b.id AND a.genome_version = 'hg19' AND b.dna_type = 'substitution'
            AND b.start_segment_type = 'exon' AND c_name !~ '^[\*-]' AND p_name !~ '\?' ORDER BY random() LIMIT 5
            """
        )
        res = curs.fetchall()
        for values in res:
            data_dict = dict(genome=values['genome_version'], chrom=values['chr'], pos=values['pos'], ref=values['pos_ref'], alt=values['pos_alt'], gene=values['gene_symbol'])
            response = client.post('/intervar', data=data_dict)
            assert response.status_code == 200
            possible = [
                b'athogenic',
                b'lassified',
                b'enign',
                b'ncertain',
                b'wintervar looks down',
                b'hg19 reference is equal to variant: no wIntervar query'
            ]
            # https://stackoverflow.com/questions/6531482/how-to-check-if-a-string-contains-an-element-from-a-list-in-python/6531704#6531704
            print(res)
            print(response.get_data())
            assert any(test in response.get_data() for test in possible)
        db_pool.putconn(db)

# test lovd


def test_lovd(client, app):
    assert client.get('/lovd').status_code == 405
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT a.genome_version, a.chr, a.g_name, b.c_name FROM variant a, variant_feature b
            WHERE a.feature_id = b.id AND a.genome_version = 'hg19'
            ORDER BY random()
            LIMIT 5
            """
        )
        res = curs.fetchall()
        db_pool.putconn(db)
        for values in res:
            data_dict = dict(genome=values['genome_version'], chrom=values['chr'], g_name=values['g_name'], c_name='c.{}'.format(values['c_name']))
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
        # email, password = get_generic_password()
        auth.login(email, password)
        response = client.post('/modif_class',
                               data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg,
                                    acmg_comment=acmg_com
                                 ), follow_redirects=True
                               )
        assert response.status_code == status_code2

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
                                    acmg_select=acmg
                               ), follow_redirects=True
                               )
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        # email, password = get_generic_password()
        auth.login(email, password)
        response = client.post('/remove_class',
                               data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg
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
        # email, password = get_generic_password()
        auth.login(email, password)
        assert client.post(
            '/send_var_message',
            data=dict(
                receiver_id=receiver_id,
                message_object=message_object,
                message=message
             ), follow_redirects=True
            ).status_code == status_code

# test variant creation


@pytest.mark.parametrize(('new_variant', 'gene', 'acc_no', 'message1', 'message2'), (
    ('c.2276G>T', 'USH2A', 'NM_206933.4', b'already', b'successfully'),
    ('', 'USH2A', 'NM_206933', b'fill in the form', b'fill in the form'),
    ('c.216_219del', 'USH2A', 'NM_206933.4', b'already', b'successfully'),
    ('c.-104_-99dup', 'USH2A', 'NM_206933.4', b'already', b'successfully'),
    ('c.*25_*26insATG', 'USH2A', 'NM_206933.4', b'already', b'successfully'),
    ('c.651+126_651+128del', 'USH2A', 'NM_206933.4', b'already', b'successfully')
))
def test_create(client, new_variant, gene, acc_no, message1, message2):
    assert client.get('/create').status_code == 405
    data_dict = dict(new_variant=new_variant, gene=gene, acc_no=acc_no)
    response = client.post('/create', data=data_dict)
    assert response.status_code == 200
    possible = [message1, message2]
    assert any(test in response.get_data() for test in possible)
    # assert message1 in response.get_data() or message2 in response.get_data()


# test toggle_email_prefs


@pytest.mark.parametrize(('caller', 'pref', 'status_code'), (
    ('lovd_export', 't', 200),
    ('lovd_export', None, 200),
    ('lovd_export', 'f', 200),
    ('email_pref', 't', 200),
    ('email_pref', None, 200),
    ('email_pref', 'f', 200)
))
def test_toggle_prefs(client, app, auth, caller, pref, status_code):
    assert client.get('/toggle_prefs').status_code == 405
    with app.app_context():
        response = client.post('/toggle_prefs', data=dict(pref_value=pref, field=caller), follow_redirects=True)
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            '/toggle_prefs',
            data=dict(
                pref_value=pref,
                field=caller
            ),
            follow_redirects=True
        ).status_code == status_code

# test favourite


@pytest.mark.parametrize(('vf_id', 'status_code'), (
    (5, 200),
    (None, 200),
    ('', 200)
))
def test_favourite(client, app, auth, vf_id, status_code):
    assert client.get('/favourite').status_code == 405
    with app.app_context():
        response = client.post('/favourite', data=dict(vf_id=vf_id), follow_redirects=True)
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            '/favourite',
            data=dict(vf_id=vf_id),
            follow_redirects=True
        ).status_code == status_code

# test empty_favourite_list


def test_empty_favourite_list(client, app, auth):
    assert client.get('/empty_favourite_list').status_code == 405
    with app.app_context():
        response = client.post(
            '/empty_favourite_list',
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            '/empty_favourite_list',
            follow_redirects=True
        ).status_code == 200

# test toggle_lock_variant_list


def test_toggle_lock_variant_list(client, app, auth):
    assert client.get('/empty_favourite_list').status_code == 405
    with app.app_context():
        response = client.get(
            '/toggle_lock_variant_list/mobidetails_list_1',
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.get(
            '/toggle_lock_variant_list/mobidetails_list_1',
            follow_redirects=True
        ).status_code == 200

# test variants group(list) creation


def test_create_unique_url(client, app, auth):
    assert client.get('/create_unique_url').status_code == 405
    with app.app_context():
        response = client.post(
            '/create_unique_url',
            data=dict(list_name='mobidetails_list_1'),
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            '/create_unique_url',
            data=dict(list_name='mobidetails_list_1'),
            follow_redirects=True
        ).status_code == 200
        assert b'already' in response.get_data()

# test delete_variant_list


@pytest.mark.parametrize(('list_name', 'return_value'), (
    ('mobidetails_list_1', 200),
    ('test', 200),
    (9, 200),
))
def test_delete_variant_list(client, app, auth, list_name, return_value):
    assert client.get('/delete_variant_list').status_code == 404
    with app.app_context():
        response = client.get(
            '/delete_variant_list/{}'.format(list_name),
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.get(
            '/delete_variant_list/{}'.format(list_name),
            follow_redirects=True
        ).status_code == return_value
        assert b'check_login_form' in client.get(
            '/delete_variant_list/{}'.format(list_name),
            follow_redirects=True
        ).get_data()

# test autocomplete


@pytest.mark.parametrize(('query', 'return_value'), (
    # ('c.100C>', b'["NM_206933.2:c.100C>A", "NM_001197104.1:c.100C>G", "NM_206933.2:c.100C>G", "NM_206933.2:c.100C>T"]'),
    # ('USH2', b'["USH2A"]'),
    # ('blabla', b'[]'),
    # ('c.blabla', b'')
    ('c.100C>', b'NM_206933.2:c.100C>A'),
    ('USH2', b'USH2A'),
    ('blabla', b'[]'),
    ('c.blabla', b'')
))
def test_autocomplete(client, app, query, return_value):
    assert client.get('/autocomplete').status_code == 405
    response = client.post('/autocomplete', data=dict(query_engine=query))
    print(response.get_data())
    assert return_value in response.get_data()

# test autocomplete_var


@pytest.mark.parametrize(('query', 'acc_no', 'return_value', 'http_code'), (
    ('c.100C>', 'NM_206933.2', b'["c.100C>A", "c.100C>G", "c.100C>T"]', 200),
    ('USH2', 'NM_206933.4', b'', 204),
    ('blabla', 'NM_206933.4', b'', 204),
    ('c.blabla', 'NM_206933.4', b'', 204),
    ('c.actg', 'NM_206933.4', b'', 204),
    ('c.ATCG', 'NM_206933.4', b'[]', 200)
))
def test_autocomplete_var(client, query, acc_no, return_value, http_code):
    assert client.get('/autocomplete_var').status_code == 405
    data_dict = dict(query_engine=query, acc_no=acc_no)
    response = client.post('/autocomplete_var', data=data_dict)
    print(response.get_data())
    print(response.status_code)
    assert return_value == response.get_data()
    assert http_code == response.status_code

# test panelApp


@pytest.mark.parametrize(('gene_symbol', 'return_value', 'http_code'), (
    ('USH2A', b'panelapp.genomicsengland.co.uk', 200),
    ('F91', b'No entry in panelApp for this gene', 200),
    (91, b'No entry in panelApp for this gene', 200)
))
def test_is_panelapp_entity(client, gene_symbol, return_value, http_code):
    assert client.get('/is_panelapp_entity').status_code == 405
    data_dict = dict(gene_symbol=gene_symbol)
    response = client.post('/is_panelapp_entity', data=data_dict)
    print(response.get_data())
    print(response.status_code)
    assert return_value in response.get_data()
    assert http_code == response.status_code

# test SPiP


@pytest.mark.parametrize(('gene_symbol', 'nm_acc', 'c_name', 'variant_id'), (
    ('USH2A', 'NM_206933', 'c.-205+40A>G', '641'),
    ('BRCA1', 'NM_007294', 'c.213-6T>G', '157446'),
    ('BRCA1', 'NM_007294', 'c.441+36_441+53delinsG', '239248'),
    ('USH2A', 'NM_206933', 'c.1972-12dup', '97698'),
    ('USH2A', 'NM_206933', 'c.7061G>A', '952'),
    ('USH2A', 'NM_206933', 'c.11389+8_11389+10delinsT', '202888'),
    ('USH2A', 'NM_206933', 'c.11549-5del', '110'),
))
def test_spip(client, gene_symbol, nm_acc, c_name, variant_id):
    assert client.get('/spip').status_code == 405
    data_dict = dict(gene_symbol=gene_symbol, nm_acc=nm_acc, c_name=c_name, variant_id=variant_id)
    response = client.post('/spip', data=data_dict)
    print(response.get_data())
    print(response.status_code)
    assert b'Interpretation' in response.get_data()

# test spliceai lookup


@pytest.mark.parametrize(('variant', 'transcript', 'return_value'), (
    ('chr1-216247118-C-A', 'NM_206933.4', b'(-419)'),
    ('chr17-43095795-TCTACCCACTCTCTTTTCAGTGCCTGTTAAGTTGGC-T', 'NM_007294.4', b'(127)'),
    ('chr17-43104962-A-C', 'NM_007294.4', b'(-94)'),
    ('chr1-216415508-CTTTTTTT-C', 'NM_206933.4', b'(-362)'),
    ('chr1-216247056-A-AGGTGTC', 'NM_206933.4', b'(-471)'),
    ('chr1-215625755-G-GCAT', 'NM_206933.4', b'(-324)'),
    ('chr1-215680269-CAG-TTTA', 'NM_206933.4', b'No results')
))
def test_spliceai_lookup(client, variant, transcript, return_value):
    assert client.get('/spliceai_lookup').status_code == 405
    data_dict = dict(variant=variant, transcript=transcript)
    response = client.post('/spliceai_lookup', data=data_dict)
    print(response.get_data())
    print(response.status_code)
    assert return_value in response.get_data()

# test spliceai visual


@pytest.mark.parametrize(('gene', 'chrom', 'pos', 'ref', 'alt', 'variant_id', 'strand', 'ncbi_transcript', 'caller', 'return_value'), (
    ('USH2A', '1', 216325499, 'G', 'T', 334809, '-', 'NM_206933.4', 'automatic', b'ok'),
    ('USH2A', '1', 216325499, 'G', 'T', 334809, '-', 'NM_206933.2', 'automatic', b'ok'),
    ('USH2A', '1', 216325499, 'G', 'T', 334809, '-', 'NM_206933.X', 'automatic', b'<p style="color:red">Bad params for SpliceAI-visual.</p>'),
    ('TTN', '2', '178599063', 'CT', 'GA', 334804, '-', 'NM_001267550.2', 'automatic', b'ok'),
))
def test_spliceaivisual(client, gene, chrom, pos, ref, alt, variant_id, strand, ncbi_transcript, caller, return_value):
    assert client.get('/spliceaivisual').status_code == 405
    data_dict = dict(chrom=chrom, pos=pos, ref=ref, alt=alt, variant_id=variant_id, strand=strand, ncbi_transcript=ncbi_transcript, gene_symbol=gene, caller=caller)
    response = client.post('/spliceaivisual', data=data_dict)
    print(response.get_data())
    print(response.status_code)
    assert return_value in response.get_data()
