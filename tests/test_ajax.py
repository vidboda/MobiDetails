from flask import url_for
import pytest
import psycopg2
import psycopg2.extras
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
        "SELECT email, password FROM mobiuser WHERE id = 1"
    )
    res = curs.fetchone()
    if res is not None:
        db_pool.putconn(db)
        return res['email'], res['password']
    db_pool.putconn(db)
    return None, None


email, password = get_generic_password()

# test litvar2


def test_litvar2(client, app):
    with app.app_context():
        assert client.get(url_for('ajax.litvar2')).status_code == 405
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
                url_for('ajax.litvar2'),
                data=dict(rsid='rs{0}'.format(values['dbsnp_id']))
            )
            assert response.status_code == 200
            possible = [
                b'Currently no match in PubMed using LitVar2 API',
                b'Full details and complete results available at',
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
    with app.app_context():
        assert client.get(url_for('ajax.defgen')).status_code == 405
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
            response = client.post(url_for('ajax.defgen'), data=data_dict)
            assert response.status_code == 200
            assert b'Export Variant data to DEFGEN' in response.get_data()

# test intervar


def test_intervar(client, app):
    with app.app_context():
        assert client.get(url_for('ajax.intervar')).status_code == 405
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            r"""
            SELECT a.genome_version, a.chr, a.pos, a.pos_ref, a.pos_alt, b.gene_symbol FROM variant a,
            variant_feature b WHERE a.feature_id = b.id AND a.genome_version = 'hg38' AND b.dna_type = 'substitution'
            AND b.start_segment_type = 'exon' AND c_name !~ '^[\*-]' AND p_name !~ '\?' ORDER BY random() LIMIT 5
            """
        )
        res = curs.fetchall()
        for values in res:
            data_dict = dict(genome=values['genome_version'], chrom=values['chr'], pos=values['pos'], ref=values['pos_ref'], alt=values['pos_alt'], gene=values['gene_symbol'])
            response = client.post(url_for('ajax.intervar'), data=data_dict)
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


# test genebe


def test_genebe(client, app):
    with app.app_context():
        assert client.get(url_for('ajax.genebe')).status_code == 405
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            r"""
            SELECT a.genome_version, a.chr, a.pos, a.pos_ref, a.pos_alt, b.gene_symbol, b.refseq FROM variant a,
            variant_feature b WHERE a.feature_id = b.id AND a.genome_version = 'hg38' ORDER BY random() LIMIT 15
            """
        )
        res = curs.fetchall()
        for values in res:
            data_dict = dict(genome=values['genome_version'], chrom=values['chr'], pos=values['pos'], ref=values['pos_ref'], alt=values['pos_alt'], gene=values['gene_symbol'], ncbi_transcript=values['refseq'])
            response = client.post(url_for('ajax.genebe'), data=data_dict)
            assert response.status_code == 200
            possible = [
                b'athogenic',
                b'lassified',
                b'enign',
                b'ncertain',
                b'MD failed to query genebe.net',
                b'reference is equal to variant: no GeneBe query',
                # b'GeneBe returned no classification for this variant or MD was unable to interpret it'
            ]
            # https://stackoverflow.com/questions/6531482/how-to-check-if-a-string-contains-an-element-from-a-list-in-python/6531704#6531704
            print(values)
            print(response.get_data())
            assert any(test in response.get_data() for test in possible)
        db_pool.putconn(db)

# test lovd


