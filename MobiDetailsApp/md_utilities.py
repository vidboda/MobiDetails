import os
import re
import datetime
import psycopg2
import psycopg2.extras
import tabix
import urllib3
import json
import twobitreader
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
	'ncbi_litvar_api': '{}research/bionlp/litvar/api/v1/public/pmids?query=%7B%22variant%22%3A%5B%22litvar%40'.format(url_ncbi),
	'mutalyzer_name_checker': 'https://mutalyzer.nl/name-checker?description=',
	'variant_validator': 'https://variantvalidator.org/variantvalidation/?variant=',
	#uncomment below to use VV web API
	#'variant_validator_api': 'https://rest.variantvalidator.org:443/',
	#'variant_validator_api_info': 'https://rest.variantvalidator.org/webservices/variantvalidator/_/resource_list.json',
	'variant_validator_api': 'http://0.0.0.0:8000/',
	'variant_validator_api_info': 'http://0.0.0.0:8000/webservices/variantvalidator/_/resource_list.json',
	'ucsc_hg19': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg19&lastVirtModeType=default&lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
	'ucsc_hg19_session': '757149165_H4Gy8jWA4BwCuA6WW1M8UxC37MFn',
	'ucsc_hg38': 'http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&lastVirtModeType=default&lastVirtModeExtraState=&virtModeType=default&virtMode=0&nonVirtPosition=&position=',
	'ucsc_hg38_session': '757151741_tUQRsEoYvqXsPekoiKpwY6Ork8eF',
	'ucsc_2bit': 'http://genome.ucsc.edu/goldenPath/help/twoBit.html',
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
	'cadd': [app_path + '/static/resources/CADD/hg38/whole_genome_SNVs.tsv.gz', 'v1.5', 'CADD SNVs', 'Prediction of deleterious effect for all variant types', 'cadd'],
	'cadd_indels': [app_path + '/static/resources/CADD/hg38/InDels.tsv.gz', 'v1.5', 'CADD indels', 'Prediction of deleterious effect for all variant types', 'cadd'],
	'dbsnp': [app_path + '/static/resources/dbsnp/hg38/All_20180418.vcf.gz', 'v151', 'dbSNP', 'Database of human genetic variations', 'ncbi_dbsnp'],
	'human_genome_hg38': [app_path + '/static/resources/genome/hg38.2bit', 'hg38', 'Human genome sequence', 'Human genome sequence chr by chr (2bit format)', 'ucsc_2bit'],
	'human_genome_hg19': [app_path + '/static/resources/genome/hg19.2bit', 'hg19', 'Human genome sequence', 'Human genome sequence chr by chr (2bit format)', 'ucsc_2bit'],
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
	'max': '#FF0000',
	'no_effect': '#000000'
}
predictors_translations = {
	'basic': {'D': 'Damaging', 'T': 'Tolerated', '.': 'no prediction'},
	'pph2': {'D': 'Probably Damaging', 'P': 'Possibly Damaging', 'B': 'Benign', '.': 'no prediction'}
}
complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
def reverse_complement(seq):
	return "".join(complement[base] for base in reversed(seq.upper()))
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
		if abs(int(positions['segment_end'])-int(pos)+1) <= abs(int(positions['segment_start'])-int(pos)+1):
			#near from segment_end
			#if seg_type == 'exon':
			#always exons!!!!
			return ['donor', abs(int(positions['segment_end'])-int(pos))+1]
		else:
			#near from segment_start
			#if seg_type == 'exon':
			return ['acceptor', abs(int(positions['segment_start'])-int(pos))+1]
			
#get aa position fomr hgvs p. (3 letter)
def get_aa_position(hgvs_p):
	match_object = re.match('^\w{3}(\d+)[^\d]+.*$', hgvs_p)
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
	if re.search('(dbNSFP|Indels|whole_genome_SNVs|dbscSNV)', tabix_file):
		i -= 1
	#print(records)
	for record in records:
		if record[i] == var['pos_ref'] and record[i+1] == var['pos_alt']:
			return record
	return 'No match in {}'.format(text)
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
#returns an html color depending on a single threshold
def get_preditor_single_threshold_color(val, predictor):
	#function to get green or red
	if val != '.':
		if float(val) > predictor_thresholds[predictor]:
			return predictor_colors['max']
		return predictor_colors['min']
	else:
		return predictor_colors['no_effect']
