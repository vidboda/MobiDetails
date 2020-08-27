import re
import pytest
import psycopg2
import json
from flask import g
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


@pytest.mark.parametrize(('chr_name', 'genome', 'ncbi_name'), (
    ('CHR12', 'hg19', 'NC_000012.11'),
    ('cHr12', 'hg19', 'NC_000012.11'),
    ('chrX', 'hg19', 'NC_000023.10'),
    ('chrM', 'hg19', None),
    ('chrX', 'hg38', 'NC_000023.11'),
    ('CHR12', 'hg38', 'NC_000012.12'),
    ('cHr12', 'hg38', 'NC_000012.12'),
    ('cHr12', 'hg38', 'NC_000012.12')
))
def test_get_ncbi_chr_name(client, app, chr_name, genome, ncbi_name):
    with app.app_context():
        db = get_db()
        ncbi_test = md_utilities.get_ncbi_chr_name(db, chr_name, genome)
        assert ncbi_test[0] == ncbi_name


@pytest.mark.parametrize(('chr_name', 'genome', 'ncbi_name'), (
    ('12', 'hg19', 'NC_000012.11'),
    ('X', 'hg19', 'NC_000023.10'),
    ('X', 'hg38', 'NC_000023.11'),
    ('12', 'hg38', 'NC_000012.12')
))
def test_get_common_chr_name(client, app, chr_name, genome, ncbi_name):
    with app.app_context():
        db = get_db()
        res_test = md_utilities.get_common_chr_name(db, ncbi_name)
        assert res_test == [chr_name, genome]


@pytest.mark.parametrize(('chr_name', 'valid'), (
    ('CHR12', True),
    ('cHr12', True),
    ('chx21', False),
    ('chrM', True),
    ('chrM1', False),
))
def test_is_valid_full_chr(client, chr_name, valid):
    valid_test = md_utilities.is_valid_full_chr(chr_name)
    assert valid_test == valid


@pytest.mark.parametrize(('chr_name', 'short_name'), (
    ('CHR12', '12'),
    ('cHr12', '12'),
    ('chr21', '21'),
    ('chrM', 'M'),
    ('M1', None),
))
def test_get_short_chr_name(client, chr_name, short_name):
    valid_test = md_utilities.get_short_chr_name(chr_name)
    assert valid_test == short_name


@pytest.mark.parametrize(('chr_name', 'valid'), (
    ('12', True),
    ('2', True),
    ('x', False),
    ('M', True),
    ('M1', False),
))
def test_is_valid_chr(client, chr_name, valid):
    valid_test = md_utilities.is_valid_chr(chr_name)
    assert valid_test == valid


@pytest.mark.parametrize(('chr_name', 'valid'), (
    ('NC_000002.11', True),
    ('NC_000015.9', True),
    ('Nc_000015.9', True),
    ('NC_000021.a', False),
    ('NC_000024.10', True),
))
def test_is_valid_ncbi_chr(client, chr_name, valid):
    valid_test = md_utilities.is_valid_ncbi_chr(chr_name)
    assert valid_test == valid

# pytest tests/test_md_utilities.py::test_get_pos_splice_site


@pytest.mark.parametrize(('pos', 'positions', 'result'), (
    (216422237, {'segment_start':216422540, 'segment_end':216421852 ,'segment_size':689}, ['acceptor', 304]),
    (34007866, {'segment_start':34008050, 'segment_end':34007773 ,'segment_size':278}, ['donor', 94]),
    (77201595, {'segment_start':77201448, 'segment_end':77201638 ,'segment_size':191}, ['donor', 44]),
    (77183093, {'segment_start':77183068, 'segment_end':77183157 ,'segment_size':90}, ['acceptor', 26])
))
def test_get_pos_splice_site(pos, positions, result):
    dist = md_utilities.get_pos_splice_site(pos, positions)
    assert dist == result


