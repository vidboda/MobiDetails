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
	vv_data = json.loads(http.request('GET', md_utilities.urls['variant_validator_api_info']).data.decode('utf-8'))
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
			"SELECT * FROM gene WHERE name[1] = '{}'".format(gene_name)
		)#get all isoforms
		result_all = curs.fetchall()
		if result_all is not None:
			#get annotations
			curs.execute(
				"SELECT * FROM gene_annotation WHERE gene_name[1] = '{}'".format(gene_name)
			)
			annot = curs.fetchone();
			if annot is None:
				annot = {'nognomad': 'No values in gnomAD'}
			close_db()
			return render_template('md/gene.html', urls=md_utilities.urls, gene=gene_name, main_iso=main, res=result_all, annotations=annot)
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
	if gene is None:
		return render_template('unknown.html', query='No gene provided')
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	#error = None
	#main isoform?
	curs.execute(
		"SELECT * FROM gene WHERE name[1] = '{0}' AND number_of_exons = (SELECT MAX(number_of_exons) FROM gene WHERE name[1] = '{0}')".format(gene_name)
	)
	main = curs.fetchone()
	if main is not None:
		curs.execute(
			"SELECT * FROM variant_feature a, variant b WHERE a.id = b.feature_id AND a.gene_name[1] = '{}' AND b.genome_version = 'hg38'".format(gene_name)
		)
		variants = curs.fetchall()
		#if vars_type is not None:
		close_db()
		return render_template('md/vars.html', urls=md_utilities.urls, gene=gene_name, variants=variants, gene_info=main)
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
		"SELECT * FROM variant_feature a, gene b, mobiuser c WHERE a.gene_name = b.name AND a.creation_user = c.id AND a.id = '{0}'".format(variant_id)
	)
	variant_features = curs.fetchone()
	if variant_features is not None:
		# get variant info
		curs.execute(
			"SELECT * FROM variant WHERE feature_id = '{0}'".format(variant_id)
		)
		variant = curs.fetchall()
	
		#dict for annotations
		annot = {}
		aa_pos = None
		pos_splice_site = None
		domain = None
		# clinvar search & gnomad
		# tabix searches in fact
		
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
				#clinvar
				record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38'][0], var)
				if isinstance(record, str):
					annot['clinsig'] = "{0} {1}".format(record, md_utilities.local_files['clinvar_hg38'][1])
				else:
					annot['clinvar_id'] = record[2]
					match_object =  re.search('CLNSIG=(.+);CLNVC=', record[7])
					if match_object:
						annot['clinsig'] = match_object.group(1)
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
						#sift4g
						#print(record)
						annot['sift4g_score'] = re.split(';', record[39])[i]
						#if annot['sift4g_score'] != '.':
						annot['sift4g_color'] = md_utilities.get_preditor_single_threshold_color(annot['sift4g_score'], 'sift')
						annot['sift4g_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[41])[i]]
						#polyphen 2
						annot['pph2_hdiv_score'] = re.split(';', record[42])[i]
						annot['pph2_hdiv_color'] = md_utilities.get_preditor_double_threshold_color(annot['pph2_hdiv_score'], 'pph2_hdiv_mid', 'pph2_hdiv_max')
						annot['pph2_hdiv_pred'] = md_utilities.predictors_translations['pph2'][re.split(';', record[44])[i]]
						annot['pph2_hvar_score'] = re.split(';', record[45])[i]
						annot['pph2_hvar_color'] = md_utilities.get_preditor_double_threshold_color(annot['pph2_hvar_score'], 'pph2_hvar_mid', 'pph2_hvar_max')
						annot['pph2_hvar_pred'] = md_utilities.predictors_translations['pph2'][re.split(';', record[47])[i]]
						#fathmm
						annot['fathmm_score'] = re.split(';', record[60])[i]
						annot['fathmm_color'] = md_utilities.get_preditor_single_threshold_reverted_color(annot['fathmm_score'], 'fathmm')
						annot['fathmm_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[62])[i]]
						#meta SVM
						#print(record[68])
						annot['msvm_score'] = record[68]
						annot['msvm_color'] = md_utilities.get_preditor_single_threshold_color(annot['msvm_score'], 'meta')
						annot['msvm_pred'] = md_utilities.predictors_translations['basic'][record[70]]
						#meta LR
						annot['mlr_score'] = record[71]
						annot['mlr_color'] = md_utilities.get_preditor_single_threshold_color(annot['mlr_score'], 'meta')
						annot['mlr_pred'] = md_utilities.predictors_translations['basic'][record[73]]
						annot['m_rel'] = record[74] #reliability index for meta score (1-10): the higher, the higher the reliability
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
					#spliceai
					record = md_utilities.get_value_from_tabix_file('spliceAI', md_utilities.local_files['spliceai'][0], var)
					if isinstance(record, str):
						annot['spliceai'] = "{0} {1}".format(record, md_utilities.local_files['spliceai'][1])
					else:
						spliceais = re.split(';', record[7])
						for spliceai in spliceais:
							#DIST=-73;DS_AG=0.0002;DS_AL=0.0000;DS_DG=0.0000;DS_DL=0.0000;DP_AG=14;DP_AL=-3;DP_DG=9;DP_DL=15
							match_object = re.search(r'(\w+)=(.+)', spliceai)
							#put value in annot dict
							identifier = "spliceai_{}".format(match_object.group(1))
							annot[identifier] = match_object.group(2)
							#put also html color corresponging to value
							if re.match('spliceai_DS_', identifier):
								id_color = "{}_color".format(identifier)
								annot[id_color] = md_utilities.get_spliceai_color(float(annot[identifier]))
	else:
		close_db()
		return render_template('md/unknown.html', query="variant id: {}".format(variant_id))
	close_db()
	return render_template('md/variant.html', aa_pos=aa_pos, urls=md_utilities.urls, variant_features=variant_features, variant=variant, pos_splice=pos_splice_site, protein_domain=domain, annot=annot)


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
		col_names = 'id'
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
		elif re.search(r'^[A-Za-z0-9]+$', query_engine):#genes
			sql_table = 'gene'
			query_type = 'name[1]'
			col_names = 'name'
			pattern = query_engine
			if not re.search(r'[oO][rR][fF]', pattern):
				pattern = pattern.upper()
			else:
				pattern = re.sub(r'O', 'o', pattern)
				pattern = re.sub(r'R', 'r', pattern)
				pattern = re.sub(r'F', 'f', pattern)
				pattern = pattern.capitalize()
				#print(pattern)
		else:
			error = 'Sorry I did not understood this query ({}).'.format(query_engine)
			#return render_template('md/unknown.html', query=query_engine, transformed_query=pattern)
		if error is None:
			db = get_db()
			curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
			#sql_query = "SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
			#return render_template('md/search_engine.html', query=text)
			#a little bit of formatting
			if re.search('variant', sql_table) and re.search('>', pattern):
				#upper for the end of the variant, lower for genomic chr
				var_match = re.search(r'^(.*)(\d+)([ACTGactg]>[ACTGactg])$', pattern)
				pattern = var_match.group(1).lower() + var_match.group(2) + var_match.group(3).upper()
				print(pattern)
			curs.execute(
				"SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
			)
			result = curs.fetchone()
			if result is None:
				
				#transformed_query = "SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern)
				error = 'Sorry the variant does not seem to exist yet in MD ({}). You can create it by first going to the corresponding gene page'.format(query_engine)
				close_db()
				#return render_template('md/unknown.html', query=query_engine, transformed_query="SELECT {0} FROM {1} WHERE {2} = '{3}'".format(col_names, sql_table, query_type, pattern))
			elif sql_table == 'gene':
				close_db()
				return redirect(url_for('md.gene', gene_name=result[col_names][0]))
			else:
				close_db()
				return redirect(url_for('md.variant', variant_id=result[col_names]))
	else:
		error = 'Please type something for the search engine to work.'
	flash(error)
	return render_template('md/unknown.html')