#returns an html color depending on a single threshold (reverted, e.g. for fathmm)
def get_preditor_single_threshold_reverted_color(val, predictor):
	#function to get green or red
	if val != '.':
		value = float(val)
		if predictor == 'sift':
			value = 1-(float(val))
		if value < predictor_thresholds[predictor]:
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
		else:
			#case of single nt dels ins dup
			match_object = re.search('^(\d+)[d]', g_name)
			if match_object is not None:
				return match_object.group(1)
#slightly diffenent as above as start can differ from VCF and HGVS - for variants > 1bp
def compute_start_end_pos(name):
	match_object = re.search('(\d+)_(\d+)[di]', name)
	if match_object is not None:
		return match_object.group(1), match_object.group(2)
	else:
		match_object = re.search('^(\d+)[ATGC]>', name)
		if match_object is not None:
			return match_object.group(1), match_object.group(1)
		else:
			#single nt del or delins
			match_object = re.search('^(\d+)[d]', name)
			if match_object is not None:
				return match_object.group(1), match_object.group(1)

#to be used in create_var_vv
def danger_panel(var, warning):
	return '<div class="w3-margin w3-panel w3-pale-red w3-leftbar w3-display-container"><span class="w3-button w3-ripple w3-display-topright w3-large" onclick="this.parentElement.style.display=\'none\'">X</span><p><span><strong>VariantValidator error: {0}<br/>{1}</strong></span><br /></p></div>'.format(var, warning)
def info_panel(text, var, id_var):
	#Newly created variant:
	return '<div class="w3-margin w3-panel w3-sand w3-leftbar w3-display-container"><span class="w3-button w3-ripple w3-display-topright w3-large" onclick="this.parentElement.style.display=\'none\'">X</span><p><span><strong>{0}<a href="/variant/{1}" target="_blank" title="Go to the variant page"> c.{2}</a><br/></strong></span><br /></p></div>'.format(text, id_var, var)

