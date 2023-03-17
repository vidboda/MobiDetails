import re
import pytest
import psycopg2
# import json
from flask import g
from MobiDetailsApp import md_utilities
from test_ajax import get_db


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
    ('p.(Met120SerfsTer40)', 'M120fs'),
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
        db_pool, db = get_db()
        ncbi_test = md_utilities.get_ncbi_chr_name(db, chr_name, genome)
        db_pool.putconn(db)
        assert ncbi_test[0] == ncbi_name


@pytest.mark.parametrize(('chr_name', 'genome', 'ncbi_name'), (
    ('12', 'hg19', 'NC_000012.11'),
    ('X', 'hg19', 'NC_000023.10'),
    ('X', 'hg38', 'NC_000023.11'),
    ('12', 'hg38', 'NC_000012.12')
))
def test_get_common_chr_name(client, app, chr_name, genome, ncbi_name):
    with app.app_context():
        db_pool, db = get_db()
        res_test = md_utilities.get_common_chr_name(db, ncbi_name)
        db_pool.putconn(db)
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
    # valid_test = md_utilities.is_valid_ncbi_chr(chr_name)
    assert md_utilities.is_valid_ncbi_chr(chr_name) == valid


@pytest.mark.parametrize(('genome_version', 'result'), (
    ('hg19', 'hg19'),
    ('Hg19', 'hg19'),
    ('hG38', 'hg38'),
    ('GRCh37', 'hg19'),
    ('GrCH38', 'hg38'),
    ('csjfkze', 'wrong_genome_input'),
    ('hg12', 'wrong_genome_input'),
    ('GRCHx38', 'wrong_genome_input'),
))
def test_translate_genome_version(genome_version, result):
    assert md_utilities.translate_genome_version(genome_version) == result


@pytest.mark.parametrize(('vcf_str', 'chr', 'pos', 'ref', 'alt'), (
    ('1-216247118-C-A', '1', 216247118, 'C', 'A'),
    ('1-216247118-C-', None, None, None, None),
    ('chr1-216247118-C-A', '1', 216247118, 'C', 'A'),
    ('ChR1-216247118-C-a', '1', 216247118, 'C', 'A'),
    ('1-216247118-C-1', None, None, None, None),
    ('1-216247118-C-TAGCTA', '1', 216247118, 'C', 'TAGCTA'),
    ('1-216247118-C-TagcTa', '1', 216247118, 'C', 'TAGCTA'),
    ('1_216247118_C_TAGCTA', '1', 216247118, 'C', 'TAGCTA'),
    ('1-216247118:C_TagcTa', '1', 216247118, 'C', 'TAGCTA'),
))
def test_decompose_vcf_str(vcf_str, chr, pos, ref, alt):
    test_chr, test_pos, test_ref, test_alt = md_utilities.decompose_vcf_str(vcf_str)
    assert test_chr == chr
    assert test_pos == pos
    assert test_ref == ref
    assert test_alt == alt
# pytest tests/test_md_utilities.py::test_get_pos_splice_site


@pytest.mark.parametrize(('var', 'result'), (
    ('*145C>T', 'exon'),
    ('145del', 'exon'),
    ('145dup', 'exon'),
    ('145-3C>T', 'intron'),
    ('145+3C>T', 'intron'),
    ('-145C>T', '5UTR'),
    ('145_148del', 'exon'),
    ('145dup', 'exon'),
    ('145-18_145-8del', 'intron'),
    ('-145_-112del', '5UTR'),
))
def test_get_var_genic_csq(var, result):
    assert md_utilities.get_var_genic_csq(var) == result


@pytest.mark.parametrize(('new_csq', 'old_csq', 'result'), (
    ('exon', 'exon', True),
    ('exon', 'intron', True),
    ('exon', '5UTR', True),
    ('intron', 'exon', False),
    ('intron', '5UTR', True),
    ('5UTR', '5UTR', True),
    ('intron', 'intron', True),
    ('5UTR', 'exon', False),
    ('5UTR', 'intron', False),
))
def test_is_higher_genic_csq(new_csq, old_csq, result):
    assert md_utilities.is_higher_genic_csq(new_csq, old_csq) == result


@pytest.mark.parametrize(('pos', 'positions', 'result'), (
    (216422237, {'segment_start': 216422540, 'segment_end': 216421852, 'segment_size': 689}, ['acceptor', 304]),
    (34007866, {'segment_start': 34008050, 'segment_end': 34007773, 'segment_size': 278}, ['donor', 94]),
    (77201595, {'segment_start': 77201448, 'segment_end': 77201638, 'segment_size': 191}, ['donor', 44]),
    (77183093, {'segment_start': 77183068, 'segment_end': 77183157, 'segment_size': 90}, ['acceptor', 26])
))
def test_get_pos_splice_site(pos, positions, result):
    dist = md_utilities.get_pos_splice_site(pos, positions)
    assert dist == result


@pytest.mark.parametrize(('name', 'return_value'), (
    ('1524+37C>T', [37, '+']),
    ('1258+59_1258+61del', [59, '+']),
    ('1258-589_1258-587del', [587, '-']),
    ('51437-4_51444del', [1, '-']),
    ('-385-172_-385-166delinsATT', [166, '-'])
))
def test_get_pos_splice_site_intron(client, app, name, return_value):
    dist = md_utilities.get_pos_splice_site_intron(name)
    assert dist == return_value


@pytest.mark.parametrize(('pos', 'positions', 'result'), (
    (216422237, {'segment_start': 216422540, 'segment_end': 216421852, 'segment_size': 689}, [288, 689]),
    (34007866, {'segment_start': 34008050, 'segment_end': 34007773, 'segment_size': 278}, [333, 278]),
    (77201595, {'segment_start': 77201448, 'segment_end': 77201638, 'segment_size': 191}, [355, 191]),
    (77183093, {'segment_start': 77183068, 'segment_end': 77183157, 'segment_size': 90}, [258, 90])
))
def test_get_pos_exon_canvas(pos, positions, result):
    canvas = md_utilities.get_pos_exon_canvas(pos, positions)
    assert canvas == result


@pytest.mark.parametrize(('positions', 'result'), (
    ({'gene_symbol': 'AMACR', 'refseq': 'NM_001167595.2', 'number': 1}, ["5'", "UTR", "intron", 1]),
    ({'gene_symbol': 'USH2A', 'refseq': 'NM_206933.4', 'number': 13}, ["intron", 12, "intron", 13]),
    ({'gene_symbol': 'MYO7A', 'refseq': 'NM_000260.4', 'number': 49}, ["intron", 48, "3'", "UTR"]),
    ({'gene_symbol': 'GJB2', 'refseq': 'NM_004004.6', 'number': 2}, ["intron", 1, "3'", "UTR"]),
    ({'gene_symbol': 'CDH23', 'refseq': 'NM_022124.6', 'number': 69}, ["intron", 68, "intron", 69])
))
def test_get_exon_neighbours(app, positions, result):
    with app.app_context():
        db_pool, db = get_db()
        neighbours = md_utilities.get_exon_neighbours(db, positions)
        db_pool.putconn(db)
        assert neighbours == result


