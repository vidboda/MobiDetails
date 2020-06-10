import os
import re
import datetime
import psycopg2
import psycopg2.extras
import tabix
import urllib3
import certifi
import json
import twobitreader
import tempfile
import subprocess
from flask import (
    url_for, request, render_template, current_app as app
)
from flask_mail import Message
#from . import config
from MobiDetailsApp import mail


app_path = os.path.dirname(os.path.realpath(__file__))
variant_regexp = '[\dACGTdienulps_>+\*-]+'
genome_regexp = 'hg[13][98]'
nochr_chrom_regexp = '[\dXYM]{1,2}'
nochr_captured_regexp = '\d{1,2}|[XYM]'

lovd_ref_file = '{}/static/resources/lovd/lovd_instances.txt'.format(app_path)

ext_exe = {
    'maxentscan5': '{}/static/resources/maxentscan/score5.pl'.format(app_path),
    'maxentscan3': '{}/static/resources/maxentscan/score3.pl'.format(app_path)
}

def get_clinvar_current_version(clinvar_dir):
    files = os.listdir(clinvar_dir)
    dates = []
    for current_file in files:
        # print(current_file)
        match_obj = re.search(r'clinvar_(\d+).vcf.gz$', current_file)
        if match_obj:
            dates.append(match_obj.group(1))
    return max(dates)

one2three = {
    'A': 'Ala', 'C': 'Cys', 'D': 'Asp', 'E': 'Glu', 'F': 'Phe', 'G': 'Gly', 'H': 'His', 'I': 'Ile',
    'K': 'Lys', 'L': 'Leu', 'M': 'Met', 'N': 'Asn', 'P': 'Pro', 'Q': 'Gln', 'R': 'Arg', 'S': 'Ser',
    'T': 'Thr', 'V': 'Val', 'W': 'Trp', 'Y': 'Tyr', 'del': 'del', 'X': 'Ter', '*': 'Ter', '=': '=',
    'Ter': 'Ter'
}
three2one = {
    'Ala': 'A', 'Cys': 'C', 'Asp': 'D', 'Glu': 'E', 'Phe': 'F', 'Gly': 'G', 'His': 'H', 'Ile': 'I',
    'Lys': 'K', 'Leu': 'L', 'Met': 'M', 'Asn': 'N', 'Pro': 'P', 'Gln': 'Q', 'Arg': 'R', 'Ser': 'S',
    'Thr': 'T', 'Val': 'V', 'Trp': 'W', 'Tyr': 'Y', 'Del': 'del', 'X': 'Ter', '*': 'Ter', '=': '=',
    'Ter': 'Ter'
}
url_ncbi = 'https://www.ncbi.nlm.nih.gov/'
urls = {
    'cadd': 'https://cadd.gs.washington.edu/',
    'clinpred': 'https://sites.google.com/site/clinpred/home',
    'dbscsnv': 'http://www.liulab.science/dbscsnv.html',
    'dbnsfp': 'https://sites.google.com/site/jpopgen/dbNSFP',
    'ensembl_t': 'http://ensembl.org/Homo_sapiens/Transcript/Summary?t=',
    'evs': 'http://evs.gs.washington.edu/EVS/PopStatsServlet?searchBy=chromosome',
    'fathmm': 'http://fathmm.biocompute.org.uk/',
    'gnomad': 'http://gnomad.broadinstitute.org/',
    'hgvs': 'http://varnomen.hgvs.org/',
    'intervar': 'http://wintervar.wglab.org/results.pos.php?queryType=position&build=',
    'intervar_api': 'http://wintervar.wglab.org/api_new.php?queryType=position&build=',
    'lovd': 'http://www.lovd.nl/',
    'map2pdb': 'http://www.rcsb.org/pdb/chromosome.do?v=',
    'marrvel': 'http://marrvel.org/search/gene/',
    'metadome': 'https://stuart.radboudumc.nl/metadome/',
    'metadome_api': 'https://stuart.radboudumc.nl/metadome/api/',
    'mp': 'https://github.com/mobidic/MPA',
    'mutalyzer_name_checker': 'https://mutalyzer.nl/name-checker?description=',
    'mutalyzer_position_converter': 'https://mutalyzer.nl/position-converter?assembly_name_or_alias=',    
    'ncbi_nuccore':  '{}nuccore/'.format(url_ncbi),
    'ncbi_prot': '{}protein/'.format(url_ncbi),
    'ncbi_dbsnp': '{}snp/'.format(url_ncbi),
    'ncbi_clinvar': '{}clinvar'.format(url_ncbi),
    'ncbi_1000g': '{}variation/tools/1000genomes/?'.format(url_ncbi),
    'ncbi_gene': '{}gene/?term='.format(url_ncbi),
    'ncbi_pubmed': '{}pubmed/'.format(url_ncbi),
    'ncbi_litvar_api': '{}research/bionlp/litvar/api/v1/public/rsids2pmids?rsids='.format(url_ncbi),
    # 'ncbi_litvar_api': '{}research/bionlp/litvar/api/v1/public/pmids?query=%7B%22variant%22%3A%5B%22litvar%40'.format(url_ncbi),
    'pph2': 'http://genetics.bwh.harvard.edu/pph2/',
    'revel': 'https://sites.google.com/site/revelgenomics/',
    'spliceai': 'https://github.com/Illumina/SpliceAI',
    'sift': 'https://sift.bii.a-star.edu.sg/',
    'ucsc_hg19': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg19&lastVirtModeType=default\
                  &lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
    'ucsc_hg19_session': '757149165_H4Gy8jWA4BwCuA6WW1M8UxC37MFn',
    'ucsc_hg38': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&lastVirtModeType=default\
                  &lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
    'ucsc_hg38_session': '757151741_tUQRsEoYvqXsPekoiKpwY6Ork8eF',
    'ucsc_2bit': 'http://genome.ucsc.edu/goldenPath/help/twoBit.html',
    'uniprot_id': 'http://www.uniprot.org/uniprot/',
    'variant_validator': ' https://variantvalidator.org/service/validate/?variant=',
    # uncomment below to use genuine VV web API
    # 'variant_validator_api': 'https://rest.variantvalidator.org/',
    # uncomment below to use VV on monster
    # 'variant_validator_api': 'https://194.167.35.245:8000/',
    # uncomment below to use VV on beast
    'variant_validator_api': 'https://194.167.35.207:8000/',
    # uncomment below to use VV on medium
    # 'variant_validator_api': 'https://10.34.20.79:8000/',
    # uncomment below to use VV on genuine VV dev
    # 'variant_validator_api': 'https://www35.lamp.le.ac.uk/',
    # hello on genuine VV
    # 'variant_validator_api_hello': 'https://rest.variantvalidator.org/hello/?content-type=application/json',
    # hello on monster VV
    # 'variant_validator_api_hello': 'https://194.167.35.245:8000/hello/?content-type=application/json',
    # hello on beast VV
    'variant_validator_api_hello': 'https://194.167.35.207:8000/hello/?content-type=application/json',
    # hello on medium VV
    # 'variant_validator_api_hello': 'https://10.34.20.79:8000/hello/?content-type=application/json',
    # hello on genuine VV dev
    # 'variant_validator_api_hello': 'https://www35.lamp.le.ac.uk/hello/?content-type=application/json',
}
# clinvar_date = get_clinvar_current_version('{}/static/resources/clinvar/hg38/'.format(app_path))
local_files = {
    # id :[local path, version, name, short desc, short name 4 urls xref]    
    'cadd': ['{}/static/resources/CADD/hg38/whole_genome_SNVs.tsv.gz'.format(app_path),
             'v1.5', 'CADD SNVs', 'Prediction of deleterious effect for all variant types', 'cadd'],
    'cadd_indels': ['{}/static/resources/CADD/hg38/InDels.tsv.gz'.format(app_path),
                    'v1.5', 'CADD indels', 'Prediction of deleterious effect for all variant types', 'cadd'],
    'clinpred': ['{}/static/resources/clinpred/clinpred.txt.gz'.format(app_path), '2018_hg19', 'ClinPred', 'pre-computed ClinPred scores for all possible human missense variant', 'clinpred'],
    'clinvar_hg38': ['{0}/static/resources/clinvar/hg38/clinvar_{1}.vcf.gz'.format(app_path, get_clinvar_current_version('{}/static/resources/clinvar/hg38/'.format(app_path))),
                     'v{}'.format(get_clinvar_current_version('{}/static/resources/clinvar/hg38/'.format(app_path))), 'ClinVar', 'database of variants, clinically assessed', 'ncbi_clinvar'],
    'dbnsfp': ['{}/static/resources/dbNSFP/v4_0/dbNSFP4.0a.txt.gz'.format(app_path),
               'v4.0a', 'dbNSFP', 'Dataset of predictions for missense', 'dbnsfp'],
    'dbscsnv': ['{}/static/resources/dbscSNV/hg19/dbscSNV.txt.gz'.format(app_path),
                'v1.1', 'dbscSNV', 'Dataset of splicing predictions', 'dbscsnv'],
    'dbsnp': ['{}/static/resources/dbsnp/hg38/GCF_000001405.38.gz'.format(app_path),
              'v153', 'dbSNP', 'Database of human genetic variations', 'ncbi_dbsnp'],
    'gnomad_exome': ['{}/static/resources/gnomad/hg19_gnomad_exome_sorted.txt.gz'.format(app_path),
                     'v2.0.1', 'gnomAD exome', 'large dataset of variants population frequencies', 'gnomad'],
    'gnomad_genome': ['{}/static/resources/gnomad/hg19_gnomad_genome_sorted.txt.gz'.format(app_path),
                      'v2.0.1', 'gnomAD genome', 'large dataset of variants population frequencies', 'gnomad'],
    'gnomad_3': ['{}/static/resources/gnomad/gnomad.genomes.r3.0.sites.vcf.bgz'.format(app_path),
                 'v3', 'gnomAD genome', 'large dataset of variants population frequencies', 'gnomad'],
    'human_genome_hg38': ['{}/static/resources/genome/hg38.2bit'.format(app_path),
                          'hg38', 'Human genome sequence', 'Human genome sequence chr by chr (2bit format)', 'ucsc_2bit'],
    'human_genome_hg19': ['{}/static/resources/genome/hg19.2bit'.format(app_path),
                          'hg19', 'Human genome sequence', 'Human genome sequence chr by chr (2bit format)', 'ucsc_2bit'],
    'maxentscan': ['{}/static/resources/maxentscan/', '2004', 'MaxEntScan', 'Human splice site prediction', 'maxentscan'],
    'metadome': ['{}/static/resources/metadome/v1/'.format(app_path),
                 'v1.0.1', 'metadome scores', 'mutation tolerance at each position in a human protein', 'metadome'],
    'spliceai_snvs': ['{}/static/resources/spliceai/hg38/spliceai_scores.raw.snv.hg38.vcf.gz'.format(app_path),
                      'v1.3', 'spliceAI SNVs', 'Dataset of splicing predictions', 'spliceai'],
    'spliceai_indels': ['{}/static/resources/spliceai/hg38/spliceai_scores.raw.indel.hg38.vcf.gz'.format(app_path),
                        'v1.3', 'spliceAI Indels', 'Dataset of splicing predictions', 'spliceai'],
}

