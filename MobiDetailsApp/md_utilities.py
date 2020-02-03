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
from flask import (
    url_for, request, current_app as app
)
from flask_mail import Message
from . import config
from MobiDetailsApp import mail
#from MobiDetailsApp.db import get_db

app_path = os.path.dirname(os.path.realpath(__file__))
one2three = {
	'A': 'Ala', 'C': 'Cys', 'D': 'Asp', 'E': 'Glu', 'F': 'Phe', 'G': 'Gly', 'H': 'His', 'I': 'Ile', 'K': 'Lys', 'L': 'Leu', 'M': 'Met', 'N': 'Asn', 'P': 'Pro', 'Q': 'Gln', 'R': 'Arg', 'S': 'Ser', 'T': 'Thr', 'V': 'Val', 'W': 'Trp', 'Y': 'Tyr', 'del': 'del', 'X': 'Ter', '*': 'Ter', '=': '=', 'Ter': 'Ter'
}
three2one = {
	'Ala': 'A', 'Cys': 'C', 'Asp': 'D', 'Glu': 'E', 'Phe': 'F', 'Gly': 'G', 'His': 'H', 'Ile': 'I', 'Lys': 'K', 'Leu': 'L', 'Met': 'M', 'Asn': 'N', 'Pro': 'P', 'Gln': 'Q', 'Arg': 'R', 'Ser': 'S', 'Thr': 'T', 'Val': 'V', 'Trp': 'W', 'Tyr': 'Y', 'Del': 'del', 'X': 'Ter', '*': 'Ter', '=': '=', 'Ter': 'Ter'
}
url_ncbi = 'https://www.ncbi.nlm.nih.gov/'
urls = {
	'uniprot_id': 'http://www.uniprot.org/uniprot/',
	'ncbi_nuccore':  '{}nuccore/'.format(url_ncbi),
	'ncbi_prot': '{}protein/'.format(url_ncbi),
	'ncbi_dbsnp': '{}snp/'.format(url_ncbi),
	'ncbi_clinvar': '{}clinvar'.format(url_ncbi),
	'ncbi_1000g': '{}variation/tools/1000genomes/?'.format(url_ncbi),
	'ncbi_gene': '{}gene/?term='.format(url_ncbi),
	'ncbi_pubmed': '{}pubmed/'.format(url_ncbi),
	'ncbi_litvar_api': '{}research/bionlp/litvar/api/v1/public/rsids2pmids?rsids='.format(url_ncbi),
	#'ncbi_litvar_api': '{}research/bionlp/litvar/api/v1/public/pmids?query=%7B%22variant%22%3A%5B%22litvar%40'.format(url_ncbi),
	'mutalyzer_name_checker': 'https://mutalyzer.nl/name-checker?description=',
	'mutalyzer_position_converter': 'https://mutalyzer.nl/position-converter?assembly_name_or_alias=',
	'variant_validator': 'https://variantvalidator.org/variantvalidation/?variant=',
	#uncomment below to use VV web API
	'variant_validator_api': 'https://rest.variantvalidator.org/',
	'variant_validator_api_info': 'https://rest.variantvalidator.org/webservices/variantvalidator/_/resource_list.json',
	#'variant_validator_api': 'http://0.0.0.0:8000/',
	#'variant_validator_api_info': 'http://0.0.0.0:8000/webservices/variantvalidator/_/resource_list.json',
	'ucsc_hg19': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg19&lastVirtModeType=default&lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
	'ucsc_hg19_session': '757149165_H4Gy8jWA4BwCuA6WW1M8UxC37MFn',
	'ucsc_hg38': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&lastVirtModeType=default&lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
	'ucsc_hg38_session': '757151741_tUQRsEoYvqXsPekoiKpwY6Ork8eF',
	'ucsc_2bit': 'http://genome.ucsc.edu/goldenPath/help/twoBit.html',
	'map2pdb': 'http://www.rcsb.org/pdb/chromosome.do?v=',
	'evs': 'http://evs.gs.washington.edu/EVS/PopStatsServlet?searchBy=chromosome',
	'gnomad': 'http://gnomad.broadinstitute.org/',
	'hgvs': 'http://varnomen.hgvs.org/',
	'ensembl_t': 'http://ensembl.org/Homo_sapiens/Transcript/Summary?t=',
	'marrvel': 'http://marrvel.org/search/gene/',
	'dbscsnv': 'http://www.liulab.science/dbscsnv.html',
	'dbnsfp': 'https://sites.google.com/site/jpopgen/dbNSFP',
	'spliceai': 'https://github.com/Illumina/SpliceAI',
	'sift': 'https://sift.bii.a-star.edu.sg/',
	'pph2': 'http://genetics.bwh.harvard.edu/pph2/',
	'fathmm': 'http://fathmm.biocompute.org.uk/',
	'intervar': 'http://wintervar.wglab.org/results.pos.php?queryType=position&build=',
	'intervar_api': 'http://wintervar.wglab.org/api_new.php?queryType=position&build=',
	'lovd': 'http://www.lovd.nl/',
	'cadd': 'https://cadd.gs.washington.edu/',
	'mp': 'https://github.com/mobidic/MPA',
	'metadome': 'https://stuart.radboudumc.nl/metadome/',
	'metadome_api': 'https://stuart.radboudumc.nl/metadome/api/',
	'revel': 'https://sites.google.com/site/revelgenomics/',
}
local_files = {
	# id :[local path, version, name, short desc, urls Xref]
	'clinvar_hg38': [app_path + '/static/resources/clinvar/hg38/clinvar_20200127.vcf.gz', 'v20200127', 'ClinVar', 'database of variants, clinically assessed', 'ncbi_clinvar'],
	'gnomad_exome': [app_path + '/static/resources/gnomad/hg19_gnomad_exome_sorted.txt.gz', 'v2.0.1', 'gnomAD exome', 'large dataset of variants population frequencies', 'gnomad'],
	'gnomad_genome': [app_path + '/static/resources/gnomad/hg19_gnomad_genome_sorted.txt.gz', 'v2.0.1', 'gnomAD genome', 'large dataset of variants population frequencies', 'gnomad'],
	'dbscsnv': [app_path + '/static/resources/dbscSNV/hg19/dbscSNV.txt.gz', 'v1.1', 'dbscSNV', 'Dataset of splicing predictions', 'dbscsnv'],
	#'spliceai': [app_path + '/static/resources/spliceai/hg19/exome_spliceai_scores.vcf.gz', 'v1.2.1', 'spliceAI', 'Dataset of splicing predictions', 'spliceai'],
	'spliceai_snvs': [app_path + '/static/resources/spliceai/hg38/spliceai_scores.raw.snv.hg38.vcf.gz', 'v1.3', 'spliceAI SNVs', 'Dataset of splicing predictions', 'spliceai'],
	'spliceai_indels': [app_path + '/static/resources/spliceai/hg38/spliceai_scores.raw.indel.hg38.vcf.gz', 'v1.3', 'spliceAI Indels', 'Dataset of splicing predictions', 'spliceai'],
	'dbnsfp': [app_path + '/static/resources/dbNSFP/v4_0/dbNSFP4.0a.txt.gz', 'v4.0a', 'dbNSFP', 'Dataset of predictions for missense', 'dbnsfp'],
	'cadd': [app_path + '/static/resources/CADD/hg38/whole_genome_SNVs.tsv.gz', 'v1.5', 'CADD SNVs', 'Prediction of deleterious effect for all variant types', 'cadd'],
	'cadd_indels': [app_path + '/static/resources/CADD/hg38/InDels.tsv.gz', 'v1.5', 'CADD indels', 'Prediction of deleterious effect for all variant types', 'cadd'],
	'dbsnp': [app_path + '/static/resources/dbsnp/hg38/All_20180418.vcf.gz', 'v153', 'dbSNP', 'Database of human genetic variations', 'ncbi_dbsnp'],
	'metadome': [app_path + '/static/resources/metadome/v1/', 'v1.0.1', 'metadome scores', 'mutation tolerance at each position in a human protein', 'metadome'],
	'human_genome_hg38': [app_path + '/static/resources/genome/hg38.2bit', 'hg38', 'Human genome sequence', 'Human genome sequence chr by chr (2bit format)', 'ucsc_2bit'],
	'human_genome_hg19': [app_path + '/static/resources/genome/hg19.2bit', 'hg19', 'Human genome sequence', 'Human genome sequence chr by chr (2bit format)', 'ucsc_2bit']	
	#'dbNSFP_base': [app_path + '/static/resources/dbNSFP/v4_0/dbNSFP4.0a_variant.chr', '4.0a', 'dbNSFP', 'Dataset of predictions for missense'],
}
predictor_thresholds = {
	'spliceai_min': 0.2,
	'spliceai_mid': 0.5,
	'spliceai_max': 0.8,
	'dbscsnv': 0.8,
	'sift': 0.95, #SIFT is reversed
	'pph2_hdiv_max': 0.957,
	'pph2_hdiv_mid': 0.454,
	'pph2_hvar_max': 0.909,
	'pph2_hvar_mid': 0.447,
	'fathmm': -1.5,
	'fathmm-mkl': -1.5,
	'meta-lr': 0.5,
	'lrt': 0.5,#must be precised - which is not solely determined by the score. => take pred directly into account?
	'meta-svm': 0,
	'provean': -2.5,
	'mpa_max': 8,
	'mpa_mid': 6,
	'metadome_hintolerant': 0.175,
	'metadome_intolerant': 0.52,
	'metadome_sintolerant': 0.7,
	'metadome_neutral': 0.875,
	'metadome_stolerant': 1.025,
	'metadome_tolerant': 1.375,
	'revel_min': 0.2,
	'revel_max': 0.8,
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
	'basic': {'D': 'Damaging', 'T': 'Tolerated', '.': 'no prediction', 'N': 'Neutral', 'U': 'Unknown'},
	'pph2': {'D': 'Probably Damaging', 'P': 'Possibly Damaging', 'B': 'Benign', '.': 'no prediction'},
	'mt': {'A': 'Disease causing automatic', 'D': 'Disease causing', 'N': 'polymorphism', 'P': 'polymorphism automatic', '.': 'no prediction'},#mutation taster
	'revel': {'D': 'Damaging', 'U': 'Uncertain', 'B': 'Benign', '.': 'no prediction'}
}

complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
def reverse_complement(seq):
	return "".join(complement[base] for base in reversed(seq.upper()))
#useless as dbNSFP has been concatenated in a single file
#def get_dbNSFP_file(chrom):
#	return local_files['dbNSFP_base'][0] + chrom + '.gz'



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
	


#get NCBI chr names for common names
def get_ncbi_chr_name(db, chr_name, genome):
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	if is_valid_full_chr(chr_name) == True:
		short_chr = get_short_chr_name(chr_name)
		if short_chr is not None:
			curs.execute(
				"SELECT ncbi_name FROM chromosomes WHERE genome_version = '{0}' AND name = '{1}'".format(genome, short_chr)
			)
			ncbi_name = curs.fetchone()
			print(ncbi_name)
			if ncbi_name is not None:
				return ncbi_name

#get common chr names for NCBI names
def get_common_chr_name(db, ncbi_name):
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	if is_valid_ncbi_chr(ncbi_name) == True:
		curs.execute(
			"SELECT name, genome_version FROM chromosomes WHERE ncbi_name = '{}'".format(ncbi_name)
		)
		res = curs.fetchone()
		if res is not None:
			return res
		
#chr name is valid?
def is_valid_full_chr(chr_name):
	if re.search(r'^[Cc][Hh][Rr](\d{1,2}|[XYM])$', chr_name):
		return True
	return False