@pytest.mark.parametrize(('name', 'return_value'), (
    ('1524+37C>T', [37, '+']),
    ('1258+59_1258+61del', [59, '+']),
    ('1258-589_1258-587del', [587, '-']),
    ('51437-4_51444del', [1, '-'])
))
def test_get_pos_splice_site_intron(client, app, name, return_value):
    dist = md_utilities.get_pos_splice_site_intron(name)
    assert dist == return_value

@pytest.mark.parametrize(('pos', 'positions', 'result'), (
    (216422237, {'segment_start':216422540, 'segment_end':216421852 ,'segment_size':689}, [288, 689]),
    (34007866, {'segment_start':34008050, 'segment_end':34007773 ,'segment_size':278}, [333, 278]),
    (77201595, {'segment_start':77201448, 'segment_end':77201638 ,'segment_size':191}, [355, 191]),
    (77183093, {'segment_start':77183068, 'segment_end':77183157 ,'segment_size':90}, [258, 90])
))
def test_get_pos_exon_canvas(pos, positions, result):
    canvas = md_utilities.get_pos_exon_canvas(pos, positions)
    assert canvas == result


@pytest.mark.parametrize(('positions', 'result'), (
    ({'gene_name':['AMACR', 'NM_001167595'], 'number':1}, ["5'", "UTR", "intron", 1]),
    ({'gene_name':['USH2A', 'NM_206933'], 'number':13}, ["intron", 12, "intron", 13]),
    ({'gene_name':['MYO7A', 'NM_000260'], 'number':49}, ["intron", 48, "3'", "UTR"]),
    ({'gene_name':['GJB2', 'NM_004004'], 'number':2}, ["intron", 1, "3'", "UTR"]),
    ({'gene_name':['CDH23', 'NM_022124'], 'number':69}, ["intron", 68, "intron", 69])    
))
def test_get_exon_neighbours(app, positions, result):
    with app.app_context():
        db = get_db()
        neighbours = md_utilities.get_exon_neighbours(db, positions)
        assert neighbours == result


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
def test_get_aa_position(variant_in, aa_pos):
    aa = md_utilities.get_aa_position(variant_in)
    assert aa == aa_pos

var = {
    'chr': '1',
    'pos': '216247118',
    'pos_ref': 'C',
    'pos_alt': 'A'
}


def test_get_value_from_tabix_file():
    record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38']['abs_path'], var)
    assert re.search('Pathogenic', record[7])
    assert re.search('2356', record[2])


def test_getdbNSFP_results():
    record = md_utilities.get_value_from_tabix_file('dbnsfp', md_utilities.local_files['dbnsfp']['abs_path'], var)
    score, pred, star = md_utilities.getdbNSFP_results(0, 36, 38, ';', 'basic', 1.1, 'lt', record)
    assert score == '0.0'
    assert pred == 'Damaging'
    assert star == ''


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


@pytest.mark.parametrize(('input_score', 'input_pred', 'threshold', 'direction', 'mode', 'output_score', 'output_pred', 'output_star'), (
    ('0.04;0.21', 'D;N', '0.05', 'lt', 'basic', '0.04', 'Damaging', '*'),
    ('0.96;0.21', 'D;B', '0.50', 'gt', 'pph2', '0.96', 'Probably Damaging', '*'),
    ('0.64;0.21', 'N;N', '0.05', 'lt', 'basic', '.', 'no prediction', '')
))
def test_get_most_other_deleterious_pred(
        input_score, input_pred, threshold, direction, mode,
        output_score, output_pred, output_star):
    score, pred, star = md_utilities.get_most_other_deleterious_pred(input_score, input_pred, threshold, direction, mode)
    assert score == output_score
    assert pred == output_pred
    assert star == output_star


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
    ('0.1', ['highly intolerant', '#D7191C']),
    ('0.2', ['intolerant', '#FF0000']),
    ('0.6', ['slightly intolerant', '#FF6020']),
    ('0.8', ['neutral', '#F9D057']),
    ('0.95', ['slightly tolerant', '#00CCBC']),
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


class fake_g_obj:
    user = dict(username='mobidetails')