predictor_thresholds = {
    'clinpred': 0.5,
    'dbscsnv': 0.8,
    'fathmm': -1.5,
    'fathmm-mkl': -1.5,
    'lrt': 0.5,  # must be precised - which is not solely determined by the score. => take pred directly into account?
    'metadome_hintolerant': 0.175,
    'metadome_intolerant': 0.52,
    'metadome_sintolerant': 0.7,
    'metadome_neutral': 0.875,
    'metadome_stolerant': 1.025,
    'metadome_tolerant': 1.375,
    'meta-lr': 0.5,    
    'meta-svm': 0,
    'mpa_max': 8,
    'mpa_mid': 5,
    'pph2_hdiv_max': 0.957,
    'pph2_hdiv_mid': 0.454,
    'pph2_hvar_max': 0.909,
    'pph2_hvar_mid': 0.447,
    'provean': -2.5,
    'revel_min': 0.2,
    'revel_max': 0.5,
    'sift': 0.95,  # SIFT is reversed
    'spliceai_min': 0.2,
    'spliceai_mid': 0.5,
    'spliceai_max': 0.8,
}
predictor_colors = {
    'min': '#00A020',
    'highly_tolerant': '#0404B4',
    'tolerant': '#2E64FE',
    'slightly_tolerant': '#00CCBC',
    'no_effect': '#000000',
    'neutral': '#F9D057',
    'small_effect': '#FFA020',
    'mid_effect': '#FF6020',
    'max': '#FF0000',
    'highly_intolerant': '#D7191C',
}
predictors_translations = {
    'basic': {
        'D': 'Damaging',
        'T': 'Tolerated',
        '.': 'no prediction',
        'N': 'Neutral',
        'U': 'Unknown'
    },
    'pph2': {
        'D': 'Probably Damaging',
        'P': 'Possibly Damaging',
        'B': 'Benign',
        '.': 'no prediction'
    },
    'mt': {
        'A': 'Disease causing automatic',
        'D': 'Disease causing',
        'N': 'polymorphism',
        'P': 'polymorphism automatic',
        '.': 'no prediction'
    },  # mutation taster
    'revel': {
        'D': 'Damaging',
        'U': 'Uncertain',
        'B': 'Benign',
        '.': 'no prediction'
    }
}

complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}


def reverse_complement(seq):
    return "".join(complement[base] for base in reversed(seq.upper()))


def clean_var_name(variant):
    variant = re.sub(r'^[cpg]\.', '', variant)
    variant = re.sub(r'\(', '', variant)
    variant = re.sub(r'\)', '', variant)
    if re.search('>', variant):
        variant = variant.upper()
    elif re.search('d[eu][lp]', variant):
        match_obj = re.search(r'^(.+d[eu][lp])[ATCG]+$', variant)
        if match_obj:
            variant = match_obj.group(1)
        else:
            match_obj = re.search(r'^(.+del)[ATCG]+(ins[ACTG])$', variant)
            if match_obj:
                variant = match_obj.group(1) + match_obj.group(2)
    return variant


def three2one_fct(var):
    var = clean_var_name(var)
    match_object = re.search(r'^(\w{3})(\d+)(\w{3}|[X\*=])$', var)
    if match_object:
        if re.search('d[ue][pl]', match_object.group(3)):
            return three2one[match_object.group(1).capitalize()] + match_object.group(2) + match_object.group(3)
        else:
            return three2one[match_object.group(1).capitalize()] + match_object.group(2) + three2one[match_object.group(3).capitalize()]
    match_object = re.search(r'^(\w{3})(\d+_)(\w{3})(\d+.+)$', var)
    if match_object:
        return three2one[match_object.group(1)].capitalize() + match_object.group(2) + three2one[match_object.group(3)].capitalize() + match_object.group(4)


def one2three_fct(var):
    var = clean_var_name(var)
    match_object = re.search(r'^(\w{1})(\d+)([\w\*=]{1})$', var)
    if match_object:
        return one2three[match_object.group(1).capitalize()] + match_object.group(2) + one2three[match_object.group(3).capitalize()]
    match_object = re.search(r'^(\w{1})(\d+)(d[ue][pl])$', var)
    if match_object:
        return one2three[match_object.group(1).capitalize()] + match_object.group(2) + match_object.group(3)
    match_object = re.search(r'^(\w{1})(\d+_)(\w{1})(\d+.+)$', var)
    if match_object:
        return one2three[match_object.group(1).capitalize()] + match_object.group(2) + one2three[match_object.group(3).capitalize()] + match_object.group(4)


def get_ncbi_chr_name(db, chr_name, genome):  # get NCBI chr names for common names
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if is_valid_full_chr(chr_name):
        short_chr = get_short_chr_name(chr_name)
        if short_chr is not None:
            curs.execute(
                "SELECT ncbi_name FROM chromosomes WHERE genome_version = %s AND name = %s",
                (genome, short_chr)
            )
            ncbi_name = curs.fetchone()
            # print(ncbi_name)
            if ncbi_name is not None:
                return ncbi_name


def get_common_chr_name(db, ncbi_name):  # get common chr names for NCBI names
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if is_valid_ncbi_chr(ncbi_name):
        curs.execute(
            "SELECT name, genome_version FROM chromosomes WHERE ncbi_name = %s",
            (ncbi_name,)
        )
        res = curs.fetchone()
        if res is not None:
            return res