@pytest.mark.parametrize(('positions', 'chrom', 'strand', 'result'), (
    ({'gene_symbol': 'AMACR', 'refseq': 'NM_001167595.2', 'number': 1, 'segment_start': 34008050, 'segment_end': 34007773}, '5', '-', 'AGTTTCCTTCAGCGGGGCACTGGGAAGCGCCATGGCACTGCAGGGCATCTCGGTCGTGGAGCTGTCCGGCCTGGCCCCGGGCCCGTTCTGTGCTATGGTCCTGGCTGACTTCGGGGCGCGTGTGGTACGCGTGGACCGGCCCGGCTCCCGCTACGACGTGAGCCGCTTGGGCCGGGGCAAGCGCTCGCTAGTGCTGGACCTGAAGCAGCCGCGGGGAGCCGCCGTGCTGCGGCGTCTGTGCAAGCGGTCGGATGTGCTGCTGGAGCCCTTCCGCCGCG'),
    ({'gene_symbol': 'USH2A', 'refseq': 'NM_206933.4', 'number': 13, 'segment_start': 216247226, 'segment_end': 216246585}, '1', '-', 'GGCTTAGGTGTGATCATTGCAATTTTGGATTTAAATTTCTCCGAAGCTTTAATGATGTTGGATGTGAGCCCTGCCAGTGTAACCTCCATGGCTCAGTGAACAAATTCTGCAATCCTCACTCTGGGCAGTGTGAGTGCAAAAAAGAAGCCAAAGGACTTCAGTGTGACACCTGCAGAGAAAACTTTTATGGGTTAGATGTCACCAATTGTAAGGCCTGTGACTGTGACACAGCTGGATCCCTCCCTGGGACTGTCTGTAATGCTAAGACAGGGCAGTGCATCTGCAAGCCCAATGTTGAAGGGAGACAGTGCAATAAATGTTTGGAGGGAAACTTCTACCTACGGCAAAATAATTCTTTCCTCTGTCTGCCTTGCAACTGTGATAAGACTGGGACAATAAATGGCTCTCTGCTGTGTAACAAATCAACAGGACAATGTCCTTGCAAATTAGGGGTAACAGGTCTTCGCTGTAATCAGTGTGAGCCTCACAGGTACAATTTGACCATTGACAATTTTCAACACTGCCAGATGTGTGAGTGTGATTCCTTGGGGACATTACCTGGGACCATTTGTGACCCAATCAGTGGCCAGTGCCTGTGTGTGCCTAATCGTCAAGGAAGAAGGTGTAATCAGTGTCAACCAG'),
    ({'gene_symbol': 'MYO7A', 'refseq': 'NM_000260.4', 'number': 49, 'segment_start': 77214607, 'segment_end': 77215241}, '11', '+', 'GGCTACAAGATGGATGACCTCCTGACTTCCTACATTAGCCAGATGCTCACAGCCATGAGCAAACAGCGGGGCTCCAGGAGCGGCAAGTGAACAGTCACGGGGAGGTGCTGGTTCCATGCCTGCTCTCGAGGCAGCAGTGGGTTCAGGCCCATCAGCTACCCCTGCAGCTGGGGAAGACTTATGCCATCCCGGCAGCGAGGCTGGGCTGGCCAGCCACCACTGACTATACCAACTGGGCCTCTGATGTTCTTCCAGTGAGGCATCTCTCTGGGATGCAGAACTTCCCTCCATCCACCCCTCTGGCACCTGGGTTGGTCTAATCCTAGTTTGCTGTGGCCTTCCCGGTTGTGAGAGCCTGTGATCCTTAGATGTGTCTCCTGTTTCAGACCAGCCCCACCATGCAACTTCCTTTGACTTTCTGTGTACCACTGGGATAGAGGAATCAAGAGGACAATCTAGCTCTCCATACTTTGAACAACCAAATGTGCATTGAATACTCTGAAACCGAAGGGACTGGATCTGCAGGTGGGATGAGGGAGACAGACCACTTTTCTATATTGCAGTGTGAATGCTGGGCCCCTGCTCAAGTCTACCCTGATCACCTCAGGGCATAAAGCATGTTTCATTCTCTGGCC'),
    ({'gene_symbol': 'GJB2', 'refseq': 'NM_004004.6', 'number': 2, 'segment_start': 20189603, 'segment_end': 20187470}, '13', '-', 'AGCAAACCGCCCAGAGTAGAAGATGGATTGGGGCACGCTGCAGACGATCCTGGGGGGTGTGAACAAACACTCCACCAGCATTGGAAAGATCTGGCTCACCGTCCTCTTCATTTTTCGCATTATGATCCTCGTTGTGGCTGCAAAGGAGGTGTGGGGAGATGAGCAGGCCGACTTTGTCTGCAACACCCTGCAGCCAGGCTGCAAGAACGTGTGCTACGATCACTACTTCCCCATCTCCCACATCCGGCTATGGGCCCTGCAGCTGATCTTCGTGTCCACGCCAGCGCTCCTAGTGGCCATGCACGTGGCCTACCGGAGACATGAGAAGAAGAGGAAGTTCATCAAGGGGGAGATAAAGAGTGAATTTAAGGACATCGAGGAGATCAAAACCCAGAAGGTCCGCATCGAAGGCTCCCTGTGGTGGACCTACACAAGCAGCATCTTCTTCCGGGTCATCTTCGAAGCCGCCTTCATGTACGTCTTCTATGTCATGTACGACGGCTTCTCCATGCAGCGGCTGGTGAAGTGCAACGCCTGGCCTTGTCCCAACACTGTGGACTGCTTTGTGTCCCGGCCCACGGAGAAGACTGTCTTCACAGTGTTCATGATTGCAGTGTCTGGAATTTGCATCCTGCTGAATGTCACTGAATTGTGTTATTTGCTAATTAGATATTGTTCTGGGAAGTCAAAAAAGCCAGTTTAACGCATTGCCCAGTTGTTAGATTAAGAAATAGACAGCATGAGAGGGATGAGGCAACCCGTGCTCAGCTGTCAAGGCTCAGTCGCTAGCATTTCCCAACACAAAGATTCTGACCTTAAATGCAACCATTTGAAACCCCTGTAGGCCTCAGGTGAAACTCCAGATGCCACAATGGAGCTCTGCTCCCCTAAAGCCTCAAAACAAAGGCCTAATTCTATGCCTGTCTTAATTTTCTTTCACTTAAGTTAGTTCCACTGAGACCCCAGGCTGTTAGGGGTTATTGGTGTAAGGTACTTTCATATTTTAAACAGAGGATATCGGCATTTGTTTCTTTCTCTGAGGACAAGAGAAAAAAGCCAGGTTCCACAGAGGACACAGAGAAGGTTTGGGTGTCCTCCTGGGGTTCTTTTTGCCAACTTTCCCCACGTTAAAGGTGAACATTGGTTCTTTCATTTGCTTTGGAAGTTTTAATCTCTAACAGTGGACAAAGTTACCAGTGCCTTAAACTCTGTTACACTTTTTGGAAGTGAAAACTTTGTAGTATGATAGGTTATTTTGATGTAAAGATGTTCTGGATACCATTATATGTTCCCCCTGTTTCAGAGGCTCAGATTGTAATATGTAAATGGTATGTCATTCGCTACTATGATTTAATTTGAAATATGGTCTTTTGGTTATGAATACTTTGCAGCACAGCTGAGAGGCTGTCTGTTGTATTCATTGTGGTCATAGCACCTAACAACATTGTAGCCTCAATCGAGTGAGACAGACTAGAAGTTCCTAGTGATGGCTTATGATAGCAAATGGCCTCATGTCAAATATTTAGATGTAATTTTGTGTAAGAAATACAGACTGGATGTACCACCAACTACTACCTGTAATGACAGGCCTGTCCAACACATCTCCCTTTTCCATGACTGTGGTAGCCAGCATCGGAAAGAACGCTGATTTAAAGAGGTCGCTTGGGAATTTTATTGACACAGTACCATTTAATGGGGAGGACAAAATGGGGCAGGGGAGGGAGAAGTTTCTGTCGTTAAAAACAGATTTGGAAAGACTGGACTCTAAAGTCTGTTGATTAAAGATGAGCTTTGTCTACTTCAAAAGTTTGTTTGCTTACCCCTTCAGCCTCCAATTTTTTAAGTGAAAATATAGCTAATAACATGTGAAAAGAATAGAAGCTAAGGTTTAGATAAATATTGAGCAGATCTATAGGAAGATTGAACCTGAATATTGCCATTATGCTTGACATGGTTTCCAAAAAATGGTACTCCACATATTTCAGTGAGGGTAAGTATTTTCCTGTTGTCAAGAATAGCATTGTAAAAGCATTTTGTAATAATAAAGAATAGCTTTAATGATATGCTTGTAACTAAAATAATTTTGTAATGTATCAAATACATTTAAAACATTAAAATATAATCTCTATAATAA'),
    ({'gene_symbol': 'CDH23', 'refseq': 'NM_022124.6', 'number': 69, 'segment_start': 71813244, 'segment_end': 71813348}, '10', '+', 'GGCTCGCTGCTGAAGGTGGTCCTGGAGGATTACCTGCGGCTCAAAAAGCTCTTTGCACAGCGGATGGTGCAAAAAGCCTCCTCCTGCCACTCCTCCATCTCTGAG')
))
def test_get_exon_sequence(positions, chrom, strand, result):
    sequence = md_utilities.get_exon_sequence(positions, chrom, strand)
    print(sequence)
    assert sequence == result