def test_create_var_vv(client, app):
    with app.app_context():
        db = get_db()
        g = fake_g_obj()
        error_dict = md_utilities.create_var_vv(
            'NM_206933.2:c.100_101delinsA', 'USH2A', 'NM_206933',
            'c.100_101delinsA', 'c.100_101delinsA', '2', vv_dict,
            'test', db, g
        )
        assert isinstance(error_dict['mobidetails_id'], int)
        # {'mobidetails_error': 'Impossible to insert variant_features for {}'.format(vv_key_var)}


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


def test_prepare_email_html(app):
    with app.test_request_context('/variant/8'):
        # the prepare_email_html functions uses request object to send back the calling URL
        # then we use test_request_context
        # https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.test_request_context
        email = md_utilities.prepare_email_html('Test', 'Test message')
        assert 'MobiDetails' in email

@pytest.mark.parametrize(('w', 'y', 'seq', 'scan_type', 'result'), (
    (9, 1, 'CTCCATGGCTCAGTGAACAAATTCT G CAATCCTCACTCTGGGCAGTGTGAG', 5, 'ACAAATTCT\t-30.52\nCAAATTCTG\t-17.88\nAAATTCTGC\t-13.03\nAATTCTGCA\t-35.61\nATTCTGCAA\t-22.21\nTTCTGCAAT\t-31.16\nTCTGCAATC\t-13.69\nCTGCAATCC\t-14.15\nTGCAATCCT\t-37.49\nGCAATCCTC\t-30.00\nCAATCCTCA\t-30.18\nAATCCTCAC\t-32.17\nATCCTCACT\t-15.42\nTCCTCACTC\t-21.75\nCCTCACTCT\t-29.76\nCTCACTCTG\t-35.21\nTCACTCTGG\t-20.42\nCACTCTGGG\t-24.21\nACTCTGGGC\t-9.48\nCTCTGGGCA\t-30.09\nTCTGGGCAG\t-20.17\nCTGGGCAGT\t-1.04\nTGGGCAGTG\t-8.17\nGGGCAGTGT\t-13.32\nGGCAGTGTG\t-43.55\nGCAGTGTGA\t-4.46\nCAGTGTGAG\t-14.47\n'),
    (9, 1, 'CTCCATGGCTCAGTGAACAAATTCT T CAATCCTCACTCTGGGCAGTGTGAG', 5, 'ACAAATTCT\t-30.52\nCAAATTCTT\t-14.12\nAAATTCTTC\t-21.88\nAATTCTTCA\t-33.58\nATTCTTCAA\t-31.95\nTTCTTCAAT\t-23.51\nTCTTCAATC\t-22.20\nCTTCAATCC\t-20.78\nTTCAATCCT\t-36.10\nTCAATCCTC\t-30.17\nCAATCCTCA\t-30.18\nAATCCTCAC\t-32.17\nATCCTCACT\t-15.42\nTCCTCACTC\t-21.75\nCCTCACTCT\t-29.76\nCTCACTCTG\t-35.21\nTCACTCTGG\t-20.42\nCACTCTGGG\t-24.21\nACTCTGGGC\t-9.48\nCTCTGGGCA\t-30.09\nTCTGGGCAG\t-20.17\nCTGGGCAGT\t-1.04\nTGGGCAGTG\t-8.17\nGGGCAGTGT\t-13.32\nGGCAGTGTG\t-43.55\nGCAGTGTGA\t-4.46\nCAGTGTGAG\t-14.47\n'),
    (9, 1, 'ACCTGAGCAACAAGGTGTAATGTAA G TAGTAGTGTAGGTATAAGCTTTCAT', 5, 'GTAATGTAA\t-26.02\nTAATGTAAG\t-27.41\nAATGTAAGT\t8.62\nATGTAAGTA\t-16.13\nTGTAAGTAG\t-32.34\nGTAAGTAGT\t-16.26\nTAAGTAGTA\t-7.04\nAAGTAGTAG\t-14.67\nAGTAGTAGT\t-20.80\nGTAGTAGTG\t-12.46\nTAGTAGTGT\t-12.39\nAGTAGTGTA\t-44.19\nGTAGTGTAG\t-16.49\nTAGTGTAGG\t-13.00\nAGTGTAGGT\t3.31\nGTGTAGGTA\t-24.84\nTGTAGGTAT\t-28.47\nGTAGGTATA\t-25.17\nTAGGTATAA\t4.04\nAGGTATAAG\t-20.14\nGGTATAAGC\t-3.70\nGTATAAGCT\t-24.17\nTATAAGCTT\t-24.77\nATAAGCTTT\t-32.94\nTAAGCTTTC\t-23.00\nAAGCTTTCA\t-10.32\nAGCTTTCAT\t-27.65\n'),
    (23, 1, 'ACCTGAGCAACAAGGTGTAATGTAA G TAGTAGTGTAGGTATAAGCTTTCAT', 3, 'CTGAGCAACAAGGTGTAATGTAA\t-20.92\nTGAGCAACAAGGTGTAATGTAAG\t-25.00\nGAGCAACAAGGTGTAATGTAAGT\t-42.43\nAGCAACAAGGTGTAATGTAAGTA\t-11.63\nGCAACAAGGTGTAATGTAAGTAG\t-10.20\nCAACAAGGTGTAATGTAAGTAGT\t-20.90\nAACAAGGTGTAATGTAAGTAGTA\t-30.33\nACAAGGTGTAATGTAAGTAGTAG\t-5.05\nCAAGGTGTAATGTAAGTAGTAGT\t-24.94\nAAGGTGTAATGTAAGTAGTAGTG\t-27.48\nAGGTGTAATGTAAGTAGTAGTGT\t-8.95\nGGTGTAATGTAAGTAGTAGTGTA\t-28.25\nGTGTAATGTAAGTAGTAGTGTAG\t-27.80\nTGTAATGTAAGTAGTAGTGTAGG\t-30.32\nGTAATGTAAGTAGTAGTGTAGGT\t-46.22\nTAATGTAAGTAGTAGTGTAGGTA\t-11.50\nAATGTAAGTAGTAGTGTAGGTAT\t-26.40\nATGTAAGTAGTAGTGTAGGTATA\t-37.78\nTGTAAGTAGTAGTGTAGGTATAA\t-48.82\nGTAAGTAGTAGTGTAGGTATAAG\t-25.70\nTAAGTAGTAGTGTAGGTATAAGC\t-32.61\nAAGTAGTAGTGTAGGTATAAGCT\t-21.04\nAGTAGTAGTGTAGGTATAAGCTT\t-14.14\nGTAGTAGTGTAGGTATAAGCTTT\t-26.64\nTAGTAGTGTAGGTATAAGCTTTC\t-41.24\nAGTAGTGTAGGTATAAGCTTTCA\t-25.18\nGTAGTGTAGGTATAAGCTTTCAT\t-28.43\n'),    
    (9, 6, 'GCAGTTTCCAGAAAATGGAGTATCG CAACAT------ CACTTAAAGTACCCTGCTTCAAAGT', 5, 'GGAGTATCG\t-6.39\nGAGTATCGC\t-13.21\nAGTATCGCA\t-30.25\nGTATCGCAA\t-32.36\nTATCGCAAC\t-30.12\nATCGCAACA\t-8.10\nTCGCAACAT\t-12.13\nCGCAACATC\t-28.77\nGCAACATCA\t-22.62\nCAACATCAC\t-25.68\nAACATCACT\t-9.94\nACATCACTT\t-17.31\nCATCACTTA\t-31.85\nATCACTTAA\t-40.66\nTCACTTAAA\t-23.74\nCACTTAAAG\t-10.65\nACTTAAAGT\t-8.10\nCTTAAAGTA\t-28.87\nTTAAAGTAC\t-31.93\nTAAAGTACC\t-30.43\nAAAGTACCC\t1.37\nAAGTACCCT\t-16.08\nAGTACCCTG\t-37.54\nGTACCCTGC\t-28.38\nTACCCTGCT\t-33.71\nACCCTGCTT\t-11.66\nCCCTGCTTC\t-33.79\nCCTGCTTCA\t-31.95\nCTGCTTCAA\t-13.25\nTGCTTCAAA\t-29.19\nGCTTCAAAG\t-19.49\nCTTCAAAGT\t-8.45\n'),
))
def test_maxentscan(w, y, seq, scan_type, result):
    score = md_utilities.maxentscan(w, y, seq, scan_type)
    assert score[0] == result