def is_valid_full_chr(chr_name):  # chr name is valid?
    if re.search(rf'^[Cc][Hh][Rr]({nochr_captured_regexp})$', chr_name):
        return True
    return False


def get_short_chr_name(chr_name):  # get small chr name
    match_obj = re.search(rf'^[Cc][Hh][Rr]({nochr_captured_regexp})$', chr_name)
    if match_obj is not None:
        return match_obj.group(1)


def is_valid_chr(chr_name):  # chr name is valid?
    if re.search(rf'^({nochr_captured_regexp})$', chr_name):
        return True
    return False


def is_valid_ncbi_chr(chr_name):  # NCBI chr name is valid?
    if re.search(r'^[Nn][Cc]_0000\d{2}\.\d{1,2}$', chr_name):
        return True
    return False


def get_pos_splice_site(pos, positions):  # compute position relative to nearest splice site
    if positions is not None:
        # print("{0}-{1}-{2}".format(positions['segment_start'],pos,positions['segment_end']))
        if abs(int(positions['segment_end'])-int(pos)+1) <= abs(int(positions['segment_start'])-int(pos)+1):
            # near from segment_end
            # always exons!!!!
            return ['donor', abs(int(positions['segment_end'])-int(pos))+1]
        else:
            # near from segment_start
            return ['acceptor', abs(int(positions['segment_start'])-int(pos))+1]


def get_pos_splice_site_intron(name):  # get position of intronic variant to the nearest ss
    match_obj = re.search(r'^[\*-]?\d+([\+-])(\d+)[^\d_]', name)
    if match_obj:
        return [int(match_obj.group(2)), match_obj.group(1)]
    match_obj = re.search(r'[\*-]?\d+([\+-])(\d+)_\d+[\+-](\d+)[^\d_]', name)
    if match_obj:
        return [min(int(match_obj.group(2)), int(match_obj.group(3))), match_obj.group(1)]
    if re.search(r'[\*-]?\d+[-]\d+_\d+[^\d_]', name):
        # overlapping variant
        return [1, '-']


def get_pos_exon_canvas(pos, positions):  # compute relative position in exon for canvas drawing
    if positions is not None:
        pos_from_beginning = abs(int(positions['segment_start'])-int(pos))+1
        # rel_pos = pos_from_beginning / positions['segment_size']
        # rel_pos_canvas = rel_pos * 200
        return [200 + int(round((pos_from_beginning / positions['segment_size'])*200)), positions['segment_size']]


def get_exon_neighbours(db, positions):  # get introns names, numbers surrounding an exon
    prec_type = prec_number = fol_type = fol_number = None
    if positions['number'] == 1:
        prec_type = "5'"
        prec_number = "UTR"
    else:
        prec_type = "intron"
        prec_number = positions['number'] - 1
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    curs.execute(
        "SELECT type FROM segment WHERE gene_name[2] = %s AND number = %s AND genome_version = 'hg38'",
        (positions['gene_name'][1], positions['number'] + 1)
    )
    following_seg = curs.fetchone()
    if following_seg is not None:
        if following_seg['type'] == '3UTR':
            fol_type = "3'"
            fol_number = "UTR"
        elif following_seg['type'] == 'intron' or \
                following_seg['type'] == 'exon':
            fol_type = "intron"
            fol_number = positions['number']
    return [prec_type, prec_number, fol_type, fol_number]


def get_aa_position(hgvs_p):  # get aa position fomr hgvs p. (3 letter)
    match_object = re.search(r'^\w{3}(\d+)_\w{3}(\d+)[^\d]+$', hgvs_p)
    if match_object:
        # return "{0}_{1}".format(match_object.group(1), match_object.group(2))
        return match_object.group(1), match_object.group(2)
    match_object = re.search(r'^\w{3}(\d+)[^\d]+.*$', hgvs_p)
    if match_object:
        return match_object.group(1), match_object.group(1)


def get_value_from_tabix_file(text, tabix_file, var):  # open a file with tabix and look for a record:
    tb = tabix.open(tabix_file)
    query = "{0}:{1}-{2}".format(var['chr'], var['pos'], var['pos'])
    if text == 'gnomADv3':
        query = "chr{0}:{1}-{2}".format(var['chr'], var['pos'], var['pos'])
    # print(query)
    try:
        records = tb.querys(query)
    except Exception as e:
        send_error_email(
            prepare_email_html(
                'MobiDetails error',
                '<p>A tabix failed</p><p>tabix {0} {1}<br /> for variant:{2} with args: {3}</p>'.format(
                    tabix_file, query, var, e.args
                )
            ),
            '[MobiDetails - Tabix Error]'
        )
        return 'Match failed in {}'.format(text)

    i = 3
    if re.search('(dbNSFP|Indels|whole_genome_SNVs|dbscSNV|clinpred)', tabix_file):
        i -= 1
    for record in records:
        if record[i] == var['pos_ref'] and \
                record[i+1] == var['pos_alt']:
            # print('{0}-{1}-{2}-{3}'.format(record[i], var['pos_ref'], record[i+1], var['pos_alt']))
            return record
        elif record[i] == var['pos_ref'] and \
                (re.search(r'{},'.format(var['pos_alt']), record[i+1]) or
                 re.search(r',{}'.format(var['pos_alt']), record[i+1])):
            # multiple alts
            return record
    return 'No match in {}'.format(text)


def getdbNSFP_results(
        transcript_index, score_index, pred_index, sep,
        translation_mode, threshold_for_other,
        direction_for_other, dbnsfp_record):  # manage dbNSFP scores and values
    score = '.'
    pred = 'no prediction'
    star = ''
    try:
        score = re.split('{}'.format(sep), dbnsfp_record[score_index])[transcript_index]
        if pred_index != score_index:
            pred = predictors_translations[translation_mode][re.split('{}'.format(sep), dbnsfp_record[pred_index])[transcript_index]]
            if score == '.':  # search most deleterious in other isoforms
                score, pred, star = get_most_other_deleterious_pred(
                    dbnsfp_record[score_index], dbnsfp_record[pred_index],
                    threshold_for_other, direction_for_other, translation_mode
                )
    except Exception:
        try:
            score = dbnsfp_record[score_index]
            if pred_index != score_index:
                pred = predictors_translations[translation_mode][dbnsfp_record[pred_index]]
        except Exception:
            pass
    return score, pred, star


def get_spliceai_color(val):  # returns an html color depending on spliceai score
    if val != '.':
        value = float(val)
        if value > predictor_thresholds['spliceai_max']:
            return predictor_colors['max']
        elif value > predictor_thresholds['spliceai_mid']:
            return predictor_colors['mid_effect']
        elif value > predictor_thresholds['spliceai_min']:
            return predictor_colors['small_effect']
        else:
            return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_most_other_deleterious_pred(
        score, pred, threshold, direction, pred_type):  # returns most deleterious score of predictors when not found in desired transcript
    j = 0
    k = 0
    best_score = threshold
    for score in re.split(';', score):
        if direction == 'lt':
            if score != '.' and \
                    float(score) < float(best_score):
                best_score = score
                k = j
        else:
            if score != '.' and \
                    float(score) > float(best_score):
                best_score = score
                k = j
        j += 1
    if best_score != threshold:
        return best_score, predictors_translations[pred_type][re.split(';', pred)[k]], '*'
    else:
        return '.', 'no prediction', ''


