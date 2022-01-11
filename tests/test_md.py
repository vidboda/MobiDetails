import pytest
from test_ajax import get_db


# def test_homepage(client):
#     assert client.get('/').status_code == 200


def test_about(client):
    assert client.get('/about').status_code == 200


def test_gene_page(client, app):
    with app.app_context():
        db = get_db()
        curs = db.cursor()
        curs.execute(
            """
            SELECT name[1]
            FROM gene
            LIMIT 50
            """,
        )
        res = curs.fetchall()
        for name in res:
            assert client.get('/gene/{}'.format(name[0])).status_code == 200
        db.close()
#             gene_page_result(client, name)
# def gene_page_result(client, name):
#     assert client.get('/gene/{}'.format(name[0])).status_code == 200


def test_genes_page(client):
    assert client.get('/genes').status_code == 200


def test_vars_page(client):
    assert client.get('/vars/PCDH15').status_code == 200


def test_basic_variant_page(client):
    assert client.get('/variant/5').status_code == 302


@pytest.mark.parametrize(('t_search', 'url'), (
    ('R34X', 'api/variant/323875/browser/'),
    ('R34*', 'api/variant/323875/browser/'),
    ('p.Arg34*', 'api/variant/323875/browser/'),
    ('p.(Arg34Ter)', 'api/variant/323875/browser/'),
    ('p.(Arg34*)', 'api/variant/323875/browser/'),
    ('c.100C>T', 'api/variant/323875/browser/'),
    ('c.100c>t', 'api/variant/323875/browser/'),
    ('c.100c>T', 'api/variant/323875/browser/'),
    ('g.6212C>T', 'api/variant/323875/browser/'),
    ('chr1:g.216595579G>A', 'api/variant/323875/browser/'),
    ('chr1:g.216422237G>A', 'api/variant/323875/browser/'),
    ('chr1:g.216422237g>A', 'api/variant/323875/browser/'),
    ('NC_000001.11:g.216422237G>A', 'api/variant/323875/browser/'),
    ('NC_000004.12:g.76311072A>C;STBD1', 'api/variant/create_g?variant_ghgvs=NC_000004.12%3Ag.76311072A%3EC&gene_hgnc=STBD1&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs'),
    ('USH2A', 'gene/USH2A'),
    ('c.2447_2461delGAGGGGAAGTAGAGG', 'api/variant/323888/browser/'),
    ('c.2447_2461del', 'api/variant/323888/browser/'),
    ('p.Gly816_Glu820del', 'api/variant/323888/browser/'),
    ('p.G816_E820del', 'api/variant/323888/browser/'),
    ('p.Leu1278del', 'api/variant/323889/browser/'),
    ('p.L1278del', 'api/variant/323889/browser/'),
    ('NM_206933.2:c.2299del', ('api/variant/create?variant_chgvs=NM_206933.2%3Ac.2299del&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs')),
    ('NM_206933.2(USH2A):c.2299del', ('api/variant/create?variant_chgvs=NM_206933.2%3Ac.2299del&caller=browser&api_key=lWjH_YMZa-NuKVAiHyDsi7yyu5aZXpCvo1Wf_zSYPCs')),
    ('MYO7A', 'gene/MYO7A'),
    ('myo7a', 'gene/MYO7A'),
    ('mYo7A', 'gene/MYO7A'),
    ('NM_206933', 'gene/USH2A'),
    ('NM_206933.', 'gene/USH2A'),
    ('NM_206933.3', 'gene/USH2A'),
    ('NM_206933.33', 'gene/USH2A'),
    ('GPR98', 'gene/ADGRV1'),
    ('c12ORF65', 'gene/MTRFR'),
    ('C12oRf65', 'gene/MTRFR'),
    ('C12orf65', 'gene/MTRFR'),
    ('rs1057516028', 'api/variant/323890/browser/'),
    ('S100G', 'gene/S100G'),
    ('S100g', 'gene/S100G'),
    ))
def test_search_engine(client, app, t_search, url):
    response = client.post(
        '/search_engine',
        data={'search': t_search}
    )
    print(response.headers['Location'] + 'http://localhost/{}'.format(url))
    assert 'http://localhost/{}'.format(url) == response.headers['Location']

# test all variants in dev db except c.1A>T (too numerous as used to test variant creation)


def test_variant_page(client, app):
    with app.app_context():
        db = get_db()
        curs = db.cursor()
        curs.execute(
            """
            SELECT id
            FROM variant_feature
            WHERE c_name <> 'c.2del'
            ORDER BY random()
            LIMIT 1000
            """
            # LIMIT 100  WHERE prot_type = 'missense'",  #  ORDER BY random() LIMIT 500
        )
        res = curs.fetchall()
        for variant_id in res:
            print(variant_id)
            assert client.get('/api/variant/{}/browser/'.format(variant_id[0])).status_code == 200
        db.close()