@pytest.mark.parametrize(('chrom', 'strand', 'scan_type', 'positions', 'result'), (
    (11, '+', 3, {'segment_start': 77201448,'segment_end': 77201638}, [5.40, 'cactcacctctgctctacagCAG']),
    (11, '+', 5, {'segment_start': 77201448,'segment_end': 77201638}, [7.64, 'GTGgtatgt']),
    (1, '-', 3, {'segment_start': 216247226,'segment_end': 216246585}, [8.95, 'taaatatattttatctttagGGC']),
    (1, '-', 5, {'segment_start': 216247226,'segment_end': 216246585}, [10.77, 'CAGgtaaga']),
    (5, '-', 3, {'segment_start': 34005899,'segment_end': 34005756}, [7.95, 'atcgttacttttctcttaagGTG']),
    (5, '-', 5, {'segment_start': 34005899,'segment_end': 34005756}, [9.80, 'CAGgtatgt'])
))
def test_get_maxent_natural_sites_scores(chrom, strand, scan_type, positions, result):
    maxent_natural = md_utilities.get_maxent_natural_sites_scores(chrom, strand, scan_type, positions)
    assert maxent_natural == result


def test_lovd_error_html():
    html = md_utilities.lovd_error_html('test')
    assert '<td class="w3-left-align">test</td>' in html