def get_preditor_single_threshold_color(val, predictor):  # returns an html color depending on a single threshold
    # function to get green or red
    if val != '.':
        value = float(val)
        if predictor == 'sift':
            value = 1-(float(val))
        if value > predictor_thresholds[predictor]:
            return predictor_colors['max']
        return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_preditor_single_threshold_reverted_color(val, predictor):  # returns an html color depending on a single threshold (reverted, e.g. for fathmm)
    # function to get green or red
    if val != '.':
        if float(val) < predictor_thresholds[predictor]:
            return predictor_colors['max']
        return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_preditor_double_threshold_color(val, predictor_min, predictor_max):  # returns an html color depending on a double threshold
    # function to get green or red
    if val != '.':
        value = float(val)
        if value > predictor_thresholds[predictor_max]:
            return predictor_colors['max']
        elif value > predictor_thresholds[predictor_min]:
            return predictor_colors['mid_effect']
        return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_metadome_colors(val):  # returns a list of effect and color for metadome
    value = float(val)
    if value < predictor_thresholds['metadome_hintolerant']:
        return ['highly intolerant', predictor_colors['highly_intolerant']]
    if value < predictor_thresholds['metadome_intolerant']:
        return ['intolerant', predictor_colors['max']]
    elif value < predictor_thresholds['metadome_sintolerant']:
        return ['slightly intolerant', predictor_colors['mid_effect']]
    elif value < predictor_thresholds['metadome_neutral']:
        return ['neutral', predictor_colors['neutral']]
    elif value < predictor_thresholds['metadome_stolerant']:
        return ['slightly tolerant', predictor_colors['slightly_tolerant']]
    elif value < predictor_thresholds['metadome_tolerant']:
        return ['tolerant', predictor_colors['tolerant']]
    else:
        return ['highly tolerant', predictor_colors['highly_tolerant']]


def compute_pos_end(g_name):
    # in ajax.py return end pos of a specific variant
    # receives g_name as 216420460C>A or 76885812_76885817del
    match_object = re.search(r'^(\d+)[ATGC]>', g_name)
    if match_object is not None:
        return match_object.group(1)
    else:
        match_object = re.search(r'_(\d+)[di]', g_name)
        if match_object is not None:
            return match_object.group(1)
        else:
            # case of single nt dels ins dup
            match_object = re.search(r'^(\d+)[d]', g_name)
            if match_object is not None:
                return match_object.group(1)


def compute_start_end_pos(name):
    # slightly diffenent as above as start can differ from VCF and HGVS - for variants > 1bp
    match_object = re.search(r'(\d+)_(\d+)[di]', name)
    if match_object is not None:
        return match_object.group(1), match_object.group(2)
    else:
        match_object = re.search(r'^(\d+)[ATGC][>=]', name)
        if match_object is not None:
            return match_object.group(1), match_object.group(1)
        else:
            # single nt del or delins
            match_object = re.search(r'^(\d+)[d]', name)
            if match_object is not None:
                return match_object.group(1), match_object.group(1)


def danger_panel(var, warning):  # to be used in create_var_vv
    begin_txt = 'VariantValidator error: '
    if var == '':
        begin_txt = ''
    return '<div class="w3-margin w3-panel w3-pale-red w3-leftbar w3-display-container">\
                <span class="w3-button w3-ripple w3-display-topright w3-large" onclick="this.parentElement.style.display=\'none\'">X</span>\
                <p><span><strong>{0}{1}<br/>{2}</strong></span><br /></p></div>'.format(begin_txt, var, warning)


def info_panel(text, var='', id_var='', color_class='w3-sand'):
    # to print general info do not send var neither id_var
    # Newly created variant:
    c = 'c.'
    if re.search('N[MR]_', var):
        c = ''
    link = ''
    if var != '':
        link = '<a href="{0}" target="_blank" title="Go to the variant page">\
                {1}{2}</a>'.format(url_for('md.variant', variant_id=id_var), c, var)
    return '<div class="w3-margin w3-panel {0} w3-leftbar w3-display-container">\
                <span class="w3-button w3-ripple w3-display-topright w3-large" \
                onclick="this.parentElement.style.display=\'none\'">X</span>\
                <p><span><strong>{1}{2}<br/></strong></span><br /></p></div>'.format(color_class, text, link)