def create_var_vv(vv_key_var, gene, acc_no, new_variant, acc_version, vv_data, caller, db, g):
	vf_d = {}
	#deal with various warnings
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
				var_obj = re.search(':c\.(.+)$', key)
				vf_d['c_name'] = var_obj.group(1)
				first_level_key = key
				break
			# else:
			# 	if re.search('{}'.format(acc_no), key):
			# 		#case of intronic variants with minus sign e.g. NM_206933.2:c.14344-223C>T
			# 		#for an unknown reason vv_key_var is not recognized the same as key
			# 		#typing issue? both are str
			# 		#print('{0}-{1}'.format(type(key), type(vv_key_var)))
			# 		#return danger_panel(key, vv_key_var)
			# 		first_level_key = key
			# 		vv_key_var = key
			#		there was a space in submitted name
	if 'validation_warnings' in vv_data[first_level_key]:
		for warning in vv_data[first_level_key]['validation_warnings']:
			#if warning == vv_key_var or re.search('does not agree with reference', warning):
			#	if caller == 'webApp':
			#		return danger_panel(warning, vv_data[first_level_key]['validation_warnings'][1])
			#elif re.search('length must be', warning) or re.search('that lies outside of the reference sequence', warning) or re.search('No transcripts found ', warning) or re.search('start or end or both are beyond', warning):
			#	if caller == 'webApp':
			#		return danger_panel(vv_key_var, warning)
			if re.search('RefSeqGene record not available', warning):
				vf_d['ng_name'] = 'NULL'
			elif re.search('automapped to {0}\.{1}:c\..+'.format(acc_no, acc_version), warning):
				match_obj = re.search('automapped to {0}\.{1}:(c\..+)'.format(acc_no, acc_version), warning)
				return_text = "VariantValidator reports that your variant should be {0} instead of {1}".format(match_obj.group(1), new_variant)
				if caller == 'webApp':
					return danger_panel(vv_key_var, return_text)
			else:
				if caller == 'webApp':
					return danger_panel(vv_key_var, warning)
	genome = 'hg38'
	#hg38
	hg38_d = get_genomic_values('hg38', vv_data, vv_key_var)
	#check again if variant exixst
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT feature_id FROM variant WHERE genome_version = '{0}' AND g_name = '{1}'".format(genome, hg38_d['g_name'])
	)
	res = curs.fetchone()
	if res is not None:
		return info_panel('Variant already in MobiDetails: ', vv_key_var, res['id'])
	
	hg19_d = get_genomic_values('hg19', vv_data, vv_key_var)
	positions = compute_start_end_pos(hg38_d['g_name'])
	if 'c_name' not in vf_d:
		var_obj = re.search('c\.(.+)$', new_variant)
		vf_d['c_name'] = var_obj.group(1)
	if 'ng_name' not in vf_d:
		ng_name_obj = re.search(':g\.(.+)$', vv_data[vv_key_var]['hgvs_refseqgene_variant'])
		vf_d['ng_name'] = ng_name_obj.group(1)
	#dna_type
	if re.search('>', vf_d['c_name']):
		vf_d['dna_type'] = 'substitution'
		vf_d['variant_size'] = 1 
	elif re.search('del.*ins', vf_d['c_name']):
		vf_d['dna_type'] = 'indel'
	elif re.search('dup', vf_d['c_name']):
		vf_d['dna_type'] = 'duplication'
	elif re.search('ins', vf_d['c_name']):
		vf_d['dna_type'] = 'insertion'
	elif re.search('del', vf_d['c_name']):
		vf_d['dna_type'] = 'deletion'
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
		return danger_panel(vv_key_var, 'No strand for gene {}, impossible to create a variant, please contact us'.format(gene))
			
	#p_name
	p_obj =  re.search(':p\.\((.+)\)$', vv_data[vv_key_var]['hgvs_predicted_protein_consequence']['tlr'])
	if p_obj:
		vf_d['p_name'] = p_obj.group(1)
		if re.search('Ter$', vf_d['p_name']):
			vf_d['prot_type'] = 'nonsense'
		elif re.search('fsTer\d+', vf_d['p_name']):
			vf_d['prot_type'] = 'frameshift'
		elif re.search('\w{3}\d+=', vf_d['p_name']):
			vf_d['prot_type'] = 'silent'
		elif re.search('^\?$', vf_d['p_name']):
			vf_d['prot_type'] = 'unknown'
		elif re.search('^Met1\?$', vf_d['p_name']):
			vf_d['prot_type'] = 'start codon'
		elif re.search('ext', vf_d['p_name']):
			vf_d['prot_type'] = 'stop codon'
		elif re.search('_\d+del', vf_d['p_name']) or re.search('^\d+del', vf_d['p_name']):
			vf_d['prot_type'] = 'inframe deletion'
		elif re.search('_\d+dup', vf_d['p_name']) or re.search('^\d+dup', vf_d['p_name']):
			vf_d['prot_type'] = 'inframe duplication'
		elif re.search('_\d+ins', vf_d['p_name']):
			vf_d['prot_type'] = 'inframe insertion'
		else:
			var_obj = re.search('(\w{3})\d+(\w{3})', vf_d['p_name'])
			if var_obj.group(1) != var_obj.group(2):
				vf_d['prot_type'] = 'missense'
			else:
				vf_d['prot_type'] = 'unknown'
	else:
		vf_d['p_name'] = '?'
		vf_d['prot_type'] = 'unknown'
		
	#TODO deal with +1,+2 etc
	vf_d['rna_type'] = 'neutral inferred'
	if re.search('\d+[\+-][12][^\d]', vf_d['c_name']):
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
			ivs_obj = re.search('^\d+([\+-]\d+)_\d+([\+-]\d+)(.+)$', vf_d['c_name'])
			vf_d['ivs_name'] = 'IVS{0}{1}_IVS{2}{3}{4}'.format(vf_d['start_segment_number'], ivs_obj.group(1), vf_d['end_segment_number'], ivs_obj.group(2), ivs_obj.group(3))
	else:
		#substitutions
		curs.execute(
			"SELECT number, type FROM segment WHERE genome_version = '{0}' AND gene_name = '{{\"{1}\",\"{2}\"}}' AND '{3}' BETWEEN SYMMETRIC segment_start AND segment_end ".format(genome, gene, acc_no, positions[0])
		)
		res_seg = curs.fetchone()
		vf_d['start_segment_type'] = res_seg['type']
		vf_d['start_segment_number'] = res_seg['number']
		vf_d['end_segment_type'] = res_seg['type']
		vf_d['end_segment_number'] = res_seg['number']
		if vf_d['start_segment_type'] == 'intron':
			ivs_obj = re.search('^\d+([\+-]\d+)(.+)$', vf_d['c_name'])
			vf_d['ivs_name'] = 'IVS{0}{1}{2}'.format(vf_d['start_segment_number'], ivs_obj.group(1), ivs_obj.group(2))
	if not 'ivs_name' in vf_d:
		vf_d['ivs_name'] = 'NULL'
	record = get_value_from_tabix_file('dbsnp', local_files['dbsnp'][0], hg38_d)
	if isinstance(record, str):
		vf_d['dbsnp_id'] = 'NULL'
	else:
		match_object =  re.search('RS=(.+);RSPOS=', record[7])
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
		seq_slice = current_chrom[x:y]
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
			mt_obj = re.search('>([ATGC])$', vf_d['c_name'])
			vf_d['mt_seq'] = "{0} {1} {2}".format(begin, mt_obj.group(1), end)
		elif vf_d['dna_type'] == 'indel':
			ins_obj = re.search('delins([ATGC]+)', vf_d['c_name'])
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
			ins_obj = re.search('ins([ATGC]+)', vf_d['c_name'])
			exp = ''
			for i in range(0,len(ins_obj.group[1])):
				exp += '-'
			vf_d['wt_seq'] = "{0} {1} {2}".format(begin, exp, end)
			vf_d['mt_seq'] = "{0} {1}{2} {3}".format(begin, ins_obj.group(1), exp, end)
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
	else:
		#intervar api returns empty results with hg38
		http = urllib3.PoolManager()
		intervar_url = "{0}{1}_updated.v.201904&chr={2}&pos={3}&ref={4}&alt={5}".format(urls['intervar_api'], 'hg19', hg19_d['chr'], hg19_d['pos'], hg19_d['pos_ref'], hg19_d['pos_alt'])
		intervar_data = http.request('GET', intervar_url).data.decode('utf-8')
		#return intervar_data
		if intervar_data != '':
			intervar_json = json.loads(intervar_data)
			#curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
			curs.execute(
				"SELECT acmg_class FROM valid_class WHERE acmg_translation = '{}'".format(intervar_json['Intervar'].lower())
			)
			res_acmg = curs.fetchone()
			if res_acmg is not None:
				vf_d['acmg_class'] = res_acmg['acmg_class']
		else:
			vf_d['acmg_class'] = 3
	#date, user
	if g.user is not None:
		curs.execute(
			"SELECT id FROM mobiuser WHERE username = '{}'".format(g.user['username'])
		)
		vf_d['creation_user'] = curs.fetchone()['id']
	else:
		vf_d['creation_user'] = 10
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
	
	return info_panel("Successfully created variant", vf_d['c_name'], vf_id)

def get_genomic_values(genome, vv_data, vv_key_var):
	if vv_data[vv_key_var]['primary_assembly_loci'][genome]:
		g_name_obj = re.search(':g\.(.+)$', vv_data[vv_key_var]['primary_assembly_loci'][genome]['hgvs_genomic_description'])
		chr_obj = re.search('chr([\dXYM]{1,2})$', vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['chr'])
		return {
			'genome_version': genome,
			'g_name': g_name_obj.group(1),
			'chr': chr_obj.group(1),
			'pos': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['pos'],
			'pos_ref': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['ref'],
			'pos_alt': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['alt']
		}
		