#get small chr name
def get_short_chr_name(chr_name):
	match_obj = re.search(r'^[Cc][Hh][Rr](\d{1,2}|[XYM])$', chr_name)
	if match_obj is not None:
		return match_obj.group(1)

#chr name is valid?
def is_valid_chr(chr_name):
	if re.search(r'^(\d{1,2}|[XYM])$', chr_name):
		return True
	return False

#NCBI chr name is valid?
def is_valid_ncbi_chr(chr_name):
	if re.search(r'^[Nn][Cc]_0000\d{2}\.\d{1,2}$', chr_name):
		return True
	return False

#compute position relative to nearest splice site
def get_pos_splice_site(db, pos, seg_type, seg_num, gene, genome='hg38'):
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#main isoform?
	curs.execute(
		"SELECT segment_start, segment_end FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND type = '{3}' AND number = '{4}'".format(genome, gene[0], gene[1], seg_type, seg_num, genome)
	)
	positions = curs.fetchone()
	if positions is not None:
		#print("{0}-{1}-{2}".format(positions['segment_start'],pos,positions['segment_end']))
		if abs(int(positions['segment_end'])-int(pos)+1) <= abs(int(positions['segment_start'])-int(pos)+1):
			#near from segment_end
			#if seg_type == 'exon':
			#always exons!!!!
			return ['donor', abs(int(positions['segment_end'])-int(pos))+1]
		else:
			#near from segment_start
			#if seg_type == 'exon':
			return ['acceptor', abs(int(positions['segment_start'])-int(pos))+1]
#get position of intronic variant to the nearest ss
def get_pos_splice_site_intron(name):
	match_obj = re.search(r'\d+[\+-](\d+)[^\d_]', name)
	if match_obj:
		return match_obj.group(1)
	match_obj = re.search(r'\d+[\+-](\d+)_\d+[\+-](\d+)[^\d_]', name)
	if match_obj:
		return min(match_obj.group(1), match_obj.group(2))
		
#get aa position fomr hgvs p. (3 letter)
def get_aa_position(hgvs_p):
	match_object = re.match('^\w{3}(\d+)_\w{3}(\d+)[^\d]+$', hgvs_p)
	if match_object:
		#return "{0}_{1}".format(match_object.group(1), match_object.group(2))
		return match_object.group(1), match_object.group(2)
	match_object = re.match('^\w{3}(\d+)[^\d]+.*$', hgvs_p)
	if match_object:
		return match_object.group(1), match_object.group(1)
	
	
#open a file with tabix and look for a record:
def get_value_from_tabix_file(text, tabix_file, var):
	tb = tabix.open(tabix_file)
	records = tb.querys("{0}:{1}-{2}".format(var['chr'], var['pos'], var['pos']))
	i = 3
	if re.search('(dbNSFP|Indels|whole_genome_SNVs|dbscSNV)', tabix_file):
		i -= 1
	#print(records)
	for record in records:
		#print(record)
		if record[i] == var['pos_ref'] and record[i+1] == var['pos_alt']:
			return record
		elif record[i] == var['pos_ref'] and (re.search(r'{},'.format(var['pos_alt']), record[i+1]) or re.search(r',{}'.format(var['pos_alt']), record[i+1])):
			#multiple alts
			return record 
	return 'No match in {}'.format(text)

#manage dbNSFP scores and values
def getdbNSFP_results(transcript_index, score_index, pred_index, sep, translation_mode, threshold_for_other, direction_for_other, dbnsfp_record):
	score = '.'
	pred = 'no prediction'
	star = ''
	try:
		score = re.split('{}'.format(sep), dbnsfp_record[score_index])[transcript_index]
		if pred_index != score_index:
			pred = predictors_translations[translation_mode][re.split('{}'.format(sep), dbnsfp_record[pred_index])[transcript_index]]
			if score == '.':#search most deleterious in other isoforms
				score, pred, star = get_most_other_deleterious_pred(dbnsfp_record[score_index], dbnsfp_record[pred_index], threshold_for_other, direction_for_other, translation_mode)
	except:
		try:
			score = dbnsfp_record[score_index]
			if pred_index != score_index:
				pred = predictors_translations[translation_mode][dbnsfp_record[pred_index]]
		except:
			pass
	return score, pred, star