def create_var_vv(vv_key_var, gene, acc_no, new_variant, original_variant, acc_version, start_time, vv_data, caller, db, g):
    vf_d = {}
    # deal with various warnings
    # docker up?
    if caller == 'webApp':
        print('Creating variant: {0} - {1}'.format(gene, original_variant))
    if 'flag' not in vv_data:
        if caller == 'webApp':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    '<p>VariantValidator looks down!! no Flag in json response</p>'
                ),
                '[MobiDetails - VariantValidator Error]'
            )
            return danger_panel(vv_key_var, "VariantValidator looks down!! Sorry for the inconvenience. Please retry later.")
        elif caller == 'api':
            return {'mobidetails_error': 'VariantValidator looks down'}
    elif vv_data['flag'] is None:
        if caller == 'webApp':
            return danger_panel(
                vv_key_var,
                "VariantValidator could not process your variant, please check carefully your nomenclature!\
                Of course this may also come from the gene and not from you!"
            )
        elif caller == 'api':
            return {'mobidetails_error': 'No flag in VariantValidator answer. Please check your variant.'}
    elif re.search('Major error', vv_data['flag']):
        if caller == 'webApp':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    '<p>A major validation error has occurred in VariantValidator.</p>'
                ),
                '[MobiDetails - VariantValidator Error]'
            )
            return danger_panel(
                vv_key_var,
                "A major validation error has occurred in VariantValidator. \
                VV Admin have been made aware of the issue. Sorry for the inconvenience. Please retry later."
            )
        elif caller == 'api':
            return {'mobidetails_error': 'A major validation error has occurred in VariantValidator'}
    # print(vv_data['flag'])
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # main isoform?
    curs.execute(
        "SELECT canonical FROM gene WHERE name[2] = %s",
        (acc_no,)
    )
    res_main = curs.fetchone()
    remapper = False
    if res_main['canonical'] is not True:
        # check if canonical in vv_data
        # we want variants in priority in canonical isoforms
        curs.execute(
            "SELECT name, nm_version FROM gene WHERE name[1] = %s and canonical = 't'",
            (gene,)
        )
        res_can = curs.fetchone()
        # main_key_reg = "{0}\.{1}".format(res_can['name'][1], res_can['nm_version'])
        # for key in vv_data:
        #     if re.search('{}'.format(main_key_reg), key):
        #         vv_key_var = key
        # cannot happen as VV when queried with an isoform returns the results  only for this isoform
        # we could get pseudo VCF values an rerun VV instead
        try:
            hg38_d = get_genomic_values('hg38', vv_data, vv_key_var)
            if 'mobidetails_error' in hg38_d:
                if caller == 'webApp':
                    return danger_panel('MobiDetails error', hg38_d['mobidetails_error'])
                elif caller == 'api':
                    return hg38_d
        except Exception as e:
            # means we have an error
            if vv_data['flag'] == 'warning':
                if caller == 'webApp':
                    return danger_panel(vv_key_var, ' '.join(vv_data['validation_warning_1']['validation_warnings']))
                elif caller == 'api':
                    return {'mobidetails_error': vv_data['validation_warning_1']['validation_warnings']}
            else:
                if caller == 'webApp':
                    send_error_email(
                        prepare_email_html(
                            'MobiDetails error',
                            '<p>Mapping issue with {0} with args: {1}</p>'.format(vv_key_var, e.args)
                        ),
                        '[MobiDetails - Mapping issue]'
                    )
                    return danger_panel(vv_key_var, 'I have some troubles with the mapping of this variant. ')
                elif caller == 'api':
                    send_error_email(
                        prepare_email_html(
                            'MobiDetails error',
                            '<p>Mapping issue with {0} with args: {1}</p>'.format(vv_key_var, e.args)
                        ),
                        '[MobiDetails API - Mapping issue]'
                    )
                    return {'mobidetails_error': '{}: mapping issue'.format(vv_key_var)}

        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}-{2}-{3}-{4}/all?content-type=application/json".format(
            urls['variant_validator_api'], hg38_d['chr'], hg38_d['pos'],
            hg38_d['pos_ref'], hg38_d['pos_alt']
        )
        try:
            vv_data2 = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
            for key in vv_data2:
                if re.search(r'{0}\.{1}'.format(res_can['name'][1], res_can['nm_version']), key):
                    # if canonical isoform in new query
                    vv_data = vv_data2
                    vv_key_var = key
                    var_obj = re.search(r':c\.(.+)$', key)
                    vf_d['c_name'] = var_obj.group(1)
                    acc_no = res_can['name'][1]
                    acc_version = res_can['nm_version']
                    first_level_key = key
                    remapper = True
        except Exception:
            pass
    # print(vv_key_var)
    if 'validation_warning_1' in vv_data:
        first_level_key = 'validation_warning_1'
    if vv_key_var in vv_data:
        first_level_key = vv_key_var

    if vv_data['flag'] == 'intergenic':
        first_level_key = 'intergenic_variant_1'
    else:
        for key in vv_data:
            # if vv modified the nomenclature
            if re.search('{}'.format(acc_no), key) and \
                    vv_data[key]['submitted_variant'] == vv_key_var:
                vv_key_var = key
                var_obj = re.search(r':c\.(.+)$', key)
                vf_d['c_name'] = var_obj.group(1)
                first_level_key = key
                break
    try:
        print('First level key: {}'.format(first_level_key))
    except UnboundLocalError as e:
        if caller == 'webApp':
            print(vv_data)
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    '<p>Insertion failed for variant hg38 for {0} with args: {1}.\
                    <br />The unknown error arised again.</p><p>{2}</p>'.format(
                        vv_key_var,
                        e.args,
                        vv_data)
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                vv_key_var,
                'An unknown error has been caught during variant creation with VariantValidator.<br /> \
                It may work if you try again.<br />I am aware of this bug and actively tracking it.'
            )
        elif caller == 'api':
            return {'mobidetails_error':  'An unknown error has been caught during variant creation with VariantValidator. \
                                            It is possible that it works if you try again: {0}-{1}'.format(acc_no, gene)}
    if 'validation_warnings' in vv_data[first_level_key]:
        for warning in vv_data[first_level_key]['validation_warnings']:
            # print(vv_data[first_level_key])
            if re.search(r'RefSeqGene record not available', warning):
                vf_d['ng_name'] = 'NULL'
            elif re.search(r'automapped to {0}\.{1}:c\..+'.format(acc_no, acc_version), warning):
                match_obj = re.search(r'automapped to {0}\.{1}:(c\..+)'.format(acc_no, acc_version), warning)
                if match_obj.group(1) is not None:
                    return_text = " VariantValidator reports that your variant should be {0} instead of {1}".format(
                        match_obj.group(1), original_variant
                    )
                    if caller == 'webApp':
                        return danger_panel(vv_key_var, return_text)
                    elif caller == 'api':
                        return {'mobidetails_error': '{}'.format(return_text)}
                else:
                    danger_panel(vv_key_var, warning)
            elif re.search('normalized', warning):
                match_obj = re.search(r'normalized to ({0}\.{1}:c\..+)'.format(acc_no, acc_version), warning)
                if match_obj.group(1) is not None and \
                        match_obj.group(1) == vv_key_var:
                    next
                elif caller == 'webApp':
                    return danger_panel(vv_key_var, warning)
                elif caller == 'api':
                    return {'mobidetails_error': '{}'.format(warning)}
            elif re.search('A more recent version of', warning) or \
                    re.search('LRG_', warning) or \
                    re.search('Whitespace', warning):
                next
            else:
                if caller == 'webApp':
                    if len(vv_data[first_level_key]['validation_warnings']) > 1:
                        return danger_panel(vv_key_var, ' '.join(vv_data[first_level_key]['validation_warnings']))
                    else:
                        return danger_panel(vv_key_var, warning)
                elif caller == 'api':
                    if len(vv_data[first_level_key]['validation_warnings']) > 1:
                        return {'mobidetails_error':  ' '.join(vv_data[first_level_key]['validation_warnings'])}
                    else:
                        return {'mobidetails_error':  '{}'.format(warning)}
    genome = 'hg38'
    # hg38
    try:
        hg38_d = get_genomic_values('hg38', vv_data, vv_key_var)
        if 'mobidetails_error' in hg38_d:
            if caller == 'webApp':
                return danger_panel('MobiDetails error', hg38_d['mobidetails_error'])
            elif caller == 'api':
                return hg38_d
    except Exception:
        if caller == 'webApp':
            return danger_panel(
                vv_key_var,
                'Transcript {0} for gene {1} does not seem to map correctly to hg38. \
                Currently, MobiDetails requires proper mapping on hg38 and hg19. It is therefore impossible to create a variant.'.format(acc_no, gene)
            )
        elif caller == 'api':
            return {'mobidetails_error':  'Transcript {0} for gene {1} does not seem to map correctly to hg38. \
                    Currently, MobiDetails requires proper mapping on hg38 and hg19. \
                    It is therefore impossible to create a variant.'.format(acc_no, gene)}
    # check again if variant exist
    curs.execute(
        "SELECT feature_id FROM variant WHERE genome_version = %s AND g_name = %s",
        (genome, hg38_d['g_name'])
    )
    res = curs.fetchone()
    if res is not None:
        if caller == 'webApp':
            return info_panel('Variant already in MobiDetails: ', vv_key_var, res['feature_id'])
        elif caller == 'api':
            return {'mobidetails_id': res['feature_id'], 'url': '{0}{1}'.format(
                request.host_url[:-1], url_for('md.variant', variant_id=res['feature_id'])
            )}
        elif caller == 'test':
            # for unit tests
            return {'mobidetails_id': res['feature_id']}
    try:
        hg19_d = get_genomic_values('hg19', vv_data, vv_key_var)
        if 'mobidetails_error' in hg19_d:
            if caller == 'webApp':
                return danger_panel('MobiDetails error', hg19_d['mobidetails_error'])
            elif caller == 'api':
                return hg19_d
    except Exception:
        if caller == 'webApp':
            return danger_panel(
                vv_key_var,
                'Transcript {0} for gene {1} does not seem to map correctly to hg19.\
                Currently, MobiDetails requires proper mapping on hg38 and hg19. \
                It is therefore impossible to create a variant.'.format(acc_no, gene)
            )
        elif caller == 'api':
            return {'mobidetails_error':  'Transcript {0} for gene {1} does not seem to map correctly to hg19. \
                    Currently, MobiDetails requires proper mapping on hg38 and hg19.\
                    It is therefore impossible to create a variant.'.format(acc_no, gene)}
    positions = compute_start_end_pos(hg38_d['g_name'])
    if 'c_name' not in vf_d:
        var_obj = re.search(r'c\.(.+)$', new_variant)
        vf_d['c_name'] = var_obj.group(1)
    if 'ng_name' not in vf_d:
        ng_name_obj = re.search(r':g\.(.+)$', vv_data[vv_key_var]['hgvs_refseqgene_variant'])
        vf_d['ng_name'] = ng_name_obj.group(1)
    # dna_type
    if re.search('>', vf_d['c_name']):
        vf_d['dna_type'] = 'substitution'
        vf_d['variant_size'] = 1
    elif re.search(r'del.*ins', vf_d['c_name']):
        vf_d['dna_type'] = 'indel'
    elif re.search('dup', vf_d['c_name']):
        vf_d['dna_type'] = 'duplication'
    elif re.search('ins', vf_d['c_name']):
        vf_d['dna_type'] = 'insertion'
    elif re.search('del', vf_d['c_name']):
        vf_d['dna_type'] = 'deletion'
    elif re.search('=', vf_d['c_name']):
        if caller == 'webApp':
            return danger_panel(vv_key_var, 'Reference should not be equal to alternative to define a variant.')
        elif caller == 'api':
            return {'mobidetails_error':  'Reference should not be equal to alternative to define a variant.'}
    if 'variant_size' not in vf_d:
        if not re.search('_', vf_d['c_name']):
            # one bp del or dup
            vf_d['variant_size'] = 1
        else:
            vf_d['variant_size'] = int(positions[1]) - int(positions[0]) + 1

    # we need strand later
    # curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # curs.execute(
    #     "SELECT strand FROM gene WHERE name = '{{\"{0}\",\"{1}\"}}'".format(gene, acc_no)
    # )
    curs.execute(
        "SELECT strand FROM gene WHERE name[1] = %s AND name[2] = %s",
        (gene, acc_no)
    )
    res_strand = curs.fetchone()
    if res_strand is None:
        if caller == 'webApp':
            return danger_panel(vv_key_var, 'No strand for gene {}, impossible to create a variant, please contact us'.format(gene))
        elif caller == 'api':
            return {'mobidetails_error': 'No strand for gene {}, impossible to create a variant, please contact us'.format(gene)}

    # p_name
    p_obj = re.search(r':p\.\((.+)\)$', vv_data[vv_key_var]['hgvs_predicted_protein_consequence']['tlr'])
    if p_obj:
        vf_d['p_name'] = p_obj.group(1)
        if re.search(r'Ter$', vf_d['p_name']):
            vf_d['prot_type'] = 'nonsense'
        elif re.search(r'fsTer\d+', vf_d['p_name']):
            vf_d['prot_type'] = 'frameshift'
        elif re.search(r'\w{3}\d+=', vf_d['p_name']):
            vf_d['prot_type'] = 'silent'
        elif re.search(r'^\?$', vf_d['p_name']):
            vf_d['prot_type'] = 'unknown'
        elif re.search(r'^Met1\?$', vf_d['p_name']):
            vf_d['prot_type'] = 'start codon'
        elif re.search(r'ext', vf_d['p_name']):
            vf_d['prot_type'] = 'stop codon'
        elif re.search(r'_\w{3}\d+del', vf_d['p_name']) or \
                re.search(r'^\w{3}\d+del', vf_d['p_name']):
            vf_d['prot_type'] = 'inframe deletion'
        elif re.search(r'_\w{3}\d+dup', vf_d['p_name']) or \
                re.search(r'^\w{3}\d+dup', vf_d['p_name']):
            vf_d['prot_type'] = 'inframe duplication'
        elif re.search(r'_\w{3}\d+ins', vf_d['p_name']):
            vf_d['prot_type'] = 'inframe insertion'
        else:
            var_obj = re.search(r'^(\w{3})\d+(\w{3})$', vf_d['p_name'])
            if var_obj.group(1) != var_obj.group(2):
                vf_d['prot_type'] = 'missense'
            else:
                vf_d['prot_type'] = 'unknown'
    else:
        vf_d['p_name'] = '?'
        vf_d['prot_type'] = 'unknown'

    # deal with +1,+2 etc
    vf_d['rna_type'] = 'neutral inferred'
    if re.search(r'\d+[\+-][12][^\d]', vf_d['c_name']):
        vf_d['rna_type'] = 'altered inferred'
    # exons pos, etc - based on hg38

    if positions[0] != positions[1]:
        # curs.execute(
        #     "SELECT number, type FROM segment WHERE genome_version = '{0}' AND \
        #     gene_name = '{{\"{1}\",\"{2}\"}}' AND '{3}' BETWEEN SYMMETRIC segment_start \
        #     AND segment_end AND {4} BETWEEN SYMMETRIC segment_start AND segment_end".format(
        #         genome, gene, acc_no, positions[0], positions[1]
        #     )
        # )
        curs.execute(
            "SELECT number, type FROM segment WHERE genome_version = %s AND \
            gene_name[1] = %s AND gene_name[2] = %s AND %s BETWEEN SYMMETRIC segment_start \
            AND segment_end AND %s BETWEEN SYMMETRIC segment_start AND segment_end",
            (genome, gene, acc_no, positions[0], positions[1])
        )
        res_seg = curs.fetchone()
        if res_seg is not None:
            # start - end in same segment
            vf_d['start_segment_type'] = res_seg['type']
            vf_d['start_segment_number'] = res_seg['number']
            vf_d['end_segment_type'] = res_seg['type']
            vf_d['end_segment_number'] = res_seg['number']
        else:
            curs.execute(
                "SELECT number, type FROM segment WHERE genome_version = %s \
                AND gene_name[1] = %s AND gene_name[2] = %s AND %s \
                BETWEEN SYMMETRIC segment_start AND segment_end ",
                (genome, gene, acc_no, positions[0])
            )
            res_seg1 = curs.fetchone()
            curs.execute(
                "SELECT number, type FROM segment WHERE genome_version = %s \
                AND gene_name[1] = %s AND gene_name[2] = %s AND %s \
                BETWEEN SYMMETRIC segment_start AND segment_end ",
                (genome, gene, acc_no, positions[1])
            )
            res_seg2 = curs.fetchone()
            if res_strand['strand'] == '+':
                vf_d['start_segment_type'] = res_seg1['type']
                vf_d['start_segment_number'] = res_seg1['number']
                vf_d['end_segment_type'] = res_seg2['type']
                vf_d['end_segment_number'] = res_seg2['number']
            else:
                vf_d['start_segment_type'] = res_seg2['type']
                vf_d['start_segment_number'] = res_seg2['number']
                vf_d['end_segment_type'] = res_seg1['type']
                vf_d['end_segment_number'] = res_seg1['number']
        # get IVS name
        if vf_d['start_segment_type'] == 'intron':
            ivs_obj = re.search(r'^\d+([\+-]\d+)_\d+([\+-]\d+)(.+)$', vf_d['c_name'])
            if ivs_obj:
                vf_d['ivs_name'] = 'IVS{0}{1}_IVS{2}{3}{4}'.format(
                    vf_d['start_segment_number'], ivs_obj.group(1),
                    vf_d['end_segment_number'], ivs_obj.group(2), ivs_obj.group(3)
                )
            else:
                ivs_obj = re.search(r'^\d+([\+-]\d+)_(\d+)([^\+-].+)$', vf_d['c_name'])
                if ivs_obj:
                    vf_d['ivs_name'] = 'IVS{0}{1}_{2}{3}'.format(
                        vf_d['start_segment_number'], ivs_obj.group(1),
                        ivs_obj.group(2), ivs_obj.group(3)
                    )
                else:
                    ivs_obj = re.search(r'^(\d+)_\d+([\+-]\d+)(.+)$', vf_d['c_name'])
                    if ivs_obj:
                        vf_d['ivs_name'] = '{0}_IVS{1}{2}{3}'.format(
                            ivs_obj.group(1), vf_d['end_segment_number'],
                            ivs_obj.group(2), ivs_obj.group(3)
                        )
    else:
        # substitutions
        # print("SELECT number, type FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}'\
        # AND '{3}' BETWEEN SYMMETRIC segment_start AND segment_end ".format(genome, gene, acc_no, positions[0]))
        curs.execute(
            "SELECT number, type FROM segment WHERE genome_version = %s \
            AND gene_name[1] = %s AND gene_name[2] = %s AND %s \
            BETWEEN SYMMETRIC segment_start AND segment_end ",
            (genome, gene, acc_no, positions[0])
        )
        res_seg = curs.fetchone()
        vf_d['start_segment_type'] = res_seg['type']
        vf_d['start_segment_number'] = res_seg['number']
        vf_d['end_segment_type'] = res_seg['type']
        vf_d['end_segment_number'] = res_seg['number']
        if vf_d['start_segment_type'] == 'intron':
            ivs_obj = re.search(r'^-?\d+([\+-]\d+)(.+)$', vf_d['c_name'])
            # print(vf_d['c_name'])
            vf_d['ivs_name'] = 'IVS{0}{1}{2}'.format(
                vf_d['start_segment_number'], ivs_obj.group(1), ivs_obj.group(2)
            )
    if 'ivs_name' not in vf_d:
        vf_d['ivs_name'] = 'NULL'
    ncbi_chr = get_ncbi_chr_name(db, 'chr{}'.format(hg38_d['chr']), 'hg38')
    hg38_d['chr'] = ncbi_chr[0]
    record = get_value_from_tabix_file('dbsnp', local_files['dbsnp'][0], hg38_d)
    reg_chr = get_common_chr_name(db, ncbi_chr[0])
    hg38_d['chr'] = reg_chr[0]
    if isinstance(record, str):
        vf_d['dbsnp_id'] = 'NULL'
    else:
        match_object = re.search(r'RS=(\d+);', record[7])
        if match_object:
            vf_d['dbsnp_id'] = match_object.group(1)
        # print(record[7])
    # get wt sequence using twobitreader module
    # 0-based
    if vf_d['variant_size'] < 50:
        x = int(positions[0])-26
        y = int(positions[1])+25
        genome = twobitreader.TwoBitFile(local_files['human_genome_hg38'][0])
        current_chrom = genome['chr{}'.format(hg38_d['chr'])]
        seq_slice = current_chrom[x:y].upper()
        # seq2 = current_chrom[int(positions[0])+1:int(positions[0])+2]
        # return seq2
        if res_strand['strand'] == '-':
            seq_slice = reverse_complement(seq_slice).upper()
        begin = seq_slice[:25]
        middle = seq_slice[25:len(seq_slice)-25]
        end = seq_slice[-25:]
        # substitutions
        if vf_d['dna_type'] == 'substitution':
            vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
            mt_obj = re.search(r'>([ATGC])$', vf_d['c_name'])
            vf_d['mt_seq'] = "{0} {1} {2}".format(begin, mt_obj.group(1), end)
        elif vf_d['dna_type'] == 'indel':
            ins_obj = re.search(r'delins([ATGC]+)', vf_d['c_name'])
            exp_size = abs(len(middle)-len(ins_obj.group(1)))
            exp = ''
            for i in range(0, exp_size):
                exp += '-'
            if len(middle) > len(ins_obj.group(1)):
                vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
                vf_d['mt_seq'] = "{0} {1}{2} {3}".format(begin, ins_obj.group(1), exp, end)
            else:
                vf_d['wt_seq'] = "{0} {1}{2} {3}".format(begin, middle, exp, end)
                vf_d['mt_seq'] = "{0} {1} {2}".format(begin, ins_obj.group(1), end)
        elif vf_d['dna_type'] == 'insertion':
            ins_obj = re.search(r'ins([ATGC]+)', vf_d['c_name'])
            exp = ''
            for i in range(0, len(ins_obj.group(1))):
                exp += '-'
            vf_d['wt_seq'] = "{0} {1} {2}".format(begin, exp, end)
            vf_d['mt_seq'] = "{0} {1} {2}".format(begin, ins_obj.group(1), end)
        elif vf_d['dna_type'] == 'deletion':
            vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
            exp = ''
            for i in range(0, vf_d['variant_size']):
                exp += '-'
            vf_d['mt_seq'] = "{0} {1} {2}".format(begin, exp, end)
        elif vf_d['dna_type'] == 'duplication':
            exp = ''
            for i in range(0, vf_d['variant_size']):
                exp += '-'
            vf_d['wt_seq'] = "{0} {1}{2} {3}".format(begin, middle, exp, end)
            vf_d['mt_seq'] = "{0} {1}{1} {2}".format(begin, middle, end)
        # return "-{0}-{1}-{2}-{3}-{4}-{5}-{6}-{7}".format(seq_slice, begin, middle, end, vf_d['wt_seq'], vf_d['mt_seq'], x, y)
    # get intervar automated class
    # too long
    # vf_d['acmg_class'] = 3
    # if vf_d['variant_size'] > 1:
    #     vf_d['acmg_class'] = 3
    # elif (vf_d['dna_type'] == 'substitution' and
    #         vf_d['start_segment_type'] == 'exon' and
    #         re.search(r'^[^\*-]', vf_d['c_name']) and
    #         vf_d['p_name'] != 'Met1?' and
    #         hg19_d['pos_ref'] != hg19_d['pos_alt']):
    #     # intervar api returns empty results with hg38 09/2019
    #     http = urllib3.PoolManager()
    #     intervar_url = "{0}{1}_updated.v.201904&chr={2}&pos={3}&ref={4}&alt={5}".format(
    #         urls['intervar_api'], 'hg19', hg19_d['chr'],
    #         hg19_d['pos'], hg19_d['pos_ref'], hg19_d['pos_alt']
    #     )
    #     intervar_json = None
    #     try:
    #         intervar_json = json.loads(http.request('GET', intervar_url).data.decode('utf-8'))
    #     except Exception as e:
    #         send_error_email(
    #             prepare_email_html(
    #                 'MobiDetails error',
    #                 '<p>Intervar API call failed in {0} for {1} with args: {2}</p>'.format(
    #                     os.path.basename(__file__),
    #                     intervar_url,
    #                     e.args
    #                 )
    #             ),
    #             '[MobiDetails - Code Error]'
    #         )
    #     # return intervar_data
    #     if intervar_json is not None:
    #         curs.execute(
    #             "SELECT acmg_class FROM valid_class WHERE acmg_translation = %s",
    #             (intervar_json['Intervar'].lower(),)
    #         )
    #         res_acmg = curs.fetchone()
    #         if res_acmg is not None:
    #             vf_d['acmg_class'] = res_acmg['acmg_class']
    #     else:
    #         vf_d['acmg_class'] = 3
    # else:
    #     vf_d['acmg_class'] = 3
    # date, user
    mobiuser = 'mobidetails'
    if caller == 'webApp':
        if g.user is not None:
            mobiuser = g.user['username']
        curs.execute(
            "SELECT id FROM mobiuser WHERE username = %s",
            (mobiuser,)
        )
        vf_d['creation_user'] = curs.fetchone()['id']
    elif caller == 'api':
        vf_d['creation_user'] = g.user['id']

    today = datetime.datetime.now()
    vf_d['creation_date'] = '{0}-{1}-{2}'.format(
        today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
    )

    s = ", "
    # attributes =
    t = "', '"
    insert_variant_feature = "INSERT INTO variant_feature (gene_name, {0}) VALUES ('{{\"{1}\",\"{2}\"}}', '{3}') RETURNING id".format(
        s.join(vf_d.keys()), gene, acc_no,
        t.join(map(str, vf_d.values()))
    ).replace("'NULL'", "NULL")
    # insert_query = "INSERT INTO variant_features (c_name, gene_name, ng_name, ivs_name, p_name, \
    # wt_seq, mt_seq, dna_type, rna_type, prot_type, acmg_class, start_segment_type, start_segment_number, \
    # end_segment_type, end_segment_number, variant_size, dbsnp_id, creation_date, creation_user) VALUES \
    # ('{0}', '{\"{1}\",\"{2}\"}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}',\
    # '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}')".format(
    # vf_d['c_name'], gene, acc_no, vf_d['ng_name'], vf_d['ivs_name'], vf_d['p_name'], vf_d['wt_seq'], vf_d['mt_seq'],
    # vf_d['dna_type'], vf_d['rna_type'], vf_d['prot_type'], vf_d['acmg_class'], vf_d['start_segment_type'], vf_d['start_segment_number'],
    # vf_d['end_segment_type'], vf_d['end_segment_number'], vf_d['variant_size'], vf_d['dbsnp_id'], vf_d['creation_date'], vf_d['creation_user']
    # )
    # print(insert_variant_feature)
    try:
        curs.execute(insert_variant_feature)
        vf_id = curs.fetchone()[0]
    except Exception as e:
        if caller == 'webApp':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    '<p>Insertion failed for variant features for {0} with args {1}</p>'.format(vv_key_var, e.args)
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                'Sorry, an issue occured with variant features. An admin has been warned'
            )
        elif caller == 'api':
            return {'mobidetails_error': 'Impossible to insert variant_features for {}'.format(vv_key_var)}
    # print(vf_id)
    # vf_id = 55
    insert_variant_38 = "INSERT INTO variant (feature_id, {0}) VALUES ('{1}', '{2}')".format(
        s.join(hg38_d.keys()), vf_id,
        t.join(map(str, hg38_d.values()))
    )
    try:
        curs.execute(insert_variant_38)
    except Exception as e:
        if caller == 'webApp':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    '<p>Insertion failed for variant hg38 for {0} with args: {1}</p>'.format(vv_key_var, e.args)
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                'Sorry, an issue occured with variant mapping in hg38. An admin has been warned'
            )
        elif caller == 'api':
            return {'mobidetails_error': 'Impossible to insert variant (hg38) for {}'.format(vv_key_var)}
    insert_variant_19 = "INSERT INTO variant (feature_id, {0}) VALUES ('{1}', '{2}')".format(
        s.join(hg19_d.keys()), vf_id,
        t.join(map(str, hg19_d.values()))
    )
    try:
        curs.execute(insert_variant_19)
    except Exception as e:
        if caller == 'webApp':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    '<p>Insertion failed for variant hg19 for {0} with args {1}</p>'.format(vv_key_var, e.args)
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                'Sorry, an issue occured with variant mapping in hg19. An admin has been warned'
            )
        elif caller == 'api':
            return {'mobidetails_error': 'Impossible to insert variant (hg19) for {}'.format(vv_key_var)}
    db.commit()
    print("--- %s seconds ---" % (time.time() - start_time))
    if remapper is True and caller == 'webApp':
        return info_panel("Successfully created variant (remapped to canonical isoform)", vf_d['c_name'], vf_id, 'w3-pale-green')
    elif caller == 'webApp':
        return info_panel("Successfully created variant", vf_d['c_name'], vf_id, 'w3-pale-green')
    if caller == 'api':
        return {'mobidetails_id': vf_id, 'url': '{0}{1}'.format(
            request.host_url[:-1], url_for('md.variant', variant_id=vf_id)
        )}


