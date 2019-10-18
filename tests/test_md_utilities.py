import re
import pytest
from flask import g, session
from MobiDetailsApp import md_utilities
from MobiDetailsApp.db import get_db

@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.Arg34*', 'Arg34*'),
	('c.100C>T', '100C>T'),
	('c.100c>t', '100C>T'),
	('g.6160C>T', '6160C>T'),
	('g.6160c>T', '6160C>T'),
	('p.(Arg34*)', 'Arg34*'),
	('p.(Arg34*', 'Arg34*'),
	('p.(Arg34=', 'Arg34='),
	('c.2447_2461del', '2447_2461del'),
	('c.2447_2461delGAGGGAGGGGAAGTA', '2447_2461del'),
	('c.2447_2461delGAGGGAGGGGAAGTAinsA', '2447_2461delinsA'),
	('c.2447_2461dupGAGGGAGGGGAAGTA', '2447_2461dup'),
	('c.2447_2461dup', '2447_2461dup'),
))
def test_clean_var_name(client, variant_in, variant_out):
	test_var = md_utilities.clean_var_name(variant_in)
	assert test_var == variant_out

@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.R34X', 'Arg34Ter'),
	('p.(R34*', 'Arg34Ter'),
	('p.R34_E65del', 'Arg34_Glu65del'),
	('p.(R34Y)', 'Arg34Tyr'),
	('p.(R34_E65del)', 'Arg34_Glu65del'),
	('p.(R34=', 'Arg34=')
))
def test_one2three_fct(client, variant_in, variant_out):
	test_var = md_utilities.one2three_fct(variant_in)
	assert test_var == variant_out
	
@pytest.mark.parametrize(('variant_in', 'variant_out'), (
	('p.Arg34X', 'R34Ter'),
	('p.Arg34del', 'R34del'),
	('p.Arg34Ter', 'R34Ter'),
	('p.(Arg34*', 'R34Ter'),
	('p.Arg34_Glu65del', 'R34_E65del'),
	('p.(Arg34tyr)', 'R34Y'),
	('p.(Arg34_Glu65del)', 'R34_E65del'),
	('p.(Arg34=', 'R34='),
	('p.Leu34del', 'L34del'),
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

	
@pytest.mark.parametrize(('val', 'result'), (
	('0.2', ['intolerant', '#FF0000']),
	('0.6', ['slightly intolerant', '#FF6020']),
	('0.8', ['neutral', '#FFA020']),
	('1.25', ['tolerant', '#2E64FE']),
	('1.4', ['highly tolerant', '#0404B4'])
))
def test_get_metadome_colors(val, result):
	res = md_utilities.get_metadome_colors(val)
	assert res == result

@pytest.mark.parametrize(('g_name', 'pos_end'), (
	('216422237G>A', '216422237'),
	('76885812_76885817del', '76885817'),
	('76885812_76885813insATGC', '76885813'),
	('76885812_76885817dup', '76885817')
))	
def test_compute_pos_end(g_name, pos_end):
	pos = md_utilities.compute_pos_end(g_name)
	assert pos == pos_end
	
vv_dict = {
  "flag": "gene_variant",
  "NM_206933.2:c.100_101delinsA": {
    "hgvs_lrg_transcript_variant": "",
    "validation_warnings": [],
    "refseqgene_context_intronic_sequence": "",
    "alt_genomic_loci": [],
    "transcript_description": "Homo sapiens usherin (USH2A), transcript variant 2, mRNA",
    "gene_symbol": "USH2A",
    "hgvs_predicted_protein_consequence": {
      "tlr": "NP_996816.2:p.(Arg34LysfsTer111)",
      "slr": "NP_996816.2:p.(R34Kfs*111)"
    },
    "submitted_variant": "NM_206933.2:c.100_101delCGinsA",
    "genome_context_intronic_sequence": "",
    "hgvs_lrg_variant": "",
    "hgvs_transcript_variant": "NM_206933.2:c.100_101delinsA",
    "hgvs_refseqgene_variant": "NG_009497.1:g.6160_6161delinsA",
    "primary_assembly_loci": {
      "hg19": {
        "hgvs_genomic_description": "NC_000001.10:g.216595578_216595579delinsT",
        "vcf": {
          "chr": "chr1",
          "ref": "CG",
          "pos": "216595578",
          "alt": "T"
        }
      },
      "hg38": {
        "hgvs_genomic_description": "NC_000001.11:g.216422236_216422237delinsT",
        "vcf": {
          "chr": "chr1",
          "ref": "CG",
          "pos": "216422236",
          "alt": "T"
        }
      },
      "grch37": {
        "hgvs_genomic_description": "NC_000001.10:g.216595578_216595579delinsT",
        "vcf": {
          "chr": "1",
          "ref": "CG",
          "pos": "216595578",
          "alt": "T"
        }
      },
      "grch38": {
        "hgvs_genomic_description": "NC_000001.11:g.216422236_216422237delinsT",
        "vcf": {
          "chr": "1",
          "ref": "CG",
          "pos": "216422236",
          "alt": "T"
        }
      }
    },
    "reference_sequence_records": {
      "refseqgene": "https://www.ncbi.nlm.nih.gov/nuccore/NG_009497.1",
      "protein": "https://www.ncbi.nlm.nih.gov/nuccore/NP_996816.2",
      "transcript": "https://www.ncbi.nlm.nih.gov/nuccore/NM_206933.2"
    }
  },
  "metadata": {
    "variantvalidator_hgvs_version": "1.1.3",
    "uta_schema": "uta_20180821",
    "seqrepo_db": "2018-08-21",
    "variantvalidator_version": "v0.2.5"
  }
}
hg38_test_d = {
	'genome_version': 'hg38',
	'g_name': '216422236_216422237delinsT',
	'chr': '1',
	'pos_ref': 'CG',
	'pos': '216422236',
	'pos_alt': 'T'
}
hg19_test_d = {
	'genome_version': 'hg19',
	'g_name': '216595578_216595579delinsT',
	'chr': '1',
	'pos_ref': 'CG',
	'pos': '216595578',
	'pos_alt': 'T'
}
@pytest.mark.parametrize(('genome', 'var', 'test_d', 'vv_dict'), (
	('hg38', 'NM_206933.2:c.100_101delinsA', hg38_test_d, vv_dict),
	('hg19', 'NM_206933.2:c.100_101delinsA', hg19_test_d, vv_dict)
))
def test_get_genomic_values(genome, var, test_d, vv_dict):
	var_dict = md_utilities.get_genomic_values(genome, vv_dict, var)
	assert var_dict == test_d

@pytest.mark.parametrize(('name', 'result'), (
	('216595578_216595582delinsT', ('216595578', '216595582')),
	('100_101del', ('100', '101')),
	('100C>T', ('100', '100')),
))
def test_compute_start_end_pos(name, result):
	positions = md_utilities.compute_start_end_pos(name)
	assert positions == result

@pytest.mark.parametrize(('seq', 'result'), (
	('ATCG', 'CGAT'),
	('TCTCCAGCCTTGGGAAAAGACCTCGTGACTCAGTCAAGGATATTGAAGCA', 'TGCTTCAATATCCTTGACTGAGTCACGAGGTCTTTTCCCAAGGCTGGAGA'),
	('TGCTTCAATATCCTTGACTGAGTCACGAGGTCTTTTCCCAAGGCTGGAGAA', 'TTCTCCAGCCTTGGGAAAAGACCTCGTGACTCAGTCAAGGATATTGAAGCA')
))
def test_reverse_complement(seq, result):
	rev_comp = md_utilities.reverse_complement(seq)
	assert rev_comp == result