#returns an html color depending on spliceai score
def get_spliceai_color(val):
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
	
#returns most deleterious score of predictors when not found in desired transcript
def get_most_other_deleterious_pred(score, pred, threshold, direction, pred_type):
	j = 0
	k = 0
	best_score = threshold
	for score in re.split(';', score):
		if direction == 'lt':
			if score != '.' and float(score) < float(best_score):
				best_score = score
				k = j
		else:
			if score != '.' and float(score) > float(best_score):
				best_score = score
				k = j
		j += 1
	if best_score != threshold:
		return best_score, predictors_translations[pred_type][re.split(';', pred)[k]], '*'
	else:
		return '.', 'no prediction', ''
#returns an html color depending on a single threshold
def get_preditor_single_threshold_color(val, predictor):
	#function to get green or red
	if val != '.':
		value = float(val)
		if predictor == 'sift':
			value = 1-(float(val))
		if value > predictor_thresholds[predictor]:
			return predictor_colors['max']
		return predictor_colors['min']
	else:
		return predictor_colors['no_effect']
#returns an html color depending on a single threshold (reverted, e.g. for fathmm)
def get_preditor_single_threshold_reverted_color(val, predictor):
	#function to get green or red
	if val != '.':
		if float(val) < predictor_thresholds[predictor]:
			return predictor_colors['max']
		return predictor_colors['min']
	else:
		return predictor_colors['no_effect']
#returns an html color depending on a double threshold
def get_preditor_double_threshold_color(val, predictor_min, predictor_max):
	#function to get green or red
	if val != '.':
		value = float(val)
		if value > predictor_thresholds[predictor_max]:
			return predictor_colors['max']
		elif value > predictor_thresholds[predictor_min]:
			return predictor_colors['mid_effect']
		return predictor_colors['min']
	else:
		return predictor_colors['no_effect']
#returns a list of effect and color for metadome
def get_metadome_colors(val):
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
#in ajax.py return end pos of a specific variant
#receives g_name as 216420460C>A or 76885812_76885817del
def compute_pos_end(g_name):
	match_object = re.search(r'^(\d+)[ATGC]>', g_name)
	if match_object is not None:
		return match_object.group(1)
	else:
		match_object = re.search(r'_(\d+)[di]', g_name)
		if match_object is not None:
			return match_object.group(1)
		else:
			#case of single nt dels ins dup
			match_object = re.search(r'^(\d+)[d]', g_name)
			if match_object is not None:
				return match_object.group(1)
#slightly diffenent as above as start can differ from VCF and HGVS - for variants > 1bp
def compute_start_end_pos(name):
	match_object = re.search(r'(\d+)_(\d+)[di]', name)
	if match_object is not None:
		return match_object.group(1), match_object.group(2)
	else:
		match_object = re.search(r'^(\d+)[ATGC][>=]', name)
		if match_object is not None:
			return match_object.group(1), match_object.group(1)
		else:
			#single nt del or delins
			match_object = re.search(r'^(\d+)[d]', name)
			if match_object is not None:
				return match_object.group(1), match_object.group(1)

#to be used in create_var_vv
def danger_panel(var, warning):
	return '<div class="w3-margin w3-panel w3-pale-red w3-leftbar w3-display-container"><span class="w3-button w3-ripple w3-display-topright w3-large" onclick="this.parentElement.style.display=\'none\'">X</span><p><span><strong>VariantValidator error: {0}<br/>{1}</strong></span><br /></p></div>'.format(var, warning)
def info_panel(text, var, id_var):
	#Newly created variant:
	c = 'c.'
	if re.search('N[MR]_', var):
		c= ''
	return '<div class="w3-margin w3-panel w3-sand w3-leftbar w3-display-container"><span class="w3-button w3-ripple w3-display-topright w3-large" onclick="this.parentElement.style.display=\'none\'">X</span><p><span><strong>{0}<a href="{1}" target="_blank" title="Go to the variant page"> {2}{3}</a><br/></strong></span><br /></p></div>'.format(text, url_for('md.variant', variant_id=id_var), c, var)