def get_genomic_values(genome, vv_data, vv_key_var):
    if vv_data[vv_key_var]['primary_assembly_loci'][genome]:
        g_name_obj = re.search(r':g\.(.+)$', vv_data[vv_key_var]['primary_assembly_loci'][genome]['hgvs_genomic_description'])
        chr_obj = re.search(r'chr([\dXYM]{1,2})$', vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['chr'])
        if len(vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['ref']) > 49 or \
                len(vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['alt']) > 49:
            # flash('MobiDetails currently only accepts variants of length < 50 bp (SNVs ans small insertions/deletions', 'w3-pale-red')
            # flash is only useful if we return a new page which is not the case here
            return {'mobidetails_error': 'MobiDetails currently only accepts variants of length < 50 bp (SNVs ans small insertions/deletions)'}
        return {
            'genome_version': genome,
            'g_name': g_name_obj.group(1),
            'chr': chr_obj.group(1),
            'pos': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['pos'],
            'pos_ref': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['ref'],
            'pos_alt': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['alt']
        }


def prepare_email_html(title, message, send_url=True):
    if send_url is False:
        return render_template('md/email.html', title=title, message=message, url='')
    else:
        return render_template('md/email.html', title=title, message=message, url=request.base_url)


def send_email(message, mail_object, receiver, bcc_receiver = None):
    if "MAIL_USERNAME" in app.config:
        msg = Message(
            mail_object,
            sender=app.config["MAIL_USERNAME"],
            recipients=receiver,
            bcc=bcc_receiver
        )
        msg.html = message
        mail.send(msg)
        


