import pytest
#import urllib.parse
from MobiDetailsApp.db import get_db


def test_homepage(client):
    assert client.get('/').status_code == 200


def test_about(client):
    assert client.get('/about').status_code == 200


def test_gene_page(client, app):
    with app.app_context():
        db = get_db()
        curs = db.cursor()
        curs.execute(
            "SELECT name[1] FROM gene LIMIT 50",
        )
        res = curs.fetchall()
        for name in res:
            assert client.get('/gene/{}'.format(name[0])).status_code == 200
#             gene_page_result(client, name)
# def gene_page_result(client, name):
#     assert client.get('/gene/{}'.format(name[0])).status_code == 200


def test_genes_page(client):
    assert client.get('/genes').status_code == 200


def test_vars_page(client):
    assert client.get('/vars/PCDH15').status_code == 200


def test_variant_page(client):
    assert client.get('/variant/5').status_code == 200


@pytest.mark.parametrize(('t_search', 'url'), (
    ('R34X', 'variant/5'),
    ('R34*', 'variant/5'),
    ('p.Arg34*', 'variant/5'),
    ('p.(Arg34Ter)', 'variant/5'),
    ('p.(Arg34*)', 'variant/5'),
    ('c.100C>T', 'variant/5'),
    ('c.100c>t', 'variant/5'),
    ('c.100c>T', 'variant/5'),
    ('g.6160C>T', 'variant/5'),
    ('chr1:g.216595579G>A', 'variant/5'),
    ('chr1:g.216422237G>A', 'variant/5'),
    ('chr1:g.216422237g>A', 'variant/5'),
    ('NC_000001.11:g.216422237G>A', 'variant/5'),
    ('USH2A', 'gene/USH2A'),
    ('c.2447_2461delGAGGGAGGGGAAGTA', 'variant/71'),
    ('c.2447_2461del', 'variant/71'),
    ('p.Gly816_Glu820del', 'variant/71'),
    ('p.G816_E820del', 'variant/71'),
    ('p.Leu1278del', 'variant/68208'),
    ('p.L1278del', 'variant/68208'),
    ('MYO7A', 'gene/MYO7A'),
    ('myo7a', 'gene/MYO7A'),
    ('mYo7A', 'gene/MYO7A'),
    ('NM_206933', 'gene/USH2A'),
    ('NM_206933.', 'gene/USH2A'),
    ('NM_206933.3', 'gene/USH2A'),
    ('NM_206933.33', 'gene/USH2A'),
    ('GPR98', 'gene/ADGRV1'),
    ('c12ORF65', 'gene/C12orf65'),
    ('C12oRf65', 'gene/C12orf65'),
    ('C12orf65', 'gene/C12orf65'),
    ('rs1057516028', 'variant/51689')
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
            "SELECT id FROM variant_feature where c_name <> 'c.1A>T' ORDER BY random() LIMIT 50"  # WHERE prot_type = 'missense'",  #  ORDER BY random() LIMIT 500
        )
        res = curs.fetchall()
        for variant_id in res:
            print(variant_id)
            assert client.get('/variant/{}'.format(variant_id[0])).status_code == 200