@pytest.mark.parametrize(('var_cdna', 'result'), (
    ('158C>T', '158'),
    ('c.158C>T', None),
    ('158H>T', None),
))
def test_get_exonic_substitution_position(var_cdna, result):
    assert md_utilities.get_exonic_substitution_position(var_cdna) == result


@pytest.mark.parametrize(('var_cdna', 'result'), (
    ('158C>T', 'C>T'),
    ('158-1C>T', 'C>T'),
    ('c.158C>T', 'C>T'),
    ('158H>T', None),
))
def test_get_substitution_nature(var_cdna, result):
    assert md_utilities.get_substitution_nature(var_cdna) == result


@pytest.mark.parametrize(('positions', 'var_gpos', 'var_c', 'result'), (
    ({'segment_start': 34008050}, 34007866, '154T>C', -31), # NM_001167595 exon 1
    ({'segment_start': 216247226}, 216247118, '2276G>T', 2168), # NM_206933 exon 13
    ({'segment_start': 77214607}, 77214617, '6569T>C', 6559), # NM_000260 exon 49
    ({'segment_start': 20189603}, 20189368, '214T>C', -22), # NM_004004 exon 2
    ({'segment_start': 71813244}, 71813280, '9670C>T', 9634) # NM_022124 exon 69
))
def test_get_exon_first_nt_cdna_position(positions, var_gpos, var_c, result):
    assert md_utilities.get_exon_first_nt_cdna_position(positions, var_gpos, var_c) == result


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


@pytest.mark.parametrize(('username', 'user_id'), (
    ('mobidetails', 10),
    ('davidbaux', 1),
    ('fake_username', None),
))
def test_get_user_id(app, username, user_id):
    with app.app_context():
        db_pool, db = get_db()
        test_user_id = md_utilities.get_user_id(username, db)
        db_pool.putconn(db)
        print(test_user_id)
        assert test_user_id == user_id


@pytest.mark.parametrize(('acmg_classes', 'lovd_class'), (
    ([{'acmg_class': 1},{'acmg_class': 2}], 'Likely benign'),
    ([{'acmg_class': 2},{'acmg_class': 1}], 'Likely benign'),
    ([{'acmg_class': 1},{'acmg_class': 2},{'acmg_class': 3}], 'VUS'),
    ([{'acmg_class': 1},{'acmg_class': 5},{'acmg_class': 3}], 'VUS'),
    ([{'acmg_class': 4},{'acmg_class': 5}], 'Likely Pathogenic'),
    ([{'acmg_class': 5},{'acmg_class': 4}], 'Likely Pathogenic'),
    ([{'acmg_class': 4},{'acmg_class': 3},{'acmg_class': 5}], 'VUS'),
    ([{'acmg_class': 4},{'acmg_class': 1}], 'Conflicting'),
    ([{'acmg_class': 1},{'acmg_class': 4}], 'Conflicting'),
    ([{'acmg_class': 4},{'acmg_class': 1},{'acmg_class': 2},{'acmg_class': 5}], 'Conflicting'),
    ([{'acmg_class': 2},{'acmg_class': 5},{'acmg_class': 4}], 'Conflicting'),
    ([{'acmg_class': 2},{'acmg_class': 5},{'acmg_class': 4},{'acmg_class': 3}], 'VUS'),
    ([{'acmg_class': 1}], 'Benign'),
    ([{'acmg_class': 2}], 'Likely benign'),
    ([{'acmg_class': 3}], 'VUS'),
    ([{'acmg_class': 4}], 'Likely Pathogenic'),
    ([{'acmg_class': 5}], 'Pathogenic'),
    ([{'acmg_class': 8}], None),
    ([{'acmg_class': 'ldhe'}], None),
    ([{'acmg_classe': 'ldhe'}], None),
    ([1], None),
    (1, None)
))
def test_define_lovd_class(app, acmg_classes, lovd_class):
    with app.app_context():
        db_pool, db = get_db()
        test_lovd_class = md_utilities.define_lovd_class(acmg_classes, db)
        db_pool.putconn(db)
        assert test_lovd_class == lovd_class


