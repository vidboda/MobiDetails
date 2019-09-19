import pytest
from flask import g, session
from MobiDetailsApp import md_utilities
from MobiDetailsApp.db import get_db

@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.Arg34*', 'Arg34*'),
	('c.100C>T', '100C>T'),
	('g.6160C>T', '6160C>T'),
	('p.(Arg34*)', 'Arg34*'),
	('p.(Arg34*', 'Arg34*'),
	('p.(Arg34=', 'Arg34=')
))
def test_clean_var_name(client, variant_in, variant_out):
	test_var = md_utilities.clean_var_name(variant_in)
	assert test_var == variant_out

@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.R34X', 'Arg34*'),
	('p.(R34*', 'Arg34*'),
	('p.R34_E65del', 'Arg34_Glu65del'),
	('p.(R34Y)', 'Arg34Tyr'),
	('p.(R34_E65del)', 'Arg34_Glu65del'),
	('p.(R34=', 'Arg34=')
))
def test_one2three_fct(client, variant_in, variant_out):
	test_var = md_utilities.one2three_fct(variant_in)
	assert test_var == variant_out
	
@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.Arg34X', 'R34*'),
	('p.Arg34del', 'R34del'),
	('p.Arg34Ter', 'R34*'),
	('p.(Arg34*', 'R34*'),
	('p.Arg34_Glu65del', 'R34_E65del'),
	('p.(Arg34tyr)', 'R34Y'),
	('p.(Arg34_Glu65del)', 'R34_E65del'),
	('p.(Arg34=', 'R34='),
))
def test_three2one_fct(client, variant_in, variant_out):
	test_var = md_utilities.three2one_fct(variant_in)
	print(test_var)
	assert test_var == variant_out

#pytest tests/test_md_utilities.py::test_get_pos_splice_site
@pytest.mark.parametrize(('pos', 'seg_type', 'seg_num', 'gene', 'genome', 'result'), (
	(216595579, 'exon', 2, ['USH2A','NM_206933'], 'hg19', ['acceptor', 304]),
	(216422237, 'exon', 2, ['USH2A','NM_206933'], 'hg38', ['acceptor', 304]),
	(53321423, 'exon', 1, ['AAAS','NM_015665'], 'hg38', ['donor', 81]),
	(53715207, 'exon', 1, ['AAAS','NM_015665'], 'hg19', ['donor', 81]),
	(34007971, 'exon', 1, ['AMACR','NM_014324'], 'hg19', ['donor', 94]),
	(34007866, 'exon', 1, ['AMACR','NM_014324'], 'hg38', ['donor', 94]),
	(76912640, 'exon', 36, ['MYO7A','NM_000260'], 'hg19', ['donor', 44]),
	(77201595, 'exon', 36, ['MYO7A','NM_000260'], 'hg38', ['donor', 44]),
	(76894138, 'exon', 26, ['MYO7A','NM_000260'], 'hg19', ['acceptor', 26]),
	(77183093, 'exon', 26, ['MYO7A','NM_000260'], 'hg38', ['acceptor', 26])
))
def test_get_pos_splice_site(client, app, pos, seg_type, seg_num, gene, genome, result):
	with app.app_context():
		db = get_db()
		dist = md_utilities.get_pos_splice_site(db, pos, seg_type, seg_num, gene, genome)
	assert dist == result

@pytest.mark.parametrize(('variant_in', 'aa_pos'), (
	('Arg34X', '34'),
	('Arg34del', '34'),
	('Arg34Ter', '34'),
	('Arg34*', '34'),
	('Arg34_Glu65del', '34_65'),
	('Glu35Arg', '35'),
	('His3417_Gly3425dup', '3417_3425'),
	('Arg34=', '34'),
))
def test_get_aa_position(client, variant_in, aa_pos):
	aa = md_utilities.get_aa_position(variant_in)
	assert aa == aa_pos