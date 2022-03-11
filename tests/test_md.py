import pytest
from test_ajax import get_db


# def test_homepage(client):
#     assert client.get('/').status_code == 200


def test_about(client):
    assert client.get('/about').status_code == 200


def test_gene_page(client, app):
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor()
        curs.execute(
            """
            SELECT name[1]
            FROM gene
            LIMIT 50
            """,
        )
        res = curs.fetchall()
        db_pool.putconn(db)
        for name in res:
            assert client.get('/gene/{}'.format(name[0])).status_code == 200
#             gene_page_result(client, name)
# def gene_page_result(client, name):
#     assert client.get('/gene/{}'.format(name[0])).status_code == 200


def test_genes_page(client):
    assert client.get('/genes').status_code == 200


def test_vars_page(client):
    assert client.get('/vars/PCDH15').status_code == 200


def test_basic_variant_page(client):
    assert client.get('/variant/5').status_code == 302


@pytest.mark.parametrize(('t_search', 'url', 'status_code'), (
    ('R34X', b'api/variant/334419/browser/', 200),
    ('R34*', b'api/variant/334419/browser/', 200),
    ('p.Arg34*', b'api/variant/334419/browser/', 200),
    ('p.(Arg34Ter)', b'api/variant/334419/browser/', 200),
    ('p.(Arg34*)', b'api/variant/334419/browser/', 200),
    ('c.100C>T', b'api/variant/334419/browser/', 200),
    ('c.100c>t', b'api/variant/334419/browser/', 200),
    ('c.100c>T', b'api/variant/334419/browser/', 200),
    ('g.6212C>T', 'api/variant/334419/browser/', 302),
    ('chr1:g.216595579G>A', b'api/variant/334419/browser/', 200),
    ('chr1:g.216422237G>A', b'api/variant/334419/browser/', 200),
    ('chr1:g.216422237g>A', b'api/variant/334419/browser/', 200),
    # ('NC_000001.11:g.216422237G>A', b'api/variant/334419/browser/', 200),
    ('NC_000004.12:g.76311072A>C;STBD1', 'api/variant/create_g?variant_ghgvs=NC_000004.12%3Ag.76311072A%3EC&gene_hgnc=STBD1&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs', 302),
    ('USH2A', 'gene/USH2A', 302),
    ('c.2447_2461delGAGGGGAAGTAGAGG', 'api/variant/71/browser/', 302),
    ('c.2447_2461del', 'api/variant/71/browser/', 302),
    ('p.Gly816_Glu820del', 'api/variant/71/browser/', 302),
    ('p.G816_E820del', 'api/variant/71/browser/', 302),
    ('p.Leu1278del', 'api/variant/68208/browser/', 302),
    ('p.L1278del', 'api/variant/68208/browser/', 302),
    ('NM_206933.2:c.2299del', ('api/variant/create?variant_chgvs=NM_206933.2%3Ac.2299del&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs'), 302),
    ('NM_206933.2(USH2A):c.2299del', ('api/variant/create?variant_chgvs=NM_206933.2%3Ac.2299del&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs'), 302),
    ('MYO7A', 'gene/MYO7A', 302),
    ('myo7a', 'gene/MYO7A', 302),
    ('mYo7A', 'gene/MYO7A', 302),
    ('NM_206933', 'gene/USH2A', 302),
    ('NM_206933.', 'gene/USH2A', 302),
    ('NM_206933.3', 'gene/USH2A', 302),
    ('NM_206933.33', 'gene/USH2A', 302),
    ('GPR98', 'gene/ADGRV1', 302),
    ('c12ORF4', 'gene/C12orf4', 302),
    ('C12oRf4', 'gene/C12orf4', 302),
    ('C12orf4', 'gene/C12orf4', 302),
    ('rs1057516028', 'api/variant/51689/browser/', 302),
    ('S100G', 'gene/S100G', 302),
    ('S100g', 'gene/S100G', 302),
    ('S100g', 'gene/S100G', 302),
    ('1-216422237:G-A', b'api/variant/334419/browser/', 307),
    ('hg38-1-216422237-G-A', b'api/variant/334419/browser/', 307),
    ('grCh38:1-216422237-G-A', b'api/variant/334419/browser/', 307),
    ('Hg19:1:216595579-G-A', b'api/variant/334419/browser/', 307),
    ('GrcH37:1-216422237-G-A', b'api/variant/334419/browser/', 307),
    ('GrcH37_1_216422237_G_A', b'api/variant/334419/browser/', 307),
    ('GrcH37:1_216422237-G-A', b'api/variant/334419/browser/', 307),
    ))
def test_search_engine(client, app, t_search, url, status_code):
    response = client.post(
        '/search_engine',
        data={'search': t_search}
    )
    print(response.status_code)
    if status_code == 200:
        print(response.get_data())
        assert url in response.get_data()
    elif status_code == 302:
        print(response.headers['Location'] + 'http://localhost/{}'.format(url))
        assert 'http://localhost/{}'.format(url) == response.headers['Location']
    else:
        assert status_code == response.status_code

# test all variants in dev db except c.1A>T (too numerous as used to test variant creation)


def test_variant_page(client, app):
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
            """
            # LIMIT 100  WHERE prot_type = 'missense'",  #  ORDER BY random() LIMIT 500
        )
        res = curs.fetchall()
        db_pool.putconn(db)
        for variant_id in res:
            print(variant_id[0])
            assert client.get('/api/variant/{}/browser/'.format(variant_id[0])).status_code == 200
