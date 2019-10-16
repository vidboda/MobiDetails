import re
import urllib3
import certifi
import json
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
import psycopg2
import psycopg2.extras
import tabix

from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db, close_db
from . import md_utilities

bp = Blueprint('md', __name__)
#to be modified when in prod - modify pythonpath and use venv with mod_wsgi
#https://stackoverflow.com/questions/10342114/how-to-set-pythonpath-on-web-server
#https://flask.palletsprojects.com/en/1.1.x/deploying/mod_wsgi/





######################################################################
#web app - index
@bp.route('/')
def index():
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT COUNT(DISTINCT(name[1])) AS gene, COUNT(name) as transcript FROM gene"
	)
	res = curs.fetchone()
	if res is None:
		error = "There is a problem with the number of genes."
		flash(error)
	else:
		close_db()
		return render_template('md/index.html', nb_genes=res['gene'], nb_isoforms=res['transcript'])

#web app - about
@bp.route('/about')
def about():
	#get VV API version
	http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
	vv_data = None
	try:
		vv_data = json.loads(http.request('GET', md_utilities.urls['variant_validator_api_info']).data.decode('utf-8'))
	except:
		vv_data = {'apiVersion': 'Service Unavailable'}
	#vv_data = json.loads(http.request('GET', 'https://rest.variantvalidator.org/webservices/variantvalidator/_/resource_list.json').data.decode('utf-8'))
	return render_template('md/about.html', vv_data=vv_data, urls=md_utilities.urls, local_files=md_utilities.local_files)


######################################################################
#web app - gene
@bp.route('/gene/<string:gene_name>', methods=['GET', 'POST'])
def gene(gene_name=None):
	if gene_name is None:
		return render_template('unknown.html')
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#main isoform? now canonical is stored in db
	#"SELECT * FROM gene WHERE name[1] = '{0}' AND number_of_exons = (SELECT MAX(number_of_exons) FROM gene WHERE name[1] = '{0}')".format(gene_name)
	curs.execute(
		"SELECT * FROM gene WHERE name[1] = '{0}' AND canonical = 't'".format(gene_name)
	)
	main = curs.fetchone()
	if main is not None:
		curs.execute(
			"SELECT * FROM gene WHERE name[1] = '{}' ORDER BY number_of_exons DESC".format(gene_name)
		)#get all isoforms
		result_all = curs.fetchall()
		num_iso = len(result_all)
		if result_all is not None:
			#get annotations
			curs.execute(
				"SELECT * FROM gene_annotation WHERE gene_name[1] = '{}'".format(gene_name)
			)
			annot = curs.fetchone();
			if annot is None:
				annot = {'nognomad': 'No values in gnomAD'}
			close_db()
			return render_template('md/gene.html', urls=md_utilities.urls, gene=gene_name, num_iso=num_iso, main_iso=main, res=result_all, annotations=annot)
		else:
			close_db()
			return render_template('md/unknown.html', query=gene_name)
	else:
		close_db()
		return render_template('md/unknown.html', query=gene_name)
	
######################################################################
#web app - all genes
@bp.route('/genes')
def genes():
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT DISTINCT(name[1]) AS hgnc FROM gene ORDER BY name[1]"
	)
	genes = curs.fetchall()
	if genes is not None:
		close_db()
		return render_template('md/genes.html', genes=genes)
	else:
		close_db()
		return render_template('md/unknown.html')

######################################################################
#web app - variants in genes
@bp.route('/vars/<string:gene_name>', methods=['GET', 'POST'])
def vars(gene_name=None):
	if gene_name is None:
		return render_template('unknown.html', query='No gene provided')
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#error = None
	#main isoform?
	curs.execute(
		"SELECT * FROM gene WHERE name[1] = '{0}' AND canonical = 't'".format(gene_name)
	)
	main = curs.fetchone()
	if main is not None:
		curs.execute(
			"SELECT name, nm_version FROM gene WHERE name[1] = '{}'".format(gene_name)
		)#get all isoforms
		result_all = curs.fetchall()
		num_iso = len(result_all)
		curs.execute(
			"SELECT * FROM variant_feature a, variant b WHERE a.id = b.feature_id AND a.gene_name[1] = '{}' AND b.genome_version = 'hg38'".format(gene_name)
		)
		variants = curs.fetchall()
		#if vars_type is not None:
		close_db()
		return render_template('md/vars.html', urls=md_utilities.urls, gene=gene_name, num_iso=num_iso, variants=variants, gene_info=main, res=result_all)
	else:
		close_db()
		return render_template('md/unknown.html', query=gene_name)