def create_var_vv(vv_key_var, gene, acc_no, new_variant, original_variant, acc_version, vv_data, caller, db, g):
	vf_d = {}
	#deal with various warnings
	#docker up?
	if caller == 'webApp':
		print('Creating variant: {0} - {1}'.format(gene, original_variant))
	if 'flag' not in vv_data:
		if caller == 'webApp':
			send_error_email(prepare_email_html('MobiDetails error', '<p>VariantValidator looks down!! no Flag in json response</p>'), '[MobiDetails - VariantValidator Error]')
			return danger_panel(vv_key_var, "VariantValidator looks down!! Sorry for the inconvenience. Please retry later.")
		elif caller == 'api':
			return {'mobidetails_error': 'VariantValidator looks down'}
	elif vv_data['flag'] is None:
		if caller == 'webApp':
			return danger_panel(vv_key_var, "VariantValidator could not process your variant, please check carefully your nomenclature! Of course this may also come from the gene and not from you!")
		elif caller == 'api':
			return {'mobidetails_error': 'No flag in VariantValidator answer. Please check your variant.'}
	elif re.search('Major error', vv_data['flag']):
		if caller == 'webApp':
			send_error_email(prepare_email_html('MobiDetails error', '<p>A major validation error has occurred in VariantValidator.</p>'), '[MobiDetails - VariantValidator Error]')
			return danger_panel(vv_key_var, "A major validation error has occurred in VariantValidator. VV Admin have been made aware of the issue. Sorry for the inconvenience. Please retry later.")
		elif caller == 'api':
			return {'mobidetails_error': 'A major validation error has occurred in VariantValidator'}
	#print(vv_data['flag'])
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#main isoform?
	curs.execute(
		"SELECT canonical FROM gene WHERE name[2] = '{0}'".format(acc_no)
	)
	res_main = curs.fetchone()
	remapper = False
	if res_main['canonical'] is not True:
		#check if canonical in vv_data
		#we want variants in priority in canonical isoforms
		curs.execute(
			"SELECT name, nm_version FROM gene WHERE name[1] = '{0}' and canonical = 't'".format(gene)
		)
		res_can = curs.fetchone()
		#main_key_reg = "{0}\.{1}".format(res_can['name'][1], res_can['nm_version'])
		# for key in vv_data:
		# 	if re.search('{}'.format(main_key_reg), key):
		# 		vv_key_var = key
				#cannot happen as VV when queried with an isoform returns the results  only for this isoform
		#we could get pseudo VCF values an rerun VV instead
		try:
			hg38_d = get_genomic_values('hg38', vv_data, vv_key_var)
		except:
			#means we have an error
			if vv_data['flag'] == 'warning':
				if caller == 'webApp':
					return danger_panel(vv_key_var, ' '.join(vv_data['validation_warning_1']['validation_warnings']))
				elif caller == 'api':
					return {'mobidetails_error': vv_data['validation_warning_1']['validation_warnings']}
		http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
		vv_url = "{0}VariantValidator/variantvalidator/GRCh38/{1}-{2}-{3}-{4}/all?content-type=application/json".format(urls['variant_validator_api'], hg38_d['chr'], hg38_d['pos'], hg38_d['pos_ref'], hg38_d['pos_alt'])
		try:
			vv_data2 = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
			for key in vv_data2:
				if re.search(r'{0}\.{1}'.format(res_can['name'][1], res_can['nm_version']), key):
					#if canonical isoform in new query
					vv_data = vv_data2
					vv_key_var = key
					var_obj = re.search(r':c\.(.+)$', key)
					vf_d['c_name'] = var_obj.group(1)
					acc_no = res_can['name'][1]
					acc_version = res_can['nm_version']
					first_level_key = key
					remapper = True
		except:
			pass
	
	if 'validation_warning_1' in vv_data:
		first_level_key = 'validation_warning_1'
	if vv_key_var in vv_data:
		first_level_key = vv_key_var
	
	if vv_data['flag'] == 'intergenic':
		first_level_key = 'intergenic_variant_1'
	else:
		for key in vv_data:
			#if vv modified the nomenclature
			if re.search('{}'.format(acc_no), key) and vv_data[key]['submitted_variant'] == vv_key_var:
				vv_key_var = key
				var_obj = re.search(r':c\.(.+)$', key)
				vf_d['c_name'] = var_obj.group(1)
				first_level_key = key
				break
	if 'validation_warnings' in vv_data[first_level_key]:
		for warning in vv_data[first_level_key]['validation_warnings']:
			#print(vv_data[first_level_key])
			if re.search('RefSeqGene record not available', warning):
				vf_d['ng_name'] = 'NULL'
			elif re.search('automapped to {0}\.{1}:c\..+'.format(acc_no, acc_version), warning):
				match_obj = re.search(r'automapped to {0}\.{1}:(c\..+)'.format(acc_no, acc_version), warning)
				if match_obj.group(1) is not None:
					return_text = " VariantValidator reports that your variant should be {0} instead of {1}".format(match_obj.group(1), original_variant)
					if caller == 'webApp':
						return danger_panel(vv_key_var, return_text)
					elif caller == 'api':
						return {'mobidetails_error': '{}'.format(return_text)}
				else:
					danger_panel(vv_key_var, warning)
			elif re.search('normalized', warning):
				match_obj = re.search(r'normalized to ({0}\.{1}:c\..+)'.format(acc_no, acc_version), warning)
				if match_obj.group(1) is not None and match_obj.group(1) == vv_key_var:
					next
				elif caller == 'webApp':
					return danger_panel(vv_key_var, warning)
				elif caller == 'api':
					return {'mobidetails_error': '{}'.format(warning)}
			elif re.search('A more recent version of', warning) or re.search('LRG_', warning) or re.search('Whitespace', warning):
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
	#hg38
	try:
		hg38_d = get_genomic_values('hg38', vv_data, vv_key_var)
	except:
		if caller == 'webApp':
			return danger_panel(vv_key_var, 'Transcript {0} for gene {1} does not seem to map correctly to hg38. Currently, MobiDetails requires proper mapping on hg38 and hg19. It is therefore impossible to create a variant.'.format(acc_no, gene))
		elif caller == 'api':
			return {'mobidetails_error':  'Transcript {0} for gene {1} does not seem to map correctly to hg38. Currently, MobiDetails requires proper mapping on hg38 and hg19. It is therefore impossible to create a variant.'.format(acc_no, gene)}
	
		
	#check again if variant exist
	curs.execute(
		"SELECT feature_id FROM variant WHERE genome_version = '{0}' AND g_name = '{1}'".format(genome, hg38_d['g_name'])
	)
	res = curs.fetchone()
	if res is not None:
		if caller == 'webApp':
			return info_panel('Variant already in MobiDetails: ', vv_key_var, res['feature_id'])
		elif caller == 'api':
			return {'mobidetails_id': res['feature_id'], 'url': '{0}{1}'.format(request.host_url[:-1], url_for('md.variant', variant_id=res['feature_id']))}
	try:
		hg19_d = get_genomic_values('hg19', vv_data, vv_key_var)
	except:
		if caller == 'webApp':
			return danger_panel(vv_key_var, 'Transcript {0} for gene {1} does not seem to map correctly to hg19. Currently, MobiDetails requires proper mapping on hg38 and hg19. It is therefore impossible to create a variant.'.format(acc_no, gene))
		elif caller == 'api':
			return {'mobidetails_error':  'Transcript {0} for gene {1} does not seem to map correctly to hg19. Currently, MobiDetails requires proper mapping on hg38 and hg19. It is therefore impossible to create a variant.'.format(acc_no, gene)}
	positions = compute_start_end_pos(hg38_d['g_name'])
	if 'c_name' not in vf_d:
		var_obj = re.search(r'c\.(.+)$', new_variant)
		vf_d['c_name'] = var_obj.group(1)
	if 'ng_name' not in vf_d:
		ng_name_obj = re.search(r':g\.(.+)$', vv_data[vv_key_var]['hgvs_refseqgene_variant'])
		vf_d['ng_name'] = ng_name_obj.group(1)
	#dna_type
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
			#one bp del or dup
			vf_d['variant_size'] = 1
		else:			
			vf_d['variant_size'] = int(positions[1]) - int(positions[0]) + 1
	
	#we need strand later
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT strand FROM gene WHERE name = '{{\"{0}\",\"{1}\"}}'".format(gene, acc_no)
	)
	res_strand = curs.fetchone()
	if res_strand is None:
		if caller == 'webApp':
			return danger_panel(vv_key_var, 'No strand for gene {}, impossible to create a variant, please contact us'.format(gene))
		elif caller == 'api':
			return {'mobidetails_error': 'No strand for gene {}, impossible to create a variant, please contact us'.format(gene)}
			
	#p_name
	p_obj =  re.search(r':p\.\((.+)\)$', vv_data[vv_key_var]['hgvs_predicted_protein_consequence']['tlr'])
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
		elif re.search(r'_\w{3}\d+del', vf_d['p_name']) or re.search('^\w{3}\d+del', vf_d['p_name']):
			vf_d['prot_type'] = 'inframe deletion'
		elif re.search(r'_\w{3}\d+dup', vf_d['p_name']) or re.search('^\w{3}\d+dup', vf_d['p_name']):
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
		
	#TODO deal with +1,+2 etc
	vf_d['rna_type'] = 'neutral inferred'
	if re.search(r'\d+[\+-][12][^\d]', vf_d['c_name']):
		vf_d['rna_type'] = 'altered inferred'
	#exons pos, etc - based on hg38
	
	
	if positions[0] != positions[1]:
		curs.execute(
			"SELECT number, type FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND '{3}' BETWEEN SYMMETRIC segment_start AND segment_end AND {4} BETWEEN SYMMETRIC segment_start AND segment_end".format(genome, gene, acc_no, positions[0], positions[1])
		)
		res_seg = curs.fetchone()
		if res_seg is not None:
			#start - end in same segment
			vf_d['start_segment_type'] = res_seg['type']
			vf_d['start_segment_number'] = res_seg['number']
			vf_d['end_segment_type'] = res_seg['type']
			vf_d['end_segment_number'] = res_seg['number']			
		else:
			curs.execute(
				"SELECT number, type FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND '{3}' BETWEEN SYMMETRIC segment_start AND segment_end ".format(genome, gene, acc_no, positions[0])
			)
			res_seg1 = curs.fetchone()
			curs.execute(
				"SELECT number, type FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND '{3}' BETWEEN SYMMETRIC segment_start AND segment_end ".format(genome, gene, acc_no, positions[1])
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
		#get IVS name
		if vf_d['start_segment_type'] == 'intron':
			ivs_obj = re.search(r'^\d+([\+-]\d+)_\d+([\+-]\d+)(.+)$', vf_d['c_name'])
			vf_d['ivs_name'] = 'IVS{0}{1}_IVS{2}{3}{4}'.format(vf_d['start_segment_number'], ivs_obj.group(1), vf_d['end_segment_number'], ivs_obj.group(2), ivs_obj.group(3))
	else:
		#substitutions
		#print("SELECT number, type FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND '{3}' BETWEEN SYMMETRIC segment_start AND segment_end ".format(genome, gene, acc_no, positions[0]))
		curs.execute(
			"SELECT number, type FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND '{3}' BETWEEN SYMMETRIC segment_start AND segment_end ".format(genome, gene, acc_no, positions[0])
		)
		res_seg = curs.fetchone()
		vf_d['start_segment_type'] = res_seg['type']
		vf_d['start_segment_number'] = res_seg['number']
		vf_d['end_segment_type'] = res_seg['type']
		vf_d['end_segment_number'] = res_seg['number']
		if vf_d['start_segment_type'] == 'intron':
			ivs_obj = re.search(r'^-?\d+([\+-]\d+)(.+)$', vf_d['c_name'])
			#print(vf_d['c_name'])
			vf_d['ivs_name'] = 'IVS{0}{1}{2}'.format(vf_d['start_segment_number'], ivs_obj.group(1), ivs_obj.group(2))
	if not 'ivs_name' in vf_d:
		vf_d['ivs_name'] = 'NULL'
	#ncbi_chr = get_ncbi_chr_name(db, 'chr{}'.format(hg38_d['chr']), 'hg38')
	#hg38_d['chr'] = ncbi_chr[0]
	record = get_value_from_tabix_file('dbsnp', local_files['dbsnp'][0], hg38_d)
	#reg_chr = get_common_chr_name(db, ncbi_chr[0])
	#hg38_d['chr'] = reg_chr[0]
	if isinstance(record, str):
		vf_d['dbsnp_id'] = 'NULL'
	else:
		match_object =  re.search(r'RS=(.+);RSPOS=', record[7])
		if match_object:
			vf_d['dbsnp_id'] = match_object.group(1)
		#print(record[7])
	#get wt sequence using twobitreader module
	#0-based
	if vf_d['variant_size'] < 50:
		x = int(positions[0])-26
		y = int(positions[1])+25
		genome = twobitreader.TwoBitFile(local_files['human_genome_hg38'][0])
		current_chrom = genome['chr{}'.format(hg38_d['chr'])]
		seq_slice = current_chrom[x:y].upper()
		#seq2 = current_chrom[int(positions[0])+1:int(positions[0])+2]
		#return seq2
		if res_strand['strand'] == '-':
			seq_slice = reverse_complement(seq_slice).upper()
		begin = seq_slice[:25]
		middle = seq_slice[25:len(seq_slice)-25]
		end = seq_slice[-25:]
		#substitutions
		if vf_d['dna_type'] == 'substitution':
			vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
			mt_obj = re.search(r'>([ATGC])$', vf_d['c_name'])
			vf_d['mt_seq'] = "{0} {1} {2}".format(begin, mt_obj.group(1), end)
		elif vf_d['dna_type'] == 'indel':
			ins_obj = re.search(r'delins([ATGC]+)', vf_d['c_name'])
			exp_size = abs(len(middle)-len(ins_obj.group(1)))
			exp = ''
			for i in range(0,exp_size):
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
			for i in range(0,len(ins_obj.group(1))):
				exp += '-'
			vf_d['wt_seq'] = "{0} {1} {2}".format(begin, exp, end)
			vf_d['mt_seq'] = "{0} {1} {2}".format(begin, ins_obj.group(1), end)
		elif vf_d['dna_type'] == 'deletion':
			vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
			exp = ''
			for i in range(0,vf_d['variant_size']):
				exp += '-'
			vf_d['mt_seq'] = "{0} {1} {2}".format(begin, exp, end)
		elif vf_d['dna_type'] == 'duplication':
			exp = ''
			for i in range(0,vf_d['variant_size']):
				exp += '-'
			vf_d['wt_seq'] = "{0} {1}{2} {3}".format(begin, middle, exp, end)
			vf_d['mt_seq'] = "{0} {1}{1} {2}".format(begin,middle, end)
		#return "-{0}-{1}-{2}-{3}-{4}-{5}-{6}-{7}".format(seq_slice, begin, middle, end, vf_d['wt_seq'], vf_d['mt_seq'], x, y)
	#get intervar automated class
	if vf_d['variant_size'] > 1:
		vf_d['acmg_class'] = 3
	elif (vf_d['dna_type'] == 'substitution' and vf_d['start_segment_type'] == 'exon' and re.search(r'^[^\*-]', vf_d['c_name']) and vf_d['p_name'] != 'Met1?' and hg19_d['pos_ref'] != hg19_d['pos_alt']):
		#intervar api returns empty results with hg38 09/2019
		http = urllib3.PoolManager()
		intervar_url = "{0}{1}_updated.v.201904&chr={2}&pos={3}&ref={4}&alt={5}".format(urls['intervar_api'], 'hg19', hg19_d['chr'], hg19_d['pos'], hg19_d['pos_ref'], hg19_d['pos_alt'])
		intervar_json = None
		try:
			intervar_json = json.loads(http.request('GET', intervar_url).data.decode('utf-8'))
		except:
			send_error_email(prepare_email_html('MobiDetails error', '<p>Intervar API call failed in {0} for {1}</p>'.format(os.path.basename(__file__), intervar_url)), '[MobiDetails - Code Error]')
			pass
		#return intervar_data
		if intervar_json is not None:
			curs.execute(
				"SELECT acmg_class FROM valid_class WHERE acmg_translation = '{}'".format(intervar_json['Intervar'].lower())
			)
			res_acmg = curs.fetchone()
			if res_acmg is not None:
				vf_d['acmg_class'] = res_acmg['acmg_class']
		else:
			vf_d['acmg_class'] = 3
	else:
			vf_d['acmg_class'] = 3
	#date, user
	mobiuser = 'mobidetails'
	if caller == 'webApp':
		if g.user is not None:
			mobiuser = g.user['username']
		curs.execute(
			"SELECT id FROM mobiuser WHERE username = '{}'".format(mobiuser)
		)
		vf_d['creation_user'] = curs.fetchone()['id']
	elif caller == 'api':
		vf_d['creation_user'] = g.user['id']
		
	today = datetime.datetime.now()
	vf_d['creation_date'] = '{0}-{1}-{2}'.format(today.strftime("%Y"), today.strftime("%m"), today.strftime("%d"))
	
	s = ", "
	#attributes = 
	t = "', '"
	insert_variant_feature = "INSERT INTO variant_feature (gene_name, {0}) VALUES ('{{\"{1}\",\"{2}\"}}', '{3}') RETURNING id".format(s.join(vf_d.keys()), gene, acc_no, t.join(map(str, vf_d.values()))).replace("'NULL'", "NULL")
	#insert_query = "INSERT INTO variant_features (c_name, gene_name, ng_name, ivs_name, p_name, wt_seq, mt_seq, dna_type, rna_type, prot_type, acmg_class, start_segment_type, start_segment_number, end_segment_type, end_segment_number, variant_size, dbsnp_id, creation_date, creation_user) VALUES ('{0}', '{\"{1}\",\"{2}\"}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}', '{14}', '{15}', '{16}', '{17}', '{18}', '{19}', '{20}', '{21}', '{22}')".format(vf_d['c_name'], gene, acc_no, vf_d['ng_name'], vf_d['ivs_name'], vf_d['p_name'], vf_d['wt_seq'], vf_d['mt_seq'], vf_d['dna_type'], vf_d['rna_type'], vf_d['prot_type'], vf_d['acmg_class'], vf_d['start_segment_type'], vf_d['start_segment_number'], vf_d['end_segment_type'], vf_d['end_segment_number'], vf_d['variant_size'], vf_d['dbsnp_id'], vf_d['creation_date'], vf_d['creation_user'])
	#print(insert_variant_feature)
	curs.execute(insert_variant_feature)
	vf_id = curs.fetchone()[0]
	#print(vf_id)
	#vf_id = 55
	insert_variant_38 = "INSERT INTO variant (feature_id, {0}) VALUES ('{1}', '{2}')".format(s.join(hg38_d.keys()), vf_id, t.join(map(str, hg38_d.values())))
	curs.execute(insert_variant_38)
	insert_variant_19 = "INSERT INTO variant (feature_id, {0}) VALUES ('{1}', '{2}')".format(s.join(hg19_d.keys()), vf_id, t.join(map(str, hg19_d.values())))
	curs.execute(insert_variant_19)
	
	db.commit()
	if remapper is True and caller == 'webApp':
			return info_panel("Successfully created variant (remapped to canonical isoform)", vf_d['c_name'], vf_id)		
	elif caller == 'webApp':
			return info_panel("Successfully created variant", vf_d['c_name'], vf_id)
	if caller == 'api':
			return {'mobidetails_id': vf_id, 'url': '{0}{1}'.format(request.host_url[:-1], url_for('md.variant', variant_id=vf_id))}

def get_genomic_values(genome, vv_data, vv_key_var):
	if vv_data[vv_key_var]['primary_assembly_loci'][genome]:
		g_name_obj = re.search(r':g\.(.+)$', vv_data[vv_key_var]['primary_assembly_loci'][genome]['hgvs_genomic_description'])
		chr_obj = re.search(r'chr([\dXYM]{1,2})$', vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['chr'])
		return {
			'genome_version': genome,
			'g_name': g_name_obj.group(1),
			'chr': chr_obj.group(1),
			'pos': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['pos'],
			'pos_ref': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['ref'],
			'pos_alt': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['alt']
		}

def prepare_email_html(title, message):
    return """<div style="padding:0.01em 16px;line-height:1.5;font-family:Verdana,sans-serif;background-color:#FFFFFF;">
                <div style="color:#FFFFFF;background-color:#2196F3;padding:16px;">
                    <p style="margin:10px 0;font-weight:600;font-size:20px;">{0}</p>
                </div><br />
                <div style="font-size:15px;padding:32px;border-left:6px solid #ccc !important;background-color:#fdf5e6 !important;">{1}</div><br />
                <div style="color:#FFFFFF;background-color:#2196F3;padding:16px;font-weight:600;">
                    <p><a style="color:#FFFFFF;font-size:18px;" href="https://mobidetails.iurc.montp.inserm.fr/MD">MobiDetails</a></p>
                    <p style="font-size:15px;">Online DNA variant interpretation</p>
                    <p style="font-size:12px;">This message is automatically generated. Please do not reply. For specific queries, please contact david baux at <span style="color:#FFFFFF;">&#100;&#097;&#118;&#105;&#100;&#046;&#098;&#097;&#117;&#120;&#064;&#105;&#110;&#115;&#101;&#114;&#109;&#046;&#102;&#114;</span>.</p>
                </div> 
            </div>""".format(title, message)

def send_error_email(message, mail_object):
    params = config.mdconfig(section='email_auth')
    msg = Message(mail_object,
            sender = params['mail_username'],
            recipients = [params['mail_error_recipient']])
    msg.html = message
    mail.send(msg)
