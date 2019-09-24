import re
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
	('p.(Arg34=', 'R34=')
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
	('Arg34X', ('34', '34')),
	('Arg34del', ('34', '34')),
	('Arg34Ter', ('34', '34')),
	('Arg34*', ('34', '34')),
	('Arg34_Glu65del', ('34', '65')),
	('Glu35Arg', ('35', '35')),
	('His3417_Gly3425dup', ('3417', '3425')),
	('Arg34=', ('34', '34'))
))
def test_get_aa_position(client, variant_in, aa_pos):
	aa = md_utilities.get_aa_position(variant_in)
	assert aa == aa_pos
#deprecated
#app_path = '/home/adminbioinfo/Devs/MobiDetails/MobiDetailsApp'
# @pytest.mark.parametrize(('chrom', 'gzfile'), (
# 	('1', md_utilities.app_path + '/static/resources/dbNSFP/v4_0_dbNSFP4.0a_variant.chr1.gz'),
# 	('X', md_utilities.app_path + '/static/resources/dbNSFP/v4_0_dbNSFP4.0a_variant.chrX.gz'),
# 	('M', md_utilities.app_path + '/static/resources/dbNSFP/v4_0_dbNSFP4.0a_variant.chrM.gz'),
# 	('22', md_utilities.app_path + '/static/resources/dbNSFP/v4_0_dbNSFP4.0a_variant.chr22.gz')
# ))
# def test_get_dbNSFP_file(client, chrom, gzfile):
# 	dbnsfp_file = md_utilities.get_dbNSFP_file(chrom)
# 	assert dbnsfp_file == gzfile
	
var = {
	'chr': '1',
	'pos': '216247118',
	'pos_ref': 'C',
	'pos_alt': 'A'
}
def test_get_value_from_tabix_file():
	record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38'][0], var)
	assert re.search('Pathogenic', record[7])
	assert re.search('2356', record[2])
	
@pytest.mark.parametrize(('value', 'result_color'), (
	(0.1270, '#00A020'),
	(0.0000, '#00A020'),
	(0.4289, '#FFA020'),
	(0.6854, '#FF6020'),
	(0.9847, '#FF0000')
))
def test_get_spliceai_color(client, value, result_color):
	color = md_utilities.get_spliceai_color(value)
	assert color == result_color

@pytest.mark.parametrize(('value', 'result_color', 'predictor'), (
	(0.12, '#00A020', 'dbscsnv'),
	(0.85, '#FF0000', 'dbscsnv')
))
def test_get_preditor_single_threshold_color(client, value, result_color, predictor):
	color = md_utilities.get_preditor_single_threshold_color(value, predictor)
	assert color == result_color
	
@pytest.mark.parametrize(('value', 'result_color', 'predictor'), (
	(0, '#00A020', 'fathmm'),
	(-5.88, '#FF0000', 'fathmm')
))
def test_get_preditor_single_threshold_reverted_color(client, value, result_color, predictor):
	color = md_utilities.get_preditor_single_threshold_reverted_color(value, predictor)
	assert color == result_color
	
@pytest.mark.parametrize(('value', 'result_color', 'predictor_min', 'predictor_max'), (
	(0.12, '#00A020', 'pph2_hdiv_mid', 'pph2_hdiv_max'),
	(0.97, '#FF0000', 'pph2_hdiv_mid', 'pph2_hdiv_max')
))
def test_get_preditor_double_threshold_color(client, value, result_color, predictor_min, predictor_max):
	color = md_utilities.get_preditor_double_threshold_color(value, predictor_min, predictor_max)
	assert color == result_color