######################################################################
#web app - variant
@bp.route('/variant/<int:variant_id>', methods=['GET', 'POST'])
def variant(variant_id=None):
	if variant_id is None:
		return render_template('unknown.html', query='No variant provided')
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	# get all variant_features and gene info
	curs.execute(
		"SELECT *, a.id as var_id FROM variant_feature a, gene b, mobiuser c WHERE a.gene_name = b.name AND a.creation_user = c.id AND a.id = '{0}'".format(variant_id)
	)
	variant_features = curs.fetchone()
	if variant_features is not None:
		# get variant info
		curs.execute(
			"SELECT * FROM variant WHERE feature_id = '{0}'".format(variant_id)
		)
		variant = curs.fetchall()
		
		#length of c_name for priting on screen
		var_cname = variant_features['c_name']
		if len(var_cname) > 30:
			match_obj = re.search('(.+ins)[ATGC]+$', var_cname)
			if match_obj is not None:
				var_cname = match_obj.group(1)
		
		#dict for annotations
		annot = {}
		aa_pos = None
		pos_splice_site = None
		domain = None
		#favourite var?
		curs.execute(
			"SELECT mobiuser_id FROM mobiuser_favourite WHERE feature_id = '{0}'".format(variant_id)
		)
		favourite = curs.fetchone()
		if favourite is not None:
			favourite = True
		
		for var in variant:
			if var['genome_version'] == 'hg38':
				# compute position / splice sites
				if variant_features['variant_size'] < 50 and variant_features['start_segment_type'] == 'exon' and not re.search(r'\*', variant_features['c_name']) and not re.search(r'^-', variant_features['c_name']):
					#get a tuple ['site_type', 'dist(bp)']
					pos_splice_site = md_utilities.get_pos_splice_site(db, var['pos'], variant_features['start_segment_type'], variant_features['start_segment_number'], variant_features['gene_name'])
					if variant_features['start_segment_type'] != variant_features['end_segment_type'] or variant_features['start_segment_number'] != variant_features['end_segment_number']:
						#indels > 1 bp
						#get a tuple ['site_type', 'dist(bp)']
						pos_splice_site_second = md_utilities.get_pos_splice_site(var['pos'], variant_features['end_segment_type'], variant_features['end_segment_number'], variant_features['gene_name'])
						if pos_splice_site[1] > pos_splice_site_second[1]:
							#pos_splice_site_second nearest from splice site
							pos_splice_site = pos_splice_site_second						
					#compute position in domain
					#1st get aa pos
					aa_pos = md_utilities.get_aa_position(variant_features['p_name'])
					curs.execute(
						"SELECT * FROM protein_domain WHERE gene_name[2] = '{0}' AND (('{1}' BETWEEN aa_start AND aa_end) OR ('{2}' BETWEEN aa_start AND aa_end));".format(variant_features['gene_name'][1], aa_pos[0], aa_pos[1])
					)
					domain = curs.fetchall()
				#MPA indel splice
				elif variant_features['start_segment_type'] == 'intron' and variant_features['dna_type'] == 'indel' and variant_features['variant_size'] < 50:
					#pos_splice = md_utilities.get_pos_splice_site_intron(variant_features['c_name'])
					if int(md_utilities.get_pos_splice_site_intron(variant_features['c_name'])) <= 20 and 'mpa_score' not in annot or annot['mpa_score'] < 6:
						annot['mpa_score'] = 6
						annot['mpa_impact'] = 'splice indel'		
				#clinvar
				record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38'][0], var)
				if isinstance(record, str):
					annot['clinsig'] = "{0} {1}".format(record, md_utilities.local_files['clinvar_hg38'][1])
				else:
					annot['clinvar_id'] = record[2]
					match_object =  re.search('CLNSIG=(.+);CLNVC=', record[7])
					if match_object:
						match2_object = re.search('^(.+);CLNSIGCONF=(.+)$', match_object.group(1))
						if match2_object:
							annot['clinsig'] = match2_object.group(1)
							annot['clinsigconf'] = match2_object.group(2)
							annot['clinsigconf'] = annot['clinsigconf'].replace('%3B', '-')
						else:
							annot['clinsig'] = match_object.group(1)
					if re.search('pathogenic', annot['clinsig'], re.IGNORECASE):
						annot['mpa_score'] = 10
						annot['mpa_impact'] = 'clinvar pathogenic'
				#MPA PTC
				if 'mpa_score' not in annot or annot['mpa_impact'] != 'clinvar pathogenic':
					if variant_features['prot_type'] == 'nonsense' or variant_features['prot_type'] == 'frameshift':
						annot['mpa_score'] = 10
						annot['mpa_impact'] = variant_features['prot_type']
				#dbNSFP
				if variant_features['prot_type'] == 'missense':
					record = md_utilities.get_value_from_tabix_file('dbnsfp', md_utilities.local_files['dbnsfp'][0], var)
					if isinstance(record, str):
						annot['dbnsfp'] = "{0} {1}".format(record, md_utilities.local_files['dbnsfp'][1])
					else:
						#first: get enst we're dealing with
						i=0
						enst_list = re.split(';', record[14])
						if len(enst_list) > 1:
							for enst in enst_list:
								if variant_features['enst'] == enst:
									transcript_index = i
									i += 1
						#then iterate for each score of interest, e.g.  sift..
						#missense:
						#mpa score
						mpa_missense = 0
						#sift4g
						annot['sift4g_score'] = re.split(';', record[39])[transcript_index]
						#if annot['sift4g_score'] != '.':
						annot['sift4g_color'] = md_utilities.get_preditor_single_threshold_color(annot['sift4g_score'], 'sift')
						annot['sift4g_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[41])[transcript_index]]
						if annot['sift4g_pred'] == 'Damaging':
							mpa_missense += 1
						#polyphen 2
						annot['pph2_hdiv_score'] = re.split(';', record[42])[transcript_index]
						annot['pph2_hdiv_color'] = md_utilities.get_preditor_double_threshold_color(annot['pph2_hdiv_score'], 'pph2_hdiv_mid', 'pph2_hdiv_max')
						annot['pph2_hdiv_pred'] = md_utilities.predictors_translations['pph2'][re.split(';', record[44])[transcript_index]]
						if re.search('Damaging', annot['pph2_hdiv_pred']):
							mpa_missense += 1
						annot['pph2_hvar_score'] = re.split(';', record[45])[transcript_index]
						annot['pph2_hvar_color'] = md_utilities.get_preditor_double_threshold_color(annot['pph2_hvar_score'], 'pph2_hvar_mid', 'pph2_hvar_max')
						annot['pph2_hvar_pred'] = md_utilities.predictors_translations['pph2'][re.split(';', record[47])[transcript_index]]
						if re.search('Damaging', annot['pph2_hvar_pred']):
							mpa_missense += 1
						#fathmm
						annot['fathmm_score'] = re.split(';', record[60])[transcript_index]
						annot['fathmm_color'] = md_utilities.get_preditor_single_threshold_reverted_color(annot['fathmm_score'], 'fathmm')
						annot['fathmm_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[62])[transcript_index]]
						if annot['fathmm_pred'] == 'Damaging':
							mpa_missense += 1
						#fathmm-mkl
						#annot['fathmm_mkl_score'] = re.split(';', record[106])[i]
						#annot['fathmm_mkl_color'] = md_utilities.get_preditor_single_threshold_color(annot['fathmm_mkl_score'], 'meta')
						#annot['fathmm_mkl_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[108])[i]]
						#print(re.split(';', record[108])[0])
						if re.split(';', record[108])[0] == 'D':
							mpa_missense += 1
						#provean
						#annot['provean_score'] = re.split(';', record[63])[i]
						#annot['provean_color'] = md_utilities.get_preditor_single_threshold_reverted_color(annot['provean_score'], 'provean')
						#annot['provean_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[65])[i]]
						#print(re.split(';', record[65])[i])
						if re.split(';', record[65])[transcript_index] == 'D':
							mpa_missense += 1
						#LRT
						#annot['lrt_score'] = re.split(';', record[48])[i]
						#annot['lrt_color'] = md_utilities.get_preditor_single_threshold_color(annot['lrt_score'], 'lrt')
						#annot['lrt_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[50])[i]]
						#print(re.split(';', record[50]))
						if re.split(';', record[50])[0] == 'D':
							mpa_missense += 1
						#MutationTaster
						#annot['mt_score'] = re.split(';', record[48])[i]
						#annot['mt_color'] = md_utilities.get_preditor_single_threshold_color(annot['mt_score'], 'mt')
						#annot['mt_pred'] = md_utilities.predictors_translations['mt'][re.split(';', record[50])[i]]
						#print(re.split(';', record[54])[i])
						if re.split(';', record[54]) == 'A' or  re.split(';', record[50]) == 'D':
							mpa_missense += 1
						#meta SVM
						#print(record[68])
						annot['msvm_score'] = record[68]
						annot['msvm_color'] = md_utilities.get_preditor_single_threshold_color(annot['msvm_score'], 'meta')
						annot['msvm_pred'] = md_utilities.predictors_translations['basic'][record[70]]
						if annot['msvm_pred'] == 'Damaging':
							mpa_missense += 1
						#meta LR
						annot['mlr_score'] = record[71]
						annot['mlr_color'] = md_utilities.get_preditor_single_threshold_color(annot['mlr_score'], 'meta')
						annot['mlr_pred'] = md_utilities.predictors_translations['basic'][record[73]]
						if annot['msvm_pred'] == 'Damaging':
							mpa_missense += 1
						annot['m_rel'] = record[74] #reliability index for meta score (1-10): the higher, the higher the reliability
						if 'mpa_score' not in annot or annot['mpa_score'] < mpa_missense:
							annot['mpa_score'] = mpa_missense
							if annot['mpa_score'] >= 8:
								annot['mpa_impact'] = 'high missense'
							elif annot['mpa_score'] >= 6:
								annot['mpa_impact'] = 'moderate missense'
							else:
								annot['mpa_impact'] = 'low missense'
						
				#CADD
				if variant_features['dna_type'] == 'substitution':
					record = md_utilities.get_value_from_tabix_file('CADD', md_utilities.local_files['cadd'][0], var)
					if isinstance(record, str):
						annot['cadd'] = "{0} {1}".format(record, md_utilities.local_files['cadd'][1])
					else:
						annot['cadd_raw'] = record[4]
						annot['cadd_phred'] = record[5]
				else:
					record = md_utilities.get_value_from_tabix_file('CADD', md_utilities.local_files['cadd_indels'][0], var)
					if isinstance(record, str):
						annot['cadd'] = "{0} {1}".format(record, md_utilities.local_files['cadd_indels'][1])
					else:
						annot['cadd_raw'] = record[4]
						annot['cadd_phred'] = record[5]
				#spliceAI 1.3
				##INFO=<ID=SpliceAI,Number=.,Type=String,Description="SpliceAIv1.3 variant annotation. These include delta scores (DS) and delta positions (DP) for acceptor gain (AG), acceptor loss (AL), donor gain (DG), and donor loss (DL). Format: ALLELE|SYMBOL|DS_AG|DS_AL|DS_DG|DS_DL|DP_AG|DP_AL|DP_DG|DP_DL">
				spliceai_res = False
				if variant_features['dna_type'] == 'substitution':
					record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai_snvs'][0], var)
					spliceai_res = True
				elif ((variant_features['dna_type'] == 'insertion' or variant_features['dna_type'] == 'duplication') and variant_features['variant_size'] == 1) or (variant_features['dna_type'] == 'deletion' and variant_features['variant_size'] <= 4):
					record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai_indels'][0], var)
					spliceai_res = True
				if spliceai_res is True:
					if isinstance(record, str):
						annot['spliceai'] = "{0} {1}".format(record, md_utilities.local_files['spliceai'][1])
					else:
						spliceais = re.split('\|', record[7])
						#ALLELE|SYMBOL|DS_AG|DS_AL|DS_DG|DS_DL|DP_AG|DP_AL|DP_DG|DP_DL
						order_list = ['DS_AG','DS_AL','DS_DG','DS_DL','DP_AG','DP_AL','DP_DG','DP_DL']
						i = 2
						for tag in order_list:
							identifier = "spliceai_{}".format(tag)
							annot[identifier] = spliceais[i]
							i += 1
							if re.match('spliceai_DS_', identifier):
								id_color = "{}_color".format(identifier)
								annot[id_color] = md_utilities.get_spliceai_color(float(annot[identifier]))
								if 'mpa_score' not in annot or annot['mpa_score'] < 10:
									if float(annot[identifier]) > md_utilities.predictor_thresholds['spliceai_max']:
										annot['mpa_score'] = 10
										annot['mpa_impact'] = 'high splice'
									elif float(annot[identifier]) > md_utilities.predictor_thresholds['spliceai_mid']:
										annot['mpa_score'] = 8
										annot['mpa_impact'] = 'moderate splice'
									elif float(annot[identifier]) > md_utilities.predictor_thresholds['spliceai_min']:
										annot['mpa_score'] = 6
										annot['mpa_impact'] = 'low splice'
						# 	
						# annot['spliceai_DS_AG'] = spliceais[2]
						# annot['spliceai_DS_AL'] = spliceais[3]
						# annot['spliceai_DS_DG'] = spliceais[4]
						# annot['spliceai_DS_DL'] = spliceais[5]
						# annot['spliceai_DP_AG'] = spliceais[6]
						# annot['spliceai_DP_AL'] = spliceais[7]
						# annot['spliceai_DP_DG'] = spliceais[8]
						# annot['spliceai_DP_DL'] = spliceais[9]						
						
			elif var['genome_version'] == 'hg19':
				#gnomad ex
				record = md_utilities.get_value_from_tabix_file('gnomAD exome', md_utilities.local_files['gnomad_exome'][0], var)
				if isinstance(record, str):
					annot['gnomad_exome_all'] = record
				else:
					annot['gnomad_exome_all'] = record[5]
				#gnomad ge
				record = md_utilities.get_value_from_tabix_file('gnomAD genome', md_utilities.local_files['gnomad_genome'][0], var)
				if isinstance(record, str):
					annot['gnomad_genome_all'] = record
				else:
					annot['gnomad_genome_all'] = record[5]
				if variant_features['dna_type'] == 'substitution':
					#dbscSNV
					record = md_utilities.get_value_from_tabix_file('dbscSNV', md_utilities.local_files['dbscsnv'][0], var)
					if isinstance(record, str):
						annot['dbscsnv_ada'] = "{0} {1}".format(record, md_utilities.local_files['dbscsnv'][1])
						annot['dbscsnv_rf'] = "{0} {1}".format(record, md_utilities.local_files['dbscsnv'][1])
					else:
						annot['dbscsnv_ada'] = "{:.2f}".format(float(record[14]))
						annot['dbscsnv_ada_color'] = md_utilities.get_preditor_single_threshold_color(float(annot['dbscsnv_ada']), 'dbscsnv')
						annot['dbscsnv_rf'] = "{:.2f}".format(float(record[15]))
						annot['dbscsnv_rf_color'] = md_utilities.get_preditor_single_threshold_color(float(annot['dbscsnv_rf']), 'dbscsnv')
						dbscsnv_mpa_threshold = 0.6
						if 'mpa_score' not in annot or annot['mpa_score'] < 10:
							if float(annot['dbscsnv_ada']) > dbscsnv_mpa_threshold or float(annot['dbscsnv_ada'])  > dbscsnv_mpa_threshold:
								annot['mpa_score'] = 10
								annot['mpa_impact'] = 'high splice'
							
					#spliceai
					# record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai'][0], var)
					# if isinstance(record, str):
					# 	annot['spliceai'] = "{0} {1}".format(record, md_utilities.local_files['spliceai'][1])
					# else:
					# 	spliceais = re.split(';', record[7])
					# 	for spliceai in spliceais:
					# 		#DIST=-73;DS_AG=0.0002;DS_AL=0.0000;DS_DG=0.0000;DS_DL=0.0000;DP_AG=14;DP_AL=-3;DP_DG=9;DP_DL=15
					# 		match_object = re.search(r'(\w+)=(.+)', spliceai)
					# 		#put value in annot dict
					# 		identifier = "spliceai_{}".format(match_object.group(1))
					# 		annot[identifier] = match_object.group(2)
					# 		#put also html color corresponging to value
					# 		if re.match('spliceai_DS_', identifier):
					# 			id_color = "{}_color".format(identifier)
					# 			annot[id_color] = md_utilities.get_spliceai_color(float(annot[identifier]))
					# 			if 'mpa_score' not in annot or annot['mpa_score'] < 10:
					# 				if float(annot[identifier]) > md_utilities.predictor_thresholds['spliceai_max']:
					# 					annot['mpa_score'] = 10
					# 					annot['mpa_impact'] = 'high splice'
					# 				elif float(annot[identifier]) > md_utilities.predictor_thresholds['spliceai_mid']:
					# 					annot['mpa_score'] = 8
					# 					annot['mpa_impact'] = 'moderate splice'
					# 				elif float(annot[identifier]) > md_utilities.predictor_thresholds['spliceai_min']:
					# 					annot['mpa_score'] = 6
					# 					annot['mpa_impact'] = 'low splice'
	else:
		close_db()
		return render_template('md/unknown.html', query="variant id: {}".format(variant_id))
	close_db()
	if 'mpa_score' not in annot:
		annot['mpa_score'] = 0
		annot['mpa_impact'] = 'unknown'
	else:
		annot['mpa_color'] = md_utilities.get_preditor_double_threshold_color(annot['mpa_score'], 'mpa_mid', 'mpa_max')
	return render_template('md/variant.html', favourite=favourite, var_cname=var_cname, aa_pos=aa_pos, urls=md_utilities.urls, thresholds=md_utilities.predictor_thresholds, variant_features=variant_features, variant=variant, pos_splice=pos_splice_site, protein_domain=domain, annot=annot)

######################################################################
#web app - search engine
@bp.route('/search_engine', methods=['POST'])
def search_engine():
	query_engine = request.form['search']
	#query_engine = query_engine.upper()
	error = None
	#print("--{}--".format(query_engine))
	if query_engine is not None and query_engine != '':
		pattern = ''
		query_type = ''
		sql_table = 'variant_feature'
		col_names = 'id, c_name, gene_name, p_name'
		semaph_query = 0
		#deal w/ protein names
		query_engine = re.sub(r'\s', '', query_engine)
		match_object = re.search(r'^([a-zA-Z]{1})(\d+)([a-zA-Z\*]{1})$', query_engine) #e.g. R34X
		if match_object:
			query_type = 'p_name'
			pattern = md_utilities.one2three_fct(query_engine)
		elif re.search(r'^p\..+', query_engine):
			query_type = 'p_name'
			var = md_utilities.clean_var_name(query_engine)
			match_object = re.search(r'^(\w{1})(\d+)([\w\*]{1})$', var) #e.g. p.R34X
			match_object_inter = re.search(r'^(\w{1})(\d+)([d][ue][pl])', var) #e.g. p.L34del
			match_object_long = re.search(r'^(\w{1})(\d+_)(\w{1})(\d+.+)$', var) #e.g. p.R34_E68del
			if match_object or match_object_inter or match_object_long:
				pattern = md_utilities.one2three_fct(var)
			else:
				if re.search('X', var):
					pattern = re.sub(r'X', 'Ter', var)
				elif re.search(r'\*', var):
					pattern = re.sub(r'\*', 'Ter', var)
				else:
					pattern = var
		elif re.search(r'[Cc][Hh][Rr][\dXYM]{1,2}:g\..+', query_engine): #deal w/ genomic
			sql_table = 'variant'
			query_type = 'g_name'
			col_names = 'feature_id'
			match_object = re.search(r'[Cc][Hh][Rr][\dXYM]{1,2}:g\.(.+)', query_engine)
			pattern = match_object.group(1)
			#if re.search(r'>', pattern):
			#	pattern = pattern.upper()
		elif re.search(r'^g\..+', query_engine):#g. ng dna vars
			query_type = 'ng_name'
			pattern = md_utilities.clean_var_name(query_engine)
		elif re.search(r'^c\..+', query_engine):#c. dna vars
			query_type = 'c_name'
			pattern = md_utilities.clean_var_name(query_engine)
		elif re.search(r'^z\d+$', query_engine):#only numbers: get matching variants (exact position match) - specific query
			match_obj = re.search(r'^z(\d+)$', query_engine)
			pattern = match_obj.group(1)
			db = get_db()
			curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
			curs.execute(
				"SELECT {0} FROM {1} WHERE c_name ~ '^{2}[^\d]' OR c_name ~ '_{2}[^\d]' OR p_name ~ '^{2}[^\d]' OR p_name ~ '_{2}[^\d]'".format(col_names, sql_table, pattern)
			)
			semaph_query = 1
		elif re.search(r'^\d{2,}$', query_engine):#only numbers: get matching variants (partial match, at least 2 numbers) - specific query
			db = get_db()
			curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
			curs.execute(
				"SELECT {0} FROM {1} WHERE c_name LIKE '%{2}%' OR p_name LIKE '%{2}%'".format(col_names, sql_table, query_engine)
			)
			semaph_query = 1
		elif re.search(r'^[A-Za-z0-9]+$', query_engine):#genes
			sql_table = 'gene'
			query_type = 'name[1]'
			col_names = 'name'
			pattern = query_engine
			if not re.search(r'[oO][rR][fF]', pattern):
				pattern = pattern.upper()
			else:
				#from experience the only low case in gene is 'orf'
				pattern = re.sub(r'O', 'o', pattern)
				pattern = re.sub(r'R', 'r', pattern)
				pattern = re.sub(r'F', 'f', pattern)
				pattern = pattern.capitalize()		
		else:
			error = 'Sorry I did not understood this query ({}).'.format(query_engine)
			#return render_template('md/unknown.html', query=query_engine, transformed_query=pattern)
		if error is None:
			#print(semaph_query)
			if semaph_query == 0:
				db = get_db()
				curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
				#sql_query = "SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
				#return render_template('md/search_engine.html', query=text)
				#a little bit of formatting
				if re.search('variant', sql_table) and re.search('>', pattern):
					#upper for the end of the variant, lower for genomic chr
					var_match = re.search(r'^(.*)(\d+)([ACTGactg]>[ACTGactg])$', pattern)
					pattern = var_match.group(1).lower() + var_match.group(2) + var_match.group(3).upper()
					#print(pattern)
				curs.execute(
					"SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
				)
				result = None
			if sql_table == 'gene':
				result = curs.fetchone()
				close_db()
				if result is None:
					error = 'Sorry the variant or gene does not seem to exist yet in MD ({}). You can create it by first going to the corresponding gene page'.format(query_engine)
				else:
					return redirect(url_for('md.gene', gene_name=result[col_names][0]))
			else:
				result = curs.fetchall()
				close_db()
				if len(result) == 0:
					error = 'Sorry the variant or gene does not seem to exist yet in MD ({}). You can create it by first going to the corresponding gene page'.format(query_engine)
				else:
					if len(result) == 1:
						#print(result[0][0])
						return redirect(url_for('md.variant', variant_id=result[0][0]))
					else:
						return render_template('md/variant_multiple.html', variants=result)
	else:
		error = 'Please type something for the search engine to work.'
	flash(error)
	return render_template('md/unknown.html')