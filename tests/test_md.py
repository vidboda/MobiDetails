import pytest
from flask import g, session
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
			"SELECT name[1] FROM gene",
		)
		res = curs.fetchall()
		for name in res:
			#print(name[0])
			assert client.get('/gene/{}'.format(name[0])).status_code == 200
	
def test_genes_page(client):
	assert client.get('/genes').status_code == 200
	
def test_vars_page(client):
	assert client.get('/vars/PCDH15').status_code == 200
	
def test_variant_page(client):
	assert client.get('/variant/5').status_code == 200

@pytest.mark.parametrize(('t_search', 'url'), (
	('R34X', 'variant/5'),
	('R34*', 'variant/5'),
	('p.Arg34X', 'variant/5'),
	('p.(Arg34X)', 'variant/5'),
	('p.(Arg34*)', 'variant/5'),
	('p.Arg34*', 'variant/5'),
	('c.100C>T', 'variant/5'),
	('g.6160C>T', 'variant/5'),
	('chr1:g.216595579G>A', 'variant/5'),
	('chr1:g.216422237G>A', 'variant/5'),
	('USH2A', 'gene/USH2A')
	))
def test_search_engine(client, t_search, url):
	response = client.post(
		'/search_engine',
		data = {'search': t_search}
	)
	print(response.headers['Location'] + 'http://localhost/{}'.format(url))
	assert 'http://localhost/{}'.format(url) == response.headers['Location']