def send_error_email(message, mail_object):
    if "MAIL_USERNAME" in app.config:
        msg = Message(
            mail_object,
            # sender=params['mail_username'],
            sender=app.config["MAIL_USERNAME"],
            # recipients=[params['mail_error_recipient']]
            recipients=[app.config["MAIL_ERROR_RECIPIENT"]]
        )
        msg.html = message
        mail.send(msg)


def maxentscan(w, y, seq, scantype, a=0, x=26):
    # takes a sequence and positions as input
    # returns a list of sequences
    # a = window slider
    # x = pos 1st nt / mutation (26)
    # y = len(var)
    # z = len(resulting seq) must be = 9|23
    # w = len(seq required) = 9|23
    # print('{0}-{1}-{2}-{3}'.format(w, y, seq, scantype))
    z = w
    seq = seq.replace(' ', '')
    seq = seq.replace('-', '')
    # html_seq = '{0}<span class="w3-text-red"><strong>{1}</strong></span>{2}'.format(seq[:25], seq[25:25+y], seq[25+y:])
    # y = variant_features['variant_size']
    pos1 = pos2 = 0
    seqs = []
    seqs_html = []
    while z == w and \
            a < y + w -1 and \
            pos2 < len(seq):
        pos1 = x - (w - y) + a
        pos2 = x + (a + y - 1)
        z = (pos2 - pos1 + 1)
        # print('{0}-{1}'.format(pos1-1, pos2))
        # get substring
        # seqs.append('>{0}{1}\n{2}\n'.format(seqtype, a, seq[pos1-1:pos2]))
        interest_seq = '{}\n'.format(seq[pos1-1:pos2])
        seqs.append(interest_seq)
        # we need to html highlight the mutant sequence so to retrieve it here
        # r is the beginning of the subseq and defined as "((len(seq required 4 maxent; 9 or 23) - window position - 1) - (len(var) -1)))
        # s is the end of the substring being r + len(var)
        # limitation for delins => the size is the size of the deleted sequence
        r = (w - a - 1) - (y - 1)
        s = r + y
        #we need to remap r and s if < 0
        if (r < 0):
            r = 0
            s = s + abs(r)
            if s < 0:
                s = 0
        # print('r: {0};s: {1}'.format(r, s))
        # print('{0}<span class="w3-text-red"><strong>{1}</strong></span>{2}'.format(interest_seq[:r], interest_seq[r:s], interest_seq[s:]))
        seqs_html.append('{0}<span class="w3-text-red"><strong>{1}</strong></span>{2}'.format(interest_seq[:r], interest_seq[r:s], interest_seq[s:]))        
        a += 1
    # create temp file and launch maxentscan
    tf = tempfile.NamedTemporaryFile()
    # print(tf.name)
    tf.write(bytes(''.join(seqs), encoding = 'utf-8'))
    tf.seek(0)
    # cannot figure out why the above line is mandatory but without it the file is empty
    # print(tf.read())
    result = subprocess.run(['/usr/bin/perl', '{}'.format(ext_exe['maxentscan{}'.format(scantype)]), '{}'.format(tf.name)], stdout=subprocess.PIPE)
    # print(result)
    # print(str(result.stdout))
    return [str(result.stdout, 'utf-8'), seqs_html]