def test_lovd(client, app):
    with app.app_context():
        assert client.get(url_for('ajax.lovd')).status_code == 405
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT a.genome_version, a.chr, a.g_name, b.c_name, b.gene_symbol, b.refseq
            FROM variant a, variant_feature b
            WHERE a.feature_id = b.id AND a.genome_version = 'hg19'
            ORDER BY random()
            LIMIT 10
            """
        )
        res = curs.fetchall()
        db_pool.putconn(db)
        for values in res:
            data_dict = dict(genome=values['genome_version'], chrom=values['chr'], g_name=values['g_name'], c_name='c.{}'.format(values['c_name']), gene=values['gene_symbol'], ncbi_transcript=values['refseq'])
            print(data_dict)
            assert client.post(url_for('ajax.lovd'), data=data_dict).status_code == 200

# test modif_class


@pytest.mark.parametrize(('vf_id', 'acmg', 'acmg_com', 'status_code2'), (
    (5, 4, 'Variant pathogenic because of its pathogenicity:;,-', 200),
    (5, 1, 'Variant  not pathogenic because of its non-pathogenicity:;,-', 200),
    (5, 8, 'test risk factor code', 200),
    (5, 8, 'Fake acmg', 200),
    (-5, 7, 'Fake variant', 200),
    ('ebc', 7, 'impossible variant', 200),
))
def test_modif_class(client, app, auth, vf_id, acmg, acmg_com, status_code2):
    with app.app_context():
        assert client.get(url_for('ajax.modif_class')).status_code == 405
        response = client.post(url_for('ajax.modif_class'),
                               data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg,
                                    acmg_comment=acmg_com
                                ), follow_redirects=True
                               )
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        response = client.post(url_for('ajax.modif_class'),
                               data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg,
                                    acmg_comment=acmg_com
                                 ), follow_redirects=True
                               )
        assert response.status_code == status_code2

# test remove_class


@pytest.mark.parametrize(('vf_id', 'acmg', 'status_code'), (
    (5, 4, 200),
    (5, 1, 200),
    (5, 7, 200),
    (5, 7, 200),
    (-5, 7, 200),
))
def test_remove_class(client, app, auth, vf_id, acmg, status_code):
    with app.app_context():
        assert client.get(url_for('ajax.modif_class')).status_code == 405
        response = client.post(url_for('ajax.remove_class'),
                               data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg
                               ), follow_redirects=True
                               )
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        response = client.post(url_for('ajax.remove_class'),
                               data=dict(
                                    variant_id=vf_id,
                                    acmg_select=acmg
                               ), follow_redirects=True
                               )
        assert response.status_code == status_code

# test send message


@pytest.mark.parametrize(('receiver_id', 'message_object', 'message', 'status_code'), (
    (1, 'test object', 'test message', 200),
    (10, 'test object', 'test message', 200),
    (10, 'Object: [MobiDetails - Query from pytest]', 'test message', 200),
))
def test_send_var_message(client, app, auth, receiver_id, message_object, message, status_code):
    with app.app_context():
        assert client.get(url_for('ajax.send_var_message')).status_code == 405
        response = client.post(url_for('ajax.send_var_message'),
                               data=dict(
                                    receiver_id=receiver_id,
                                    message_object=message_object,
                                    message=message
                               ), follow_redirects=True
                               )
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            url_for('ajax.send_var_message'),
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
def test_create(client, app, new_variant, gene, acc_no, message1, message2):
    with app.app_context():
        assert client.get(url_for('ajax.create')).status_code == 405
        data_dict = dict(new_variant=new_variant, gene=gene, acc_no=acc_no)
        response = client.post(url_for('ajax.create'), data=data_dict)
        assert response.status_code == 200
        possible = [message1, message2]
        assert any(test in response.get_data() for test in possible)

# test toggle_prefs


@pytest.mark.parametrize(('caller', 'pref', 'status_code'), (
    ('lovd_export', 't', 200),
    ('lovd_export', None, 200),
    ('lovd_export', 'f', 200),
    ('email_pref', 't', 200),
    ('email_pref', None, 200),
    ('clinvar_check', 'f', 200),
    ('clinvar_check', 't', 200),
    ('auto_add2clinvar_check', 'f', 200),
    ('auto_add2clinvar_check', None, 200)
))
def test_toggle_prefs(client, app, auth, caller, pref, status_code):
    with app.app_context():
        assert client.get(url_for('ajax.toggle_prefs')).status_code == 405
        response = client.post(url_for('ajax.toggle_prefs'), data=dict(pref_value=pref, field=caller), follow_redirects=True)
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            url_for('ajax.toggle_prefs'),
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
    with app.app_context():
        assert client.get(url_for('ajax.favourite')).status_code == 405
        response = client.post(url_for('ajax.favourite'), data=dict(vf_id=vf_id), follow_redirects=True)
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            url_for('ajax.favourite'),
            data=dict(vf_id=vf_id),
            follow_redirects=True
        ).status_code == status_code

# test empty_favourite_list


def test_empty_favourite_list(client, app, auth):
    with app.app_context():
        assert client.get(url_for('ajax.empty_favourite_list')).status_code == 405
        response = client.post(
            url_for('ajax.empty_favourite_list'),
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            url_for('ajax.empty_favourite_list'),
            follow_redirects=True
        ).status_code == 200

# test toggle_lock_variant_list


def test_toggle_lock_variant_list(client, app, auth):
    with app.app_context():
        assert client.get(url_for('ajax.empty_favourite_list')).status_code == 405
        response = client.get(
            url_for('ajax.toggle_lock_variant_list', list_name='MYO7A_LGM_2021'),
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.get(
            url_for('ajax.toggle_lock_variant_list', list_name='MYO7A_LGM_2021'),
            follow_redirects=True
        ).status_code == 200

# test variants group(list) creation


def test_create_unique_url(client, app, auth):
    with app.app_context():
        assert client.get(url_for('ajax.create_unique_url')).status_code == 405
        response = client.post(
            url_for('ajax.create_unique_url'),
            data=dict(list_name='MYO7A_LGM_2021'),
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.post(
            url_for('ajax.create_unique_url'),
            data=dict(list_name='MYO7A_LGM_2021'),
            follow_redirects=True
        ).status_code == 200
        assert b'already' in response.get_data()


# test delete_variant_list


@pytest.mark.parametrize(('list_name', 'return_value'), (
    ('MYO7A_LGM_2021', 200),
    ('test', 200),
    (9, 200),
))
def test_delete_variant_list(client, app, auth, list_name, return_value):
    with app.app_context():
        assert client.get(url_for('ajax.delete_variant_list', list_name='')).status_code == 404
        response = client.get(
            url_for('ajax.delete_variant_list', list_name=list_name),
            follow_redirects=True
        )
        print(response.get_data())
        assert b'check_login_form' in response.get_data()  # means we are in the login page
        auth.login(email, password)
        assert client.get(
            url_for('ajax.delete_variant_list', list_name=list_name),
            follow_redirects=True
        ).status_code == return_value
        assert b'check_login_form' in client.get(
            url_for('ajax.delete_variant_list', list_name=list_name),
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
    with app.app_context():
        assert client.get(url_for('ajax.autocomplete')).status_code == 405
        response = client.post(url_for('ajax.autocomplete'), data=dict(query_engine=query))
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
def test_autocomplete_var(client, app, query, acc_no, return_value, http_code):
    with app.app_context():
        assert client.get(url_for('ajax.autocomplete_var')).status_code == 405
        data_dict = dict(query_engine=query, acc_no=acc_no)
        response = client.post(url_for('ajax.autocomplete_var'), data=data_dict)
        print(response.get_data())
        print(response.status_code)
        assert return_value == response.get_data()
        assert http_code == response.status_code

# test panelApp


@pytest.mark.parametrize(('gene_symbol', 'return_value', 'http_code'), (
    ('USH2A', b'panelapp.genomicsengland.co.uk', 200),
    ('F91', b'No entry in panelApp for this gene', 200),
    (91, b'No entry in panelApp for this gene', 200),
    ('HLA-A', b'panelapp.genomicsengland.co.uk', 200),
    ('HLA-DPA1:', b'Invalid character in the gene symbol', 200)
))
def test_is_panelapp_entity(client, app, gene_symbol, return_value, http_code):
    with app.app_context():
        assert client.get(url_for('ajax.is_panelapp_entity')).status_code == 405
        data_dict = dict(gene_symbol=gene_symbol)
        response = client.post(url_for('ajax.is_panelapp_entity'), data=data_dict)
        print(response.get_data())
        print(response.status_code)
        assert return_value in response.get_data()
        assert http_code == response.status_code

# test SPiP


@pytest.mark.parametrize(('gene_symbol', 'nm_acc', 'c_name', 'variant_id'), (
    ('USH2A', 'NM_206933.2', 'c.-205+40A>G', '641'),
    ('BRCA1', 'NM_007294.3', 'c.213-6T>G', '157446'),
    ('BRCA1', 'NM_007294.3', 'c.441+36_441+53delinsG', '239248'),
    ('USH2A', 'NM_206933.2', 'c.1972-12dup', '97698'),
    ('USH2A', 'NM_206933.2', 'c.7061G>A', '952'),
    ('USH2A', 'NM_206933.2', 'c.11389+8_11389+10delinsT', '202888'),
    ('USH2A', 'NM_206933.2', 'c.11549-5del', '110'),
))
def test_spip(client, app, gene_symbol, nm_acc, c_name, variant_id):
    with app.app_context():
        assert client.get(url_for('ajax.spip')).status_code == 405
        data_dict = dict(gene_symbol=gene_symbol, nm_acc=nm_acc, c_name=c_name, variant_id=variant_id)
        response = client.post(url_for('ajax.spip'), data=data_dict)
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
    ('chr1-215680269-CAG-TTTA', 'NM_206933.4', b'0.00 (-27)')
))
def test_spliceai_lookup(client, app, variant, transcript, return_value):
    with app.app_context():
        assert client.get(url_for('ajax.spliceai_lookup')).status_code == 405
        data_dict = dict(variant=variant, transcript=transcript)
        response = client.post(url_for('ajax.spliceai_lookup'), data=data_dict)
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
def test_spliceaivisual(client, app, gene, chrom, pos, ref, alt, variant_id, strand, ncbi_transcript, caller, return_value):
    with app.app_context():
        assert client.get(url_for('ajax.spliceaivisual')).status_code == 405
        data_dict = dict(chrom=chrom, pos=pos, ref=ref, alt=alt, variant_id=variant_id, strand=strand, ncbi_transcript=ncbi_transcript, gene_symbol=gene, caller=caller)
        response = client.post(url_for('ajax.spliceaivisual'), data=data_dict)
        print(response.get_data())
        print(response.status_code)
        assert return_value in response.get_data()

# test mobideep


@pytest.mark.parametrize(('mobideep_input', 'return_value'), (
    ('21.20 -7.81 1.000 0.999 6.273', b'9.5732'),
    ('4.43 -0.04 0.314 0.000 0.253', b'0.1187'),
    ('-4.43 -0.04 0.314 0.000 0.253', b'Unable to run MobiDeep API'),
    ('0.04 0.314 0.000 0.253', b'Unable to run MobiDeep API'),
))
def test_mobideep(client, app, mobideep_input, return_value):
    with app.app_context():
        assert client.get(url_for('ajax.mobideep')).status_code == 405
        data_dict = dict(mobideep_input_scores=mobideep_input)
        response = client.post(url_for('ajax.mobideep'), data=data_dict)
        print(response.get_data())
        print(response.status_code)
        assert return_value in response.get_data()