@pytest.mark.parametrize(('acmg_class', 'lovd_class'), (
    (1, 'Benign'),
    (2, 'Likely benign'),
    (3, 'VUS'),
    (4, 'Likely Pathogenic'),
    (5, 'Pathogenic'),
    (6, 'Unknown'),
    ('ae', None),
    (None, None),
    (0, None),
))
def test_acmg2lovd(app, acmg_class, lovd_class):
    with app.app_context():
        db_pool, db = get_db()
        test_lovd_class = md_utilities.acmg2lovd(acmg_class, db)
        db_pool.putconn(db)
        assert test_lovd_class == lovd_class


var = {
    'chr': '1',
    'pos': '216247118',
    'pos_ref': 'C',
    'pos_alt': 'A'
}
var_f = {
    'dna_type': 'substitution',
    'prot_type': 'missense',
    'p_name': 'Cys759Phe'
}
var_hg19 = {
    'chr': '1',
    'pos': '216420460',
    'pos_ref': 'C',
    'pos_alt': 'A'
}
var_indel = {
    'chr': '6',
    'pos': '32830680',
    'pos_ref': 'CC',
    'pos_alt': 'TT'
}
var_indel_f = {
    'dna_type': 'indel',
    'prot_type': 'missense',
    'p_name': 'Val467Ile'
}
var_3utr1 = {
    'chr': '1',
    'pos': '215625629',
    'pos_ref': 'A',
    'pos_alt': 'T'
}
var_3utr1_f = {
    'dna_type': 'substitution',
    'prot_type': 'unknown',
    'p_name': '?'
}
var_3utr2 = {
    'chr': '7',
    'pos': '117667155',
    'pos_ref': 'G',
    'pos_alt': 'T'
}
var_3utr2_f = {
    'dna_type': 'substitution',
    'prot_type': 'unknown',
    'p_name': '?'
}
var_dup = {
    'chr': '3',
    'pos': '81761551',
    'pos_ref': 'A',
    'pos_alt': 'AG'
}
var_dup_f = {
    'dna_type': 'duplication',
    'prot_type': 'unknown',
    'p_name': '?'
}
var_dup_hg19 = {
    'chr': '3',
    'pos': '81810702',
    'pos_ref': 'A',
    'pos_alt': 'AG'
}
var_ss = {
    'chr': '7',
    'pos': '117480148',
    'pos_ref': 'G',
    'pos_alt': 'T'
}
# var_ss_hg19 = {
#     'chr': '7',
#     'pos': '117120202',
#     'pos_ref': 'G',
#     'pos_alt': 'T'
# }
var_ss_f = {
    'dna_type': 'substitution',
    'prot_type': 'unknown',
    'p_name': '?'
}