def select_mes_scores(scoreswt, html_wt, scoresmt, html_mt, cutoff, threshold):
    # get 2 lists of wt and mt scores, returns only those
    # which have a 15% variation
    signif_scores = {}
    for i in range(len(scoreswt)):
        # a score is
        # CAAATTCTG\t-17.88
        if i < len(scoresmt):
            wt = re.split('\s+', scoreswt[i])
            mt = re.split('\s+', scoresmt[i])
            if len(wt) == 2 and \
                    len(mt) == 2:
                if float(wt[1]) !=0:
                    variation = (float(mt[1]) - float(wt[1])) / abs(float(wt[1]))
                else:
                    variation = float(wt[1])
                if abs(variation) >= float(cutoff) and (float(mt[1]) > threshold or float(wt[1]) > threshold):
                    # get span with exon/intron depending on score5 or score 3
                    html_seqwt = html_seqmt = ''
                    if len(wt[0]) == 9:
                        #score 5
                        html_seqwt = '<strong>{0}</strong>{1}'.format(wt[0][:3], wt[0][3:].lower())
                        html_seqmt = '<strong>{0}</strong>{1}'.format(mt[0][:3], mt[0][3:].lower())
                    else:
                        html_seqwt = '{0}<strong>{1}</strong>'.format(wt[0][:20].lower(), wt[0][20:])
                        html_seqmt = '{0}<strong>{1}</strong>'.format(mt[0][:20].lower(), mt[0][20:])
                    signif_scores[i] = [wt[0], wt[1], mt[0], mt[1], round(variation*100, 2), html_wt[i], html_seqwt, html_mt[i], html_seqmt]
    return signif_scores


def get_maxent_natural_sites_scores(chrom, strand, scantype, positions):
    # 1st we need the sequences and therefore determine start and end of interest
    x = y = None
    if scantype == 3:
        if strand == '+':
            x = positions['segment_start']-21
            y = positions['segment_start']+2
        else:
            x = positions['segment_start']-3
            y = positions['segment_start']+20

    else:
        if strand == '+':
            x = positions['segment_end']-3
            y = positions['segment_end']+6
        else:
            x = positions['segment_end']-7
            y = positions['segment_end']+2

    genome = twobitreader.TwoBitFile(local_files['human_genome_hg38'][0])
    current_chrom = genome['chr{}'.format(chrom)]
    seq_slice = current_chrom[x:y].upper()
    if strand == '-':
        seq_slice = reverse_complement(seq_slice).upper()
    # create temp file and launch maxentscan
    tf = tempfile.NamedTemporaryFile()
    # print(tf.name)
    tf.write(bytes(seq_slice, encoding = 'utf-8'))
    tf.seek(0)
    if scantype == 3:
        formatted_seq = '{0}{1}'.format(seq_slice[:20].lower(), seq_slice[20:])
    else:
        formatted_seq = '{0}{1}'.format(seq_slice[:3], seq_slice[3:].lower())
    # cannot figure out why the above line is mandatory but without it the file is empty
    # print(tf.read())
    result = subprocess.run(['/usr/bin/perl', '{}'.format(ext_exe['maxentscan{}'.format(scantype)]), '{}'.format(tf.name)], stdout=subprocess.PIPE)
    return [float(re.split('\n', re.split('\t', str(result.stdout, 'utf-8'))[1])[0]), formatted_seq]
