import os
import re
import psycopg2
import psycopg2.extras
import tabix
from MobiDetailsApp.db import get_db

app_path = os.path.dirname(os.path.realpath(__file__))
one2three = {
	'A': 'Ala', 'C': 'Cys', 'D': 'Asp', 'E': 'Glu', 'F': 'Phe', 'G': 'Gly', 'H': 'His', 'I': 'Ile', 'K': 'Lys', 'L': 'Leu', 'M': 'Met', 'N': 'Asn', 'P': 'Pro', 'Q': 'Gln', 'R': 'Arg', 'S': 'Ser', 'T': 'Thr', 'V': 'Val', 'W': 'Trp', 'Y': 'Tyr', 'del': 'del', 'X': '*', '*': '*', '=': '='
}
three2one = {
	'Ala': 'A', 'Cys': 'C', 'Asp': 'D', 'Glu': 'E', 'Phe': 'F', 'Gly': 'G', 'His': 'H', 'Ile': 'I', 'Lys': 'K', 'Leu': 'L', 'Met': 'M', 'Asn': 'N', 'Pro': 'P', 'Gln': 'Q', 'Arg': 'R', 'Ser': 'S', 'Thr': 'T', 'Val': 'V', 'Trp': 'W', 'Tyr': 'Y', 'Del': 'del', 'X': '*', '*': '*', 'Ter': '*', '=': '='
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
	'ncbi_litvar_api': '{}research/bionlp/litvar/api/v1/public/pmids?query=%7B%22variant%22%3A%5B%22litvar%40'.format(url_ncbi),
	'mutalyzer_name_checker': 'https://mutalyzer.nl/name-checker?description=',
	'variant_validator': 'https://variantvalidator.org/variantvalidation/?variant=',
	'variant_validator_api': 'https://rest.variantvalidator.org:443/',
	'ucsc_hg19': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg19&lastVirtModeType=default&lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
	'ucsc_hg19_session': '757149165_H4Gy8jWA4BwCuA6WW1M8UxC37MFn',
	'ucsc_hg38': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&lastVirtModeType=default&lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
	'ucsc_hg38_session': '757151741_tUQRsEoYvqXsPekoiKpwY6Ork8eF',
	'map2pdb': 'http://www.rcsb.org/pdb/chromosome.do?v=',
	'evs': 'http://evs.gs.washington.edu/EVS/PopStatsServlet?searchBy=chromosome',
	'gnomad': 'http://gnomad.broadinstitute.org/',
	'hgvs': 'http://varnomen.hgvs.org/',
	'ensembl_t': 'http://ensembl.org/Homo_sapiens/Transcript/Summary?',
	'marrvel': 'http://marrvel.org/search/gene/',
	'dbscsnv': 'http://www.liulab.science/dbscsnv.html',
	'dbnsfp': 'https://sites.google.com/site/jpopgen/dbNSFP',
	'spliceai': 'https://github.com/Illumina/SpliceAI',
	'sift4g': 'https://sift.bii.a-star.edu.sg/sift4g/AboutSIFT4G.html',
	'pph2': 'http://genetics.bwh.harvard.edu/pph2/',
	'fathmm': 'http://fathmm.biocompute.org.uk/',
	'intervar': 'http://wintervar.wglab.org/results.pos.php?queryType=position&build=',
	'intervar_api': 'http://wintervar.wglab.org/api_new.php?queryType=position&build=',
	'lovd': 'http://www.lovd.nl/',
	'cadd': 'https://cadd.gs.washington.edu/',
}
local_files = {
	#'clinvar_hg19': [app_path + '/static/resources/clinvar/hg19/clinvar_20190916.vcf.gz', '20190916'],
	# id :[local path, version, name, short desc, urls Xref]
	'clinvar_hg38': [app_path + '/static/resources/clinvar/hg38/clinvar_20190916.vcf.gz', 'v20190916', 'ClinVar', 'database of variants, clinically assessed', 'ncbi_clinvar'],
	'gnomad_exome': [app_path + '/static/resources/gnomad/hg19_gnomad_exome_sorted.txt.gz', 'v2', 'gnomAD exome', 'large dataset of variants population frequencies', 'gnomad'],
	'gnomad_genome': [app_path + '/static/resources/gnomad/hg19_gnomad_genome_sorted.txt.gz', 'v2', 'gnomAD genome', 'large dataset of variants population frequencies', 'gnomad'],
	'dbscsnv': [app_path + '/static/resources/dbscSNV/hg19/dbscSNV.txt.gz', 'v1.1', 'dbscSNV', 'Dataset of splicing predictions', 'dbscsnv'],
	'spliceai': [app_path + '/static/resources/spliceai/hg19/exome_spliceai_scores.vcf.gz', 'v1', 'spliceAI', 'Dataset of splicing predictions', 'spliceai'],
	'dbnsfp': [app_path + '/static/resources/dbNSFP/v4_0/dbNSFP4.0a.txt.gz', 'v4.0a', 'dbNSFP', 'Dataset of predictions for missense', 'dbnsfp'],
	'cadd': [app_path + '/static/resources/CADD/hg38/whole_genome_SNVs.tsv.gz', 'v1.5', 'CADD', 'Prediction of deleterious effect for all variant types', 'cadd'],
	'cadd_indels': [app_path + '/static/resources/CADD/hg38/InDels.tsv.gz', 'v1.5', 'CADD', 'Prediction of deleterious effect for all variant types', 'cadd'],
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
	'meta': 0.5,
}
predictor_colors = {
	'min': '#00A020',
	'small_effect': '#FFA020',
	'mid_effect': '#FF6020',
	'max': '#FF0000'
}
predictors_translations = {
	'basic': {'D': 'Damaging', 'T': 'Tolerated'},
	'pph2': {'D': 'Probably Damaging', 'P': 'Possibly Damaging', 'B': 'Benign'}
}