@pytest.mark.parametrize(('tool', 'var', 'expected', 'record_number', 'file_name', 'var_f'), (
    ('Clinvar', var, 'Pathogenic', 7, 'clinvar_hg38', var_f),
    ('Clinvar', var, '2356', 2, 'clinvar_hg38', var_f),
    ('dbnsfp', var, '3.55', int(md_utilities.external_tools['CADD']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '24.9', int(md_utilities.external_tools['CADD']['dbNSFP_phred_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '1.04', int(md_utilities.external_tools['Eigen']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '15.52', int(md_utilities.external_tools['Eigen']['dbNSFP_pred_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '0.0', int(md_utilities.external_tools['SIFT']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '1.0', int(md_utilities.external_tools['Polyphen-2']['dbNSFP_value_col_hdiv']), 'dbnsfp', var_f),
    ('dbnsfp', var, '0.999', int(md_utilities.external_tools['Polyphen-2']['dbNSFP_value_col_hvar']), 'dbnsfp', var_f),
    ('dbnsfp', var, '-3.4', int(md_utilities.external_tools['FatHMM']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '0.98828', int(md_utilities.hidden_external_tools['FatHMM-MKL']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '9.39', int(md_utilities.hidden_external_tools['Provean']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '0.000146', int(md_utilities.hidden_external_tools['LRT']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '1', int(md_utilities.hidden_external_tools['MutationTaster']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var, '0.883', int(md_utilities.external_tools['ClinPred']['dbNSFP_value_col']), 'dbnsfp', var_f),
    ('dbnsfp', var_indel, '0.0006', int(md_utilities.external_tools['ClinPred']['dbNSFP_value_col']), 'dbnsfp', var_indel_f),
    ('dbnsfp', var_indel, '0.081', int(md_utilities.external_tools['SIFT']['dbNSFP_value_col']), 'dbnsfp', var_indel_f),
    ('REVEL', var_indel, '0.193', int(md_utilities.external_tools['REVEL']['value_col']), 'revel', var_indel_f),
    ('REVEL', var, '0.902', int(md_utilities.external_tools['REVEL']['value_col']), 'revel', var_f),
    ('dbnsfp', var, '1.0888', int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_col_msvm']), 'dbnsfp', var_f),
    ('dbnsfp', var, '0.9471', int(md_utilities.external_tools['MetaSVM-LR']['dbNSFP_value_col_mlr']), 'dbnsfp', var_f),
    ('dbmts', var_3utr1, '0.35', int(md_utilities.external_tools['Eigen']['dbMTS_value_col']), 'dbmts', var_3utr1_f),
    ('dbmts', var_3utr1, '10.12', int(md_utilities.external_tools['Eigen']['dbMTS_pred_col']), 'dbmts', var_3utr1_f),
    ('dbmts', var_3utr1, '0.511638467', int(md_utilities.external_tools['dbMTS']['miranda_rankscore_col']), 'dbmts', var_3utr1_f),
    ('dbmts', var_3utr1, '0.656990242', int(md_utilities.external_tools['dbMTS']['targetscan_rankscore_col']), 'dbmts', var_3utr1_f),
    ('dbmts', var_3utr2, '0.102982936', int(md_utilities.external_tools['dbMTS']['rnahybrid_rankscore_col']), 'dbmts', var_3utr2_f),
    ('CADD', var_3utr2, '0.069', int(md_utilities.external_tools['CADD']['raw_col']), 'cadd', var_3utr2_f),
    ('CADD', var_3utr2, '1.83', int(md_utilities.external_tools['CADD']['phred_col']), 'cadd', var_3utr2_f),
    ('CADD', var_dup, '1.793870', int(md_utilities.external_tools['CADD']['raw_col']), 'cadd_indels', var_dup_f),
    ('CADD', var_dup, '17.69', int(md_utilities.external_tools['CADD']['phred_col']), 'cadd_indels', var_dup_f),
    ('spliceAI', var, 'SpliceAI=A|USH2A|0.00|0.00|0.01|0.00|-20|12|-20|46', 7, 'spliceai_snvs', var_f),
    ('spliceAI', var_dup, 'SpliceAI=AG|GBE1|0.00|0.00|0.00|0.00|32|50|-5|-12', 7, 'spliceai_indels', var_dup_f),
    ('gnomAD exome', var, '0.0010', 5, 'gnomad_exome_hg38', var_f),
    ('gnomAD exome', var, '0.0021', 20, 'gnomad_exome_hg38', var_f),
    ('gnomAD exome', var_dup, '1.0', 5, 'gnomad_exome_hg38', var_dup_f),
    ('gnomAD genome', var, '0.0010', 5, 'gnomad_genome_hg38', var_f),
    ('gnomAD genome', var_dup, '1.0', 5, 'gnomad_genome_hg38', var_dup_f),
    ('gnomADv3', var, '0.0013', 5, 'gnomad_3', var_f),
    ('gnomADv3', var_dup, '1.0000', 5, 'gnomad_3', var_dup_f),
    ('Mistic', var, '0.876', 4, 'mistic', var_f),
    ('dbscSNV', var_ss, '0.9999', 14, 'dbscsnv', var_ss_f),
    ('dbscSNV', var_ss, '0.928', 15, 'dbscsnv', var_ss_f)
))
def test_get_value_from_tabix_file(tool, var, expected, record_number, file_name, var_f):
    record = md_utilities.get_value_from_tabix_file(tool, md_utilities.local_files[file_name]['abs_path'], var, var_f)
    print(record)
    print(record[record_number])
    print(record_number)
    assert re.search(expected, record[record_number])
    # record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38']['abs_path'], var)
    # assert re.search('Pathogenic', record[7])
    # assert re.search('2356', record[2])


def test_getdbNSFP_results():
    record = md_utilities.get_value_from_tabix_file('dbnsfp', md_utilities.local_files['dbnsfp']['abs_path'], var, var_f)
    score, pred, star = md_utilities.getdbNSFP_results(0, 37, 39, ';', 'basic', 1.1, 'lt', record)
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


@pytest.mark.parametrize(('val', 'result'), (
    ('0.1', 'Benign'),
    ('0.2', 'Uncertain'),
    ('0.6', 'Damaging'),
    ('0.8', 'Damaging'),
    ('.', 'no prediction'),
    (None, 'no prediction'),
))
def test_build_revel_pred(val, result):
    res = md_utilities.build_revel_pred(val)
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


@pytest.mark.parametrize(('vv_expr', 'result'), (
    ('8i', 'intron'),
    ('72', 'exon'),
    ('xc', 'segment_type_error'),
))
def test_get_segment_type_from_vv(vv_expr, result):
    segment_type = md_utilities.get_segment_type_from_vv(vv_expr)
    assert segment_type == result


@pytest.mark.parametrize(('vv_expr', 'result'), (
    ('8i', '8'),
    ('72', '72'),
    ('xc', 'segment_number_error'),
))
def test_get_segment_number_from_vv(vv_expr, result):
    segment_number = md_utilities.get_segment_number_from_vv(vv_expr)
    assert segment_number == result


@pytest.mark.parametrize(('cigar', 'result'), (
    ('8=', '8'),
    ('72258=', '72258'),
    ('xc', 'cigar_error'),
))
def test_get_segment_size_from_vv_cigar(cigar, result):
    segment_size = md_utilities.get_segment_size_from_vv_cigar(cigar)
    assert segment_size == result


@pytest.mark.parametrize(('gene_symbol', 'transcript', 'ncbi_chr', 'exon_number', 'start_result'), (
    ('A2ML1', 'NM_144670.6', 'NC_000012.12', '27', '8860881'),
    ('A2ML1', 'NM_144670.6', 'NC_000012.13', '27', 'transcript_error'),
    ('A2ML1', 'NM_001282424.3', 'NC_000012.12', '27', 'transcript_error'),
    ('ABCA4', 'NM_000350.3', 'NC_000001.11', '22', '94042898'),
    ('ABCA4', 'NM_000350.3', 'NC_000001.11', '82', 'transcript_error'),
    ('ABCA4', 'NM_000350.7', 'NC_000001.11', '22', 'transcript_error'),
))
def test_get_positions_dict_from_vv_json(gene_symbol, transcript, ncbi_chr, exon_number, start_result):
    positions = md_utilities.get_positions_dict_from_vv_json(gene_symbol, transcript, ncbi_chr, exon_number)
    if isinstance(positions, str):
        assert positions == start_result
    else:
        assert positions['segment_start'] == start_result


@pytest.mark.parametrize(('gene_symbol', 'transcript', 'ncbi_chr', 'strand', 'start_result', 'end_result'), (
    ('A2ML1', 'NM_144670.6', 'NC_000012.12', '+', 8822621, 8876787),
    ('A2ML1', 'NM_144670.6', 'NC_000012.12', '-', -2, -2),
    ('A2ML1', 'NM_144670.1', 'NC_000012.12', '+', -1, -1),
    ('GJB2', 'NM_004004.6', 'NC_000013.11', '-', 20187470, 20192938),
    ('GJB2', 'NM_004004.6', 'NC_000013.11', '+', -2, -2),
    ('GJB2', 'NM_004004.1', 'NC_000013.11', '-', -1, -1),
))
def test_get_genomic_transcript_positions_from_vv_json(app, gene_symbol, transcript, ncbi_chr, strand, start_result, end_result):
    with app.test_request_context('/'):
        start, end = md_utilities.get_genomic_transcript_positions_from_vv_json(gene_symbol, transcript, ncbi_chr, strand)
        print('start: {0}, end: {1}'.format(start, end))
        assert start == start_result and end == end_result


vv_dict = {
  "flag": "gene_variant",
  "NM_206933.4:c.100_101delinsA": {
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
    "submitted_variant": "NM_206933.4:c.100_101delCGinsA",
    "genome_context_intronic_sequence": "",
    "hgvs_lrg_variant": "",
    "hgvs_transcript_variant": "NM_206933.4:c.100_101delinsA",
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
      "transcript": "https://www.ncbi.nlm.nih.gov/nuccore/NM_206933.4"
    },
    "variant_exonic_positions": {
      "NC_000001.10": {
        "end_exon": "2",
        "start_exon": "2"
      },
      "NC_000001.11": {
        "end_exon": "2",
        "start_exon": "2"
      },
      "NG_009497.2": {
        "end_exon": "2",
        "start_exon": "2"
      }
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
    ('hg38', 'NM_206933.4:c.100_101delinsA', hg38_test_d, vv_dict),
    ('hg19', 'NM_206933.4:c.100_101delinsA', hg19_test_d, vv_dict)
))
def test_get_genomic_values(genome, var, test_d, vv_dict):
    var_dict = md_utilities.get_genomic_values(genome, vv_dict, var)
    assert var_dict == test_d


@pytest.mark.parametrize(('vv_dict'), (
    (vv_dict),
))
def test_check_vv_variant_data(vv_dict):
    verif_data = md_utilities.check_vv_variant_data('NM_206933.4:c.100_101delinsA', vv_dict)
    print(verif_data)
    assert verif_data is True


vv_warning1 = {'flag': 'warning', 'metadata': {'variantvalidator_hgvs_version': '2.0.1', 'variantvalidator_version': '2.0.1.dev16+g3ea810a', 'vvdb_version': 'vvdb_2021_4', 'vvseqrepo_db': 'VV_SR_2021_2/master', 'vvta_version': 'vvta_2021_2'}, 'validation_warning_1': {'alt_genomic_loci': [], 'annotations': {}, 'gene_ids': {}, 'gene_symbol': '', 'genome_context_intronic_sequence': '', 'hgvs_lrg_transcript_variant': '', 'hgvs_lrg_variant': '', 'hgvs_predicted_protein_consequence': {'lrg_slr': '', 'lrg_tlr': '', 'slr': '', 'tlr': ''}, 'hgvs_refseqgene_variant': '', 'hgvs_transcript_variant': '', 'primary_assembly_loci': {}, 'reference_sequence_records': '', 'refseqgene_context_intronic_sequence': '', 'selected_assembly': 'GRCh38', 'submitted_variant': 'NM_000059.3:c.68-7_68-8delinsAA', 'transcript_description': '', 'validation_warnings': ['base start position must be <= end position: Did you mean NM_000059.3:c.68-8_68-7delinsAA?'], 'variant_exonic_positions': None}}

vv_warning2 = {'flag': 'warning', 'metadata': {'variantvalidator_hgvs_version': '2.0.1', 'variantvalidator_version': '2.0.1.dev16+g3ea810a', 'vvdb_version': 'vvdb_2021_4', 'vvseqrepo_db': 'VV_SR_2021_2/master', 'vvta_version': 'vvta_2021_2'}, 'validation_warning_1': {'alt_genomic_loci': [], 'annotations': {}, 'gene_ids': {}, 'gene_symbol': '', 'genome_context_intronic_sequence': '', 'hgvs_lrg_transcript_variant': '', 'hgvs_lrg_variant': '', 'hgvs_predicted_protein_consequence': {'lrg_slr': '', 'lrg_tlr': '', 'slr': '', 'tlr': ''}, 'hgvs_refseqgene_variant': '', 'hgvs_transcript_variant': '', 'primary_assembly_loci': {}, 'reference_sequence_records': '', 'refseqgene_context_intronic_sequence': '', 'selected_assembly': 'GRCh38', 'submitted_variant': 'NM_001292063.2:c.71_78delAGTCCCTG*', 'transcript_description': '', 'validation_warnings': ['Removing redundant reference bases from variant description', 'NM_001292063.2:c.71_78del*: char 34: expected EOF'], 'variant_exonic_positions': None}}

vv_warning3 = {'flag': 'warning', 'metadata': {'variantvalidator_hgvs_version': '2.0.1', 'variantvalidator_version': '2.0.1.dev16+g3ea810a', 'vvdb_version': 'vvdb_2021_4', 'vvseqrepo_db': 'VV_SR_2021_2/master', 'vvta_version': 'vvta_2021_2'}, 'validation_warning_1': {'alt_genomic_loci': [], 'annotations': {}, 'gene_ids': {}, 'gene_symbol': '', 'genome_context_intronic_sequence': '', 'hgvs_lrg_transcript_variant': '', 'hgvs_lrg_variant': '', 'hgvs_predicted_protein_consequence': {'lrg_slr': '', 'lrg_tlr': '', 'slr': '', 'tlr': ''}, 'hgvs_refseqgene_variant': '', 'hgvs_transcript_variant': '', 'primary_assembly_loci': {}, 'reference_sequence_records': '', 'refseqgene_context_intronic_sequence': '', 'selected_assembly': 'GRCh38', 'submitted_variant': 'NM_021175.4:c.*203G>T', 'transcript_description': '', 'validation_warnings': ['Using a transcript reference sequence to specify a variant position that lies outside of the reference sequence is not HGVS-compliant: Instead re-submit NC_000019.10:g.35285245G>T'], 'variant_exonic_positions': None}}

vv_warning4 = {'flag': 'warning', 'metadata': {'variantvalidator_hgvs_version': '2.0.1', 'variantvalidator_version': '2.0.1.dev50+g4572981', 'vvdb_version': 'vvdb_2021_4', 'vvseqrepo_db': 'VV_SR_2021_2/master', 'vvta_version': 'vvta_2021_2'}, 'validation_warning_1': {'alt_genomic_loci': [], 'annotations': {}, 'gene_ids': {}, 'gene_symbol': '', 'genome_context_intronic_sequence': '', 'hgvs_lrg_transcript_variant': '', 'hgvs_lrg_variant': '', 'hgvs_predicted_protein_consequence': {'lrg_slr': '', 'lrg_tlr': '', 'slr': '', 'tlr': ''}, 'hgvs_refseqgene_variant': '', 'hgvs_transcript_variant': '', 'primary_assembly_loci': {}, 'reference_sequence_records': '', 'refseqgene_context_intronic_sequence': '', 'selected_assembly': 'GRCh38', 'submitted_variant': 'NM_058216.3:c.1026+5_1026+7de', 'transcript_description': '', 'validation_warnings': ['NM_058216.3:c.1026+5_1026+7de: char 28: expected one of =, or >'], 'variant_exonic_positions': None}}

vv_warning5 = {'flag': 'warning', 'metadata': {'variantvalidator_hgvs_version': '2.0.1', 'variantvalidator_version': '2.0.1.dev50+g4572981', 'vvdb_version': 'vvdb_2021_4', 'vvseqrepo_db': 'VV_SR_2021_2/master', 'vvta_version': 'vvta_2021_2'}, 'validation_warning_1': {'alt_genomic_loci': [], 'annotations': {}, 'gene_ids': {}, 'gene_symbol': '', 'genome_context_intronic_sequence': '', 'hgvs_lrg_transcript_variant': '', 'hgvs_lrg_variant': '', 'hgvs_predicted_protein_consequence': {'lrg_slr': '', 'lrg_tlr': '', 'slr': '', 'tlr': ''}, 'hgvs_refseqgene_variant': '', 'hgvs_transcript_variant': '', 'primary_assembly_loci': {}, 'reference_sequence_records': '', 'refseqgene_context_intronic_sequence': '', 'selected_assembly': 'GRCh38', 'submitted_variant': 'NM_058216.3:c.1026+5_1026+7d', 'transcript_description': '', 'validation_warnings': ['NM_058216.3:c.1026+5_1026+7d: char 29: end of input'], 'variant_exonic_positions': None}}

vv_warning6 = {'flag': 'warning', 'metadata': {'variantvalidator_hgvs_version': '2.0.1', 'variantvalidator_version': '2.0.1.dev50+g4572981', 'vvdb_version': 'vvdb_2021_4', 'vvseqrepo_db': 'VV_SR_2021_2/master', 'vvta_version': 'vvta_2021_2'}, 'validation_warning_1': {'alt_genomic_loci': [], 'annotations': {}, 'gene_ids': {}, 'gene_symbol': '', 'genome_context_intronic_sequence': '', 'hgvs_lrg_transcript_variant': '', 'hgvs_lrg_variant': '', 'hgvs_predicted_protein_consequence': {'lrg_slr': '', 'lrg_tlr': '', 'slr': '', 'tlr': ''}, 'hgvs_refseqgene_variant': '', 'hgvs_transcript_variant': '', 'primary_assembly_loci': {}, 'reference_sequence_records': '', 'refseqgene_context_intronic_sequence': '', 'selected_assembly': 'GRCh38', 'submitted_variant': 'NM_000179.3:c.4002-10_4002-9ins22', 'transcript_description': '', 'validation_warnings': ['The length of the variant is not formatted following the HGVS guidelines. Please rewrite e.g. 10 to N[10](where N is an unknown nucleotide)'], 'variant_exonic_positions': None}}


@pytest.mark.parametrize(('vv_data', 'return_warning'), (
    (vv_warning1, 'base start position must be <= end position: Did you mean NM_000059.3:c.68-8_68-7delinsAA?'),
    (vv_warning2, 'Removing redundant reference bases from variant description'),
    (vv_warning3, 'Using a transcript reference sequence to specify a variant position that lies outside of the reference sequence is not HGVS-compliant'),
    (vv_warning4, 'NM_058216.3:c.1026+5_1026+7de: char 28: expected one of =, or >'),
    (vv_warning5, 'NM_058216.3:c.1026+5_1026+7d: char 29: end of input'),
    (vv_warning6, 'The length of the variant is not formatted following the HGVS guidelines. Please rewrite e.g. 10 to N[10](where N is an unknown nucleotide)'),
    (vv_dict, ''),
))
def test_return_vv_validation_warnings(vv_data, return_warning):
    assert md_utilities.return_vv_validation_warnings(vv_data) == return_warning


@pytest.mark.parametrize(('vv_api_hello_url', 'vv_api_url'), (
    ('https://rest.variantvalidator.org/hello/?content-type=application/json', 'https://rest.variantvalidator.org/'),
    ('http://194.167.35.195:8000/hello/?content-type=application/json', 'http://194.167.35.195:8000/'),
    ('https://github.com', None),
    ('abcgcece', None),
))
def test_test_vv_api_url(vv_api_hello_url, vv_api_url):
    assert  md_utilities.test_vv_api_url(vv_api_hello_url, vv_api_url) == vv_api_url


@pytest.mark.parametrize(('ua', 'vv_api_url'), (
    ('MobiDetails (mobidetails.iurc@gmail.com)', 'https://rest.variantvalidator.org/'),
    ('chu-bordeaux', 'http://194.167.35.195:8000/'),
    ('CJP', 'http://194.167.35.195:8000/'),
    ('abcgcece', 'https://rest.variantvalidator.org/'),
))
def test_get_vv_api_url(client, app, ua, vv_api_url):
    with app.test_request_context(headers={'user-agent': ua}):
        api_url = md_utilities.get_vv_api_url()
        assert 'http' in api_url
        assert api_url == vv_api_url


class fake_g_obj:
    user = dict(username='mobidetails', id=1)


def test_vv_internal_server_error():
    vv_error = {'message': 'Internal Server Error'}
    assert 'mobidetails_error' in md_utilities.vv_internal_server_error('cli', vv_error, 'NM_001322246.2:c.2del')


def test_create_var_vv(client, app):
    with app.app_context():
        g = fake_g_obj()
        db_pool, db = get_db()
        res_id = md_utilities.create_var_vv(
            'NM_206933.4:c.100_101delinsA', 'USH2A', 'NM_206933.4',
            'c.100_101delinsA', 'c.100_101delinsA', vv_dict,
            'test', db, g
        )
        db_pool.putconn(db)
        print(res_id)
        assert isinstance(res_id, int)


@pytest.mark.parametrize(('name', 'result'), (
    ('216595578_216595582delinsT', ('216595578', '216595582')),
    ('100_101del', ('100', '101')),
    ('100C>T', ('100', '100')),
))
def test_compute_start_end_pos(name, result):
    positions = md_utilities.compute_start_end_pos(name)
    assert positions == result


@pytest.mark.parametrize(('url', 'result'), (
    ('https://stackoverflow.com/questions/18423853/how-to-validate-url-and-redirect-to-some-url-using-flask', True),
    ('abcgeerg', False),
    ('http://194.167.35.195:8000/', True),
    ('https://rest.variantvalidator.org/', True)
))
def test_validate_url(url, result):
    assert md_utilities.validate_url(url) == result


@pytest.mark.parametrize(('seq', 'result'), (
    ('ATCG', 'CGAT'),
    ('TCTCCAGCCTTGGGAAAAGACCTCGTGACTCAGTCAAGGATATTGAAGCA',
        'TGCTTCAATATCCTTGACTGAGTCACGAGGTCTTTTCCCAAGGCTGGAGA'),
    ('TGCTTCAATATCCTTGACTGAGTCACGAGGTCTTTTCCCAAGGCTGGAGAA',
        'TTCTCCAGCCTTGGGAAAAGACCTCGTGACTCAGTCAAGGATATTGAAGCA')
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
    (11, '+', 3, {'segment_start': 77201448, 'segment_end': 77201638}, [5.40, 'cactcacctctgctctacagCAG']),
    (11, '+', 5, {'segment_start': 77201448, 'segment_end': 77201638}, [7.64, 'GTGgtatgt']),
    (1, '-', 3, {'segment_start': 216247226, 'segment_end': 216246585}, [8.95, 'taaatatattttatctttagGGC']),
    (1, '-', 5, {'segment_start': 216247226, 'segment_end': 216246585}, [10.77, 'CAGgtaaga']),
    (5, '-', 3, {'segment_start': 34005899, 'segment_end': 34005756}, [7.95, 'atcgttacttttctcttaagGTG']),
    (5, '-', 5, {'segment_start': 34005899, 'segment_end': 34005756}, [9.80, 'CAGgtatgt'])
))
def test_get_maxent_natural_sites_scores(chrom, strand, scan_type, positions, result):
    maxent_natural = md_utilities.get_maxent_natural_sites_scores(chrom, strand, scan_type, positions)
    assert maxent_natural == result


def test_lovd_error_html():
    html = md_utilities.lovd_error_html('test')
    assert '<td class="w3-left-align" style="vertical-align:middle;">test</td>' in html


@pytest.mark.parametrize(('record', 'result'), (
    ('hsa-miR-548j-3p;hsa-miR-548j-3p;hsa-miR-548x-3p;hsa-miR-548ah-3p;\
hsa-miR-548am-3p', "<a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548j-3p' target='_blank' title='Link to miRBase'>miR-548j-3p</a><br /><a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548x-3p' target='_blank' title='Link to miRBase'>miR-548x-3p</a><br /><a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548ah-3p' target='_blank' title='Link to miRBase'>miR-548ah-3p</a><br /><a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548am-3p' target='_blank' title='Link to miRBase'>miR-548am-3p</a><br />"),
    ('hsa-miR-548o-3p', "<a href='http://www.mirbase.org/cgi-bin/mirna_entry.pl?acc=hsa-miR-548o-3p' target='_blank' title='Link to miRBase'>miR-548o-3p</a><br />"),
    ('.', '.')
))
def test_format_mirs(record, result):
    totest = md_utilities.format_mirs(record)
    print('-{}'.format(totest))
    assert re.split(r'\s+', result) == re.split(r'\s+', totest)


@pytest.mark.parametrize(('api_key', 'result'), (
    ('random', 'Invalid API key'),
    ('ahkgs6!jforjsge%hefqvx,v;:dlzmpdtshenicldje', 'Bad chars in API key'),
    ('ahkgs69jforjsgeghefqvx5vggdlzmpdtshenicldje', 'Unknown API key or unactivated account'),
    ('', 'mobidetails'),
))
def test_check_api_key(app, api_key, result):
    with app.app_context():
        db_pool, db = get_db()
        if api_key == '':
            curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
            curs.execute(
                """
                SELECT api_key
                FROM mobiuser
                WHERE email = 'mobidetails.iurc@gmail.com'
                """
            )
            res = curs.fetchone()
            if res is not None:
                api_key = res['api_key']
        check = md_utilities.check_api_key(db, api_key)
        db_pool.putconn(db)
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
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        g.user = None
        db_pool.putconn(db)
        assert md_utilities.get_api_key(g, curs) is not None


@pytest.mark.parametrize(('criterion', 'color'), (
    ('PVS1', 'w3-red'),
    ('PS5', 'w3-red'),
    ('PM2', 'w3-deep-orange'),
    ('PP2', 'w3-orange'),
    ('BS1', 'w3-green'),
    ('BA1', 'w3-green'),
    ('BP4', 'w3-teal'),
    (1, None),
    ('BBR', None)
))
def test_get_acmg_criterion_color(criterion, color):
    assert md_utilities.get_acmg_criterion_color(criterion) == color


# @pytest.mark.parametrize(('gene_symbol', 'nm_acc', 'c_name', 'prediction'), (
#     ('USH2A', 'NM_206933', 'c.2276G>T', 'NTR'),
# ))
def test_run_spip(app):
    with app.app_context():
        db_pool, db = get_db()
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT id, gene_symbol, refseq, c_name
            FROM variant_feature
            WHERE c_name <> 'c.2del'
            ORDER BY random()
            LIMIT 15
            """
        )
        res = curs.fetchall()
        db_pool.putconn(db)
        for var in res:
            spip_results = md_utilities.run_spip(
                var['gene_symbol'], var['refseq'], var['c_name'], var['id']
            )
            print(spip_results)
            assert 'Interpretation' in spip_results
            dict_spip = md_utilities.format_spip_result(spip_results, 'cli')
            print(dict_spip)
            assert isinstance(dict_spip, dict)


def test_get_running_mode(app):
    with app.app_context():
        assert md_utilities.get_running_mode() in ['on', 'maintenance']


def test_get_tinyurl_api_key(app):
    with app.app_context():
        tinyurl_api_key = md_utilities.get_tinyurl_api_key()
        assert len(tinyurl_api_key) == 60
        assert re.search(r'^\w+$', tinyurl_api_key)


def test_get_vv_token(app):
    with app.app_context():
        vv_token = md_utilities.get_vv_token()
        assert len(vv_token) == 119
        assert re.search(r'^[\w\.-]+$', vv_token)


@pytest.mark.parametrize(('p_name', 'aa1', 'ppos', 'aa2'), (
    ('Pro1239Phe', 'P', '1239', 'F'),
    ('Pro1239X', None, None, None),
    ('1239Phe', None, None, None)
))
def test_decompose_missense(p_name, aa1, ppos, aa2):
    assert aa1 == md_utilities.decompose_missense(p_name)[0]
    assert ppos == md_utilities.decompose_missense(p_name)[1]
    assert aa2 == md_utilities.decompose_missense(p_name)[2]


@pytest.mark.parametrize(('incoming_url', 'outcoming_url'), (
    ('http://10.34.20.79:5001/variant/8#',
        'http://10.34.20.79:5001/variant/8#'),
    ('http://10.34.20.79:5001/variant/8#splicing',
        'http://10.34.20.79:5001/variant/8#splicing'),
    ('http://10.34.20.79:5001/gene/USH2A#',
        'http://10.34.20.79:5001/gene/USH2A#'),
    ('https://mobidetails.iurc.montp.inserm.fr/gene/USH2A#',
        'https://mobidetails.iurc.montp.inserm.fr/gene/USH2A#'),
    ('https://mobidetails.iurc.montp.inserm.fr/variant/8#splicing',
        'https://mobidetails.iurc.montp.inserm.fr/variant/8#splicing'),
    ('/favourite',
        '/favourite'),
    ('/favourite#case',
        '/favourite#case'),
))
def test_build_redirect_url(incoming_url, outcoming_url):
    assert outcoming_url == md_utilities.build_redirect_url(incoming_url)


@pytest.mark.parametrize(('gene_symbol', 'result'), (
    ('USH2A', 'GN005'),
    ('TTN', None),
))
def test_get_clingen_criteria_specification_id(gene_symbol, result):
    assert md_utilities.get_clingen_criteria_specification_id(gene_symbol) == result


def test_spliceai_internal_api_hello():
    print(md_utilities.spliceai_internal_api_hello())
    assert isinstance(md_utilities.spliceai_internal_api_hello(), bool)


def test_build_bedgraph_from_raw_spliceai():
    header1 = 'browser position chr1:215622891-216423448\n'
    header2 = 'track name="spliceAI" type=bedGraph description="spliceAI predictions for NM_206933.4     acceptor_sites = positive_values       donor_sites = negative_values" visibility=full windowingFunction=maximum color=200,100,0 altColor=0,100,200 priority=20 autoScale=off viewLimits=-1:1 darkerLabels=on\n'
    file_basename = '{0}/transcripts/NM_206933.4'.format(
        md_utilities.local_files['spliceai_folder']['abs_path']
    )
    assert md_utilities.build_bedgraph_from_raw_spliceai(1, header1, header2, file_basename) == 'ok'


@pytest.mark.parametrize(('yn_value', 'result'), (
    ('Yes', True),
    ('yes', True),
    ('y', True),
    ('No', False)
))
def test_translate_yn_to_bool(yn_value, result):
    assert md_utilities.translate_yn_to_bool(yn_value) == result


@pytest.mark.parametrize(('gene_symbol', 'is_oncogene', 'is_tumor_suppressor'), (
    ('FBXW7', False, True),
    ('NOTCH1', True, True),
    ('USH2A', False, False)
))
def test_get_oncokb_genes_info(gene_symbol, is_oncogene, is_tumor_suppressor):
    oncokb_dict =  md_utilities.get_oncokb_genes_info(gene_symbol)
    print(oncokb_dict)
    assert oncokb_dict['is_oncogene'] == is_oncogene
    assert oncokb_dict['is_tumor_suppressor'] == is_tumor_suppressor


#
# @pytest.mark.parametrize(('caller', 'param', 'value'), (
#     ('cli', 'variant_g_hgvs', 'NC_000001.11:g.40817273T>G'),
#     ('cli', 'variant_hgvs', 'NM_005422.2:c.5040G>T'),
#     ('browser', 'caller', 'browser'),
# ))
# def test_get_post_param(app, caller, param, value):
#     assert md_utilities.get_post_param(caller, param) == value
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