@pytest.mark.parametrize(('record', 'result'), (
    ('hsa-miR-548j-3p;hsa-miR-548j-3p;hsa-miR-548x-3p;hsa-miR-548ah-3p;hsa-miR-548am-3p', "<a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548j-3p' target='_blank' title='Link to miRBase'>miR-548j-3p</a><br /><a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548x-3p' target='_blank' title='Link to miRBase'>miR-548x-3p</a><br /><a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548ah-3p' target='_blank' title='Link to miRBase'>miR-548ah-3p</a><br /><a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548am-3p' target='_blank' title='Link to miRBase'>miR-548am-3p</a><br />"),
    ('hsa-miR-548o-3p', "<a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548o-3p' target='_blank' title='Link to miRBase'>miR-548o-3p</a><br />"),
    ('.', '.')
))
def test_format_mirs(record, result):
    totest = md_utilities.format_mirs(record)
    assert result == totest


@pytest.mark.parametrize(('api_key', 'result'), (
    ('random', 'Invalid API key'),
    ('ahkgs6!jforjsge%hefqvx,v;:dlzmpdtshenicldje', 'Unknown API key'),
    ('', 'mobidetails'),
))
def test_check_api_key(app, api_key, result):
    with app.app_context():
        db = get_db()
        if api_key == '':
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                "SELECT api_key FROM mobiuser WHERE email = 'mobidetails.iurc@gmail.com'"
            )
            res = curs.fetchone()
            if res is not None:
                api_key = res['api_key']
        check = md_utilities.check_api_key(db, api_key)
        if 'mobidetails_error' in check:
            assert result == check['mobidetails_error']
        else:
            print(check['mobiuser'])
            assert result == check['mobiuser'][4]


@pytest.mark.parametrize(('caller', 'result'), (
    ('random', 'Invalid caller submitted'),
    ('', 'Invalid caller submitted'),
    (None, 'Invalid caller submitted'),
    ('browser', 'Valid caller'),
    ('cli', 'Valid caller')
))
def test_check_caller(caller, result):
        assert md_utilities.check_caller(caller) == result


def test_get_api_key(app):
    with app.app_context():
        db = get_db()
        curs =  db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        g.user = None
        assert md_utilities.get_api_key(g, curs) is not None