#useless as dbNSFP has been concatenated in a single file
#def get_dbNSFP_file(chrom):
#	return local_files['dbNSFP_base'][0] + chrom + '.gz'


def clean_var_name(variant):
	variant = re.sub('^[cpg]\.', '', variant)
	variant = re.sub(r'\(', '', variant)
	variant = re.sub(r'\)', '', variant)
	return variant

def three2one_fct(var):
	var = clean_var_name(var)
	match_object = re.match('^(\w{3})(\d+)(\w{3}|[X\*=])$', var)
	if match_object:
		return three2one[match_object.group(1).capitalize()] + match_object.group(2) + three2one[match_object.group(3).capitalize()]
	match_object = re.match('^(\w{3})(\d+_)(\w{3})(\d+.+)$', var)
	if match_object:
		return three2one[match_object.group(1)].capitalize() + match_object.group(2) + three2one[match_object.group(3)].capitalize() + match_object.group(4)
	
def one2three_fct(var):
	var = clean_var_name(var)
	match_object = re.match('^(\w{1})(\d+)([\w\*=]{1})$', var)
	if match_object:
		return one2three[match_object.group(1).capitalize()] + match_object.group(2) + one2three[match_object.group(3).capitalize()]
	match_object = re.match('^(\w{1})(\d+_)(\w{1})(\d+.+)$', var)
	if match_object:
		return one2three[match_object.group(1).capitalize()] + match_object.group(2) + one2three[match_object.group(3).capitalize()] + match_object.group(4)
	
#jinja custom filter
def match(value, regexp):
	return re.match(regexp, value)

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
		#return min(abs(int(positions['segment_end'])-int(pos)+1), abs(int(positions['segment_start'])-int(pos)+1))
		if abs(int(positions['segment_end'])-int(pos)+1) <= abs(int(positions['segment_start'])-int(pos)+1):
			#near from segment_end
			#if seg_type == 'exon':
			#always exons!!!!
			return ['donor', abs(int(positions['segment_end'])-int(pos))+1]
			#else:
			#	return ['acceptor', abs(int(positions['segment_end'])-int(pos))+1]
		else:
			#near from segment_start
			#if seg_type == 'exon':
			return ['acceptor', abs(int(positions['segment_start'])-int(pos))+1]
			#else:
			#	return ['donor', abs(int(positions['segment_start'])-int(pos))+1]
			
#get aa position fomr hgvs p. (3 letter)
def get_aa_position(hgvs_p):
	match_object = re.match('^\w{3}(\d+)[^\d]+$', hgvs_p)
	if match_object:
		return match_object.group(1), match_object.group(1)
	match_object = re.match('^\w{3}(\d+)_\w{3}(\d+)[^\d]+$', hgvs_p)
	if match_object:
		#return "{0}_{1}".format(match_object.group(1), match_object.group(2))
		return match_object.group(1), match_object.group(2)
	
#open a file with tabix and look for a record:
def get_value_from_tabix_file(text, tabix_file, var):
	tb = tabix.open(tabix_file)
	records = tb.querys("{0}:{1}-{2}".format(var['chr'], var['pos'], var['pos']))
	i = 3
	if re.search('(dbNSFP|Indels|whole_genome_SNVs)', tabix_file) or re.search('InDels', tabix_file):
		i -= 1
	for record in records:
		if record[i] == var['pos_ref'] and record[i+1] == var['pos_alt']:
			return record
	return 'No match in {}'.format(text)
#returns an html color depending on spliceai score
def get_spliceai_color(value):
	if value > predictor_thresholds['spliceai_max']:
		return predictor_colors['max']
	elif value > predictor_thresholds['spliceai_mid']:
		return predictor_colors['mid_effect']
	elif value > predictor_thresholds['spliceai_min']:
		return predictor_colors['small_effect']
	else:
		return predictor_colors['min']
#returns an html color depending on a single threshold
def get_preditor_single_threshold_color(value, predictor):
	#function to get green or red
	if value > predictor_thresholds[predictor]:
		return predictor_colors['max']
	return predictor_colors['min']
#returns an html color depending on a single threshold (reverted, e.g. for fathmm)
def get_preditor_single_threshold_reverted_color(value, predictor):
	#function to get green or red
	if value < predictor_thresholds[predictor]:
		return predictor_colors['max']
	return predictor_colors['min']
#returns an html color depending on a double threshold
def get_preditor_double_threshold_color(value, predictor_min, predictor_max):
	#function to get green or red
	if value > predictor_thresholds[predictor_max]:
		return predictor_colors['max']
	elif value > predictor_thresholds[predictor_min]:
		return predictor_colors['mid_effect']
	return predictor_colors['min']

#in ajax.py return end pos of a specific variant
#receives g_name as 216420460C>A or 76885812_76885817del
def compute_pos_end(g_name):
	match_object = re.search('^(\d+)[ATGC]>', g_name)
	if match_object is not None:
		return match_object.group(1)	
	else:
		match_object = re.search('_(\d+)[di]', g_name)
		if match_object is not None:
			return match_object.group(1)