# scoreswt = ['GGTGGTCTCCAGCCTTTTACAGG\t-8.62', 'GTGGTCTCCAGCCTTTTACAGGT\t-15.00', 'TGGTCTCCAGCCTTTTACAGGTA\t5.22', 'GGTCTCCAGCCTTTTACAGGTAA\t-10.77', 'GTCTCCAGCCTTTTACAGGTAAT\t-26.67', 'TCTCCAGCCTTTTACAGGTAATG\t-27.62', 'CTCCAGCCTTTTACAGGTAATGT\t-11.72', 'TCCAGCCTTTTACAGGTAATGTG\t-11.21', 'CCAGCCTTTTACAGGTAATGTGG\t-15.62', 'CAGCCTTTTACAGGTAATGTGGA\t-22.41', 'AGCCTTTTACAGGTAATGTGGAG\t-25.73', 'GCCTTTTACAGGTAATGTGGAGG\t-12.15', 'CCTTTTACAGGTAATGTGGAGGT\t-27.04', 'CTTTTACAGGTAATGTGGAGGTC\t-10.80', 'TTTTACAGGTAATGTGGAGGTCC\t-13.64', 'TTTACAGGTAATGTGGAGGTCCT\t-24.18', 'TTACAGGTAATGTGGAGGTCCTC\t-35.55', 'TACAGGTAATGTGGAGGTCCTCT\t-23.70', 'ACAGGTAATGTGGAGGTCCTCTA\t-22.70', 'CAGGTAATGTGGAGGTCCTCTAA\t-25.09', 'AGGTAATGTGGAGGTCCTCTAAA\t-23.02', 'GGTAATGTGGAGGTCCTCTAAAT\t-20.93', 'GTAATGTGGAGGTCCTCTAAATT\t-10.23', '']
# scoresmt = ['GGTGGTCTCCAGCCTTTTACAGA\t-8.20', 'GTGGTCTCCAGCCTTTTACAGAT\t-14.75', 'TGGTCTCCAGCCTTTTACAGATA\t4.51', 'GGTCTCCAGCCTTTTACAGATAA\t-19.52', 'GTCTCCAGCCTTTTACAGATAAT\t-18.71', 'TCTCCAGCCTTTTACAGATAATG\t-19.24', 'CTCCAGCCTTTTACAGATAATGT\t-11.20', 'TCCAGCCTTTTACAGATAATGTG\t-11.13', 'CCAGCCTTTTACAGATAATGTGG\t-15.36', 'CAGCCTTTTACAGATAATGTGGA\t-21.98', 'AGCCTTTTACAGATAATGTGGAG\t-25.75', 'GCCTTTTACAGATAATGTGGAGG\t-11.23', 'CCTTTTACAGATAATGTGGAGGT\t-26.14', 'CTTTTACAGATAATGTGGAGGTC\t-10.16', 'TTTTACAGATAATGTGGAGGTCC\t-12.89', 'TTTACAGATAATGTGGAGGTCCT\t-25.08', 'TTACAGATAATGTGGAGGTCCTC\t-35.69', 'TACAGATAATGTGGAGGTCCTCT\t-23.45', 'ACAGATAATGTGGAGGTCCTCTA\t-22.62', 'CAGATAATGTGGAGGTCCTCTAA\t-24.86', 'AGATAATGTGGAGGTCCTCTAAA\t-22.87', 'GATAATGTGGAGGTCCTCTAAAT\t-19.36', 'ATAATGTGGAGGTCCTCTAAATT\t-9.76', '']
# 
# result = {2: ['TGGTCTCCAGCCTTTTACAGGTA', '5.22', 'TGGTCTCCAGCCTTTTACAGATA', '4.51', -15.74]}
# 
# @pytest.mark.parametrize(('cutoff', 'threshold', 'scoreswt', 'scoresmt', 'result'), (
#     (0.15, 3, scoreswt, scoresmt, result)
# ))
# def test_select_mes_scores(cutoff, threshold, scoreswt, scoresmt, result):
#     signif_scores3 = md_utilities.select_mes_scores(scoreswt, scoresmt, cutoff, threshold)
#     assert signifscore3 == result

