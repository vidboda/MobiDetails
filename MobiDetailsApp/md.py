import re
import os.path
import urllib3
import certifi
import json
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app as app
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
		md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails PostGreSQL error', '<p>There is a problem with the number of genes.<br /> in {}</p>'.format(os.path.basename(__file__))), '[MobiDetails - PostGreSQL Error]')
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
		d_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails VariantValidator error', '<p>VariantValidator looks down!!<br /> - from {}</p>'.format(os.path.basename(__file__))), '[MobiDetails - VariantValidator Error]')
		vv_data = {'apiVersion': 'Service Unavailable'}
	#vv_data = json.loads(http.request('GET', 'https://rest.variantvalidator.org/webservices/variantvalidator/_/resource_list.json').data.decode('utf-8'))
	return render_template('md/about.html', vv_data=vv_data, urls=md_utilities.urls, local_files=md_utilities.local_files)


######################################################################
#web app - gene
@bp.route('/gene/<string:gene_name>', methods=['GET', 'POST'])
def gene(gene_name=None):
	if gene_name is None:
		return render_template('unknown.html', query='No gene provided')
	elif re.search(r'^[^\w+]$', gene_name):
		return render_template('unknown.html', query=gene_name)
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
		#get metadome json?
		enst_ver = {}
		#if not json metadome file on filesystem, create it in radboud server, then next time get it - it will then be available for future requests
		for gene in result_all:
			#print('{0}{1}.json'.format(md_utilities.local_files['metadome'][0], gene['enst']))
			if not os.path.isfile('{0}{1}.json'.format(md_utilities.local_files['metadome'][0], gene['enst'])):
				http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
				if gene['enst'] not in enst_ver:
					#get enst versions in a dict
					metad_ts = None
					try:
						#print('{0}get_transcripts/{1}'.format(md_utilities.urls['metadome_api'], gene['name'][0]))
						metad_ts = json.loads(http.request('GET', '{0}get_transcripts/{1}'.format(md_utilities.urls['metadome_api'], gene['name'][0])).data.decode('utf-8'))
						if metad_ts is not None and 'trancript_ids' in metad_ts:
							for ts in metad_ts['trancript_ids']:
								if ts['has_protein_data']:
									match_obj = re.search(r'^(ENST\d+)\.\d', ts['gencode_id'])
									enst_ver[match_obj.group(1)] = ts['gencode_id']
					except:
						md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>MetaDome first block code failed for gene {0} ({1})<br /> - from {2}</p>'.format(gene_name, gene['enst'], os.path.basename(__file__)), '[MobiDetails - API Error]'))
						pass
				break
					
		#we check if data exist at metadome
		#we have a set of metadome transcripts
		for enst in enst_ver:
			#print(enst)
			#print('--{}--'.format(app.debug))
			if not os.path.isfile('{0}{1}.json'.format(md_utilities.local_files['metadome'][0], enst)):
				metad_data = None
				try:
					metad_data = json.loads(http.request('GET', '{0}status/{1}/'.format(md_utilities.urls['metadome_api'], enst_ver[enst])).data.decode('utf-8'))
				except:
					md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>MetaDome second block code failed for gene {0} ({1})<br /> - from {2}</p>'.format(gene_name, enst, os.path.basename(__file__)), '[MobiDetails - API Error]'))
					pass
				if metad_data is not None:
					if metad_data['status'] == 'PENDING':
						#get transcript_ids ?? coz of the version number
						#send request to build visualization to metadome
						vis_request = None
						#find out how to get app object
						try:
							vis_request = json.loads(http.request('POST', '{0}submit_visualization/'.format(md_utilities.urls['metadome_api']),
													   headers={'Content-Type': 'application/json'},
													   body=json.dumps({'transcript_id' : enst_ver[enst]})).data.decode('utf-8'))						
							if not app.debug:
								app.logger.info('{} submitted to metadome'.format(vis_request['transcript_id']))
							else:
								print('{} submitted to metadome'.format(vis_request['transcript_id']))
						except:
							md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>Error with metadome submission for {0} ({1})<br /> - from  {2}</p>'.format(gene_name, enst, os.path.basename(__file__)), '[MobiDetails - API Error]'))
							pass
							#print('Error with metadome submission for {}'.format(enst))
					elif metad_data['status'] == 'SUCCESS':
						#get_request = None
						try:
							get_request = json.loads(http.request('GET', '{0}result/{1}/'.format(md_utilities.urls['metadome_api'], enst_ver[enst])).data.decode('utf-8'))		
							#copy in file system
							with open('{0}{1}.json'.format(md_utilities.local_files['metadome'][0], enst), "w", encoding='utf-8') as metad_file:
								json.dump(get_request, metad_file, ensure_ascii=False, indent=4)
							if not app.debug:
								app.logger.info('saving metadome {} into local file system'.format(enst_ver[enst]))
							else:
								print('saving metadome {} into local file system'.format(enst_ver[enst]))
						except:
							md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>Error with metadome file writing for {0} ({1})<br /> - from  {2}</p>'.format(gene_name, enst, os.path.basename(__file__)), '[MobiDetails - API Error]'))
							pass
							#print('error saving metadome json file for {}'.format(enst))
		if result_all is not None:
			#get annotations
			curs.execute(
				"SELECT * FROM gene_annotation WHERE gene_name[1] = '{}'".format(gene_name)
			)
			annot = curs.fetchone()
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
	elif re.search(r'^[^\w+]$', gene_name):
		return render_template('unknown.html', query=gene_name)
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
			match_obj = re.search(r'(.+ins)[ATGC]+$', var_cname)
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
				#HGVS strict genomic names e.g. NC_000001.11:g.216422237G>A
				curs.execute(
					"SELECT ncbi_name, genome_version FROM chromosomes WHERE name = '{0}'".format(var['chr'])
				)
				res_chr = curs.fetchall()
				for res in res_chr:
					if res['genome_version'] == 'hg19':
						annot['ncbi_chr_hg19'] = res['ncbi_name']
					elif res['genome_version'] == 'hg38':
						annot['ncbi_chr_hg38'] = res['ncbi_name']
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
					#metadome data?
					if variant_features['dna_type'] == 'substitution' and os.path.isfile('{0}{1}.json'.format(md_utilities.local_files['metadome'][0], variant_features['enst'])) is True:
						#get value in json file
						with open('{0}{1}.json'.format(md_utilities.local_files['metadome'][0], variant_features['enst']), "r") as metad_file:
							metad_json = json.load(metad_file)
							if 'positional_annotation' in metad_json:
								for pos in metad_json['positional_annotation']:
									if int(pos['protein_pos']) == int(aa_pos[0]):
										if 'sw_dn_ds' in pos:
											annot['metadome_dn_ds'] = "{:.2f}".format(float(pos['sw_dn_ds']))
											[annot['metadome_effect'], annot['metadome_color']] = md_utilities.get_metadome_colors(annot['metadome_dn_ds'])
					
					
				#MPA indel splice
				elif variant_features['start_segment_type'] == 'intron' and variant_features['dna_type'] == 'indel' and variant_features['variant_size'] < 50:
					#pos_splice = md_utilities.get_pos_splice_site_intron(variant_features['c_name'])
					if int(md_utilities.get_pos_splice_site_intron(variant_features['c_name'])) <= 20 and ('mpa_score' not in annot or annot['mpa_score'] < 6):
						annot['mpa_score'] = 6
						annot['mpa_impact'] = 'splice indel'		
				#clinvar
				record = md_utilities.get_value_from_tabix_file('Clinvar', md_utilities.local_files['clinvar_hg38'][0], var)
				if isinstance(record, str):
					annot['clinsig'] = "{0} {1}".format(record, md_utilities.local_files['clinvar_hg38'][1])
				else:
					annot['clinvar_id'] = record[2]
					match_object =  re.search(r'CLNSIG=(.+);CLNVC=', record[7])
					if match_object:
						match2_object = re.search(r'^(.+);CLNSIGCONF=(.+)$', match_object.group(1))
						if match2_object:
							annot['clinsig'] = match2_object.group(1)
							annot['clinsigconf'] = match2_object.group(2)
							annot['clinsigconf'] = annot['clinsigconf'].replace('%3B', '-')
						else:
							annot['clinsig'] = match_object.group(1)
					if re.search('pathogenic', annot['clinsig'], re.IGNORECASE) and not re.search('pathogenicity', annot['clinsig'], re.IGNORECASE):
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
						i = 0
						transcript_index = 0
						enst_list = re.split(';', record[14])
						if len(enst_list) > 1:
							for enst in enst_list:
								if variant_features['enst'] == enst:
									transcript_index = i
								i += 1
						#print(transcript_index)
						#then iterate for each score of interest, e.g.  sift..
						#missense:
						#mpa score
						mpa_missense = 0
						mpa_avail = 0
						#sift
						#if re.search(';', record[39]):
						try:
							annot['sift_score'] = re.split(';', record[36])[transcript_index]
							annot['sift_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[38])[transcript_index]]
							annot['sift_star'] = ''
							if annot['sift_score'] == '.':#search most deleterious in other isoforms
								annot['sift_score'], annot['sift_pred'], annot['sift_star'] = md_utilities.get_most_other_deleterious_pred(record[36], record[38], 1.1, 'lt', 'basic')
						except:
							annot['sift_score'] = record[36]
							annot['sift_pred'] = md_utilities.predictors_translations['basic'][record[38]]
						annot['sift_color'] = md_utilities.get_preditor_single_threshold_color(annot['sift_score'], 'sift')						
						if annot['sift_pred'] == 'Damaging':
							mpa_missense += 1
						if annot['sift_pred'] != 'no prediction':
							mpa_avail += 1
						#polyphen 2 hdiv
						if re.search(';', record[42]):
							annot['pph2_hdiv_score'] = re.split(';', record[42])[transcript_index]
							annot['pph2_hdiv_pred'] = md_utilities.predictors_translations['pph2'][re.split(';', record[44])[transcript_index]]
							if annot['pph2_hdiv_score'] == '.':#search most deleterious in other isoforms
								annot['pph2_hdiv_score'], annot['pph2_hdiv_pred'], annot['pph2_hdiv_star'] = md_utilities.get_most_other_deleterious_pred(record[42], record[44], -0.1, 'gt', 'pph2')
						else:
							annot['pph2_hdiv_score'] = record[42]
							annot['pph2_hdiv_pred'] = md_utilities.predictors_translations['pph2'][record[44]]
						annot['pph2_hdiv_color'] = md_utilities.get_preditor_double_threshold_color(annot['pph2_hdiv_score'], 'pph2_hdiv_mid', 'pph2_hdiv_max')
						if re.search('Damaging', annot['pph2_hdiv_pred']):
							mpa_missense += 1
						if annot['pph2_hdiv_pred'] != 'no prediction':
							mpa_avail += 1
						#hvar
						try:
							annot['pph2_hvar_score'] = re.split(';', record[45])[transcript_index]						
							annot['pph2_hvar_pred'] = md_utilities.predictors_translations['pph2'][re.split(';', record[47])[transcript_index]]
							if annot['pph2_hvar_score'] == '.':#search most deleterious in other isoforms
								annot['pph2_hvar_score'], annot['pph2_hvar_pred'], annot['pph2_hvar_star'] = md_utilities.get_most_other_deleterious_pred(record[45], record[47], -0.1, 'gt', 'pph2')
						except:
							annot['pph2_hvar_score'] = record[42]						
							annot['pph2_hvar_pred'] = md_utilities.predictors_translations['pph2'][record[47]]
						annot['pph2_hvar_color'] = md_utilities.get_preditor_double_threshold_color(annot['pph2_hvar_score'], 'pph2_hvar_mid', 'pph2_hvar_max')
						if re.search('Damaging', annot['pph2_hvar_pred']):
							mpa_missense += 1
						if annot['pph2_hvar_pred'] != 'no prediction':
							mpa_avail += 1
						#fathmm
						try:	
							annot['fathmm_score'] = re.split(';', record[60])[transcript_index]
							annot['fathmm_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[62])[transcript_index]]
							if annot['fathmm_score'] == '.':#search most deleterious in other isoforms
								annot['fathmm_score'], annot['fathmm_pred'], annot['fathmm_star'] = md_utilities.get_most_other_deleterious_pred(record[60], record[62], 20, 'lt', 'basic')
						except:
							 annot['fathmm_score'] = record[60]
							 annot['fathmm_pred'] = md_utilities.predictors_translations['basic'][record[62]]
						annot['fathmm_color'] = md_utilities.get_preditor_single_threshold_reverted_color(annot['fathmm_score'], 'fathmm')
						if annot['fathmm_pred'] == 'Damaging':
							mpa_missense += 1
						if annot['fathmm_pred'] != 'no prediction':
							mpa_avail += 1
						#fathmm-mkl -- not displayed
						try:	
							annot['fathmm_mkl_score'] = re.split(';', record[106])[transcript_index]
							annot['fathmm_mkl_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[108])[transcript_index]]
							if annot['fathmm_mkl_score'] == '.':#search most deleterious in other isoforms
								annot['fathmm_mkl_score'], annot['fathmm_mkl_pred'], annot['fathmm_mkl_star'] = md_utilities.get_most_other_deleterious_pred(record[106], record[108], 20, 'lt', 'basic')
						except:
							annot['fathmm_mkl_score'] = record[106]
							annot['fathmm_mkl_pred'] = md_utilities.predictors_translations['basic'][record[108]]
						annot['fathmm_mkl_color'] = md_utilities.get_preditor_single_threshold_reverted_color(annot['fathmm_mkl_score'], 'fathmm-mkl')
						if annot['fathmm_mkl_pred'] == 'Damaging':
							mpa_missense += 1
						if annot['fathmm_mkl_pred'] != 'no prediction':
							mpa_avail += 1
						#provean -- not displayed
						try:
							annot['provean_score'] = re.split(';', record[63])[transcript_index]
							annot['provean_pred'] = md_utilities.predictors_translations['basic'][re.split(';', record[65])[transcript_index]]
							if annot['provean_score'] == '.':#search most deleterious in other isoforms
								annot['provean_score'], annot['provean_pred'], annot['provean_star'] = md_utilities.get_most_other_deleterious_pred(record[63], record[65], 20, 'lt', 'basic')
						except:
							annot['provean_score'] = record[63]						
							annot['provean_pred'] = md_utilities.predictors_translations['basic'][record[65]]
						annot['provean_color'] = md_utilities.get_preditor_single_threshold_reverted_color(annot['provean_score'], 'provean')
						#print(re.split(';', record[65])[i])
						if annot['provean_pred'] == 'Damaging':
						#if re.split(';', record[65])[transcript_index] == 'D':
							mpa_missense += 1
						if annot['provean_pred'] != 'no prediction':
							mpa_avail += 1
						#LRT -- not displayed
						try:
							annot['lrt_score'] = re.split(';', record[48])[transcript_index]
							annot['lrt_pred'] = re.split(';', record[50])[transcript_index]
							if annot['lrt_score'] == '.':#search most deleterious in other isoforms
								annot['lrt_score'], annot['lrt_pred'], annot['lrt_star'] = md_utilities.get_most_other_deleterious_pred(record[48], record[50], -1, 'gt', 'basic')
						except:
							annot['lrt_score'] = record[48]
							annot['lrt_pred'] = record[50]
						#color must be determined by pred and not score
						#annot['lrt_color'] = md_utilities.get_preditor_single_threshold_reverted_color(annot['lrt_score'], 'lrt')
						#print(re.split(';', record[50]))
						if annot['lrt_pred'] == 'D':
						#if re.split(';', record[50])[0] == 'D':
							mpa_missense += 1
						if re.search(r'^[DUN]', annot['lrt_pred']):
							mpa_avail += 1
						#MutationTaster -- not displayed
						try:
							annot['mt_score'] = re.split(';', record[52])[transcript_index]
							annot['mt_pred'] = md_utilities.predictors_translations['mt'][re.split(';', record[54])[transcript_index]]
							if annot['mt_score'] == '.':#search most deleterious in other isoforms
								annot['mt_score'], annot['mt_pred'], annot['mt_star'] = md_utilities.get_most_other_deleterious_pred(record[52], record[54], -1, 'gt', 'mt')
						except:
							try:
								annot['mt_score'] = record[52]
								annot['mt_pred'] = md_utilities.predictors_translations['mt'][record[54]]
							except:
								annot['mt_score'] = '.'
								annot['mt_pred'] = 'no prediction'
						#color must be determined by pred and not score
						#annot['mt_color'] = md_utilities.get_preditor_single_threshold_color(annot['mt_score'], 'mt')
						#print(re.split(';', record[54])[i])
						if re.search('Disease causing', annot['mt_pred']):
						#if re.split(';', record[54]) == 'A' or  re.split(';', record[50]) == 'D':
							mpa_missense += 1
						if annot['mt_pred'] != 'no prediction':
							mpa_avail += 1
						#meta SVM
						#print(record[68])
						annot['msvm_score'] = record[68]
						annot['msvm_color'] = md_utilities.get_preditor_single_threshold_color(annot['msvm_score'], 'meta-svm')
						annot['msvm_pred'] = md_utilities.predictors_translations['basic'][record[70]]
						if annot['msvm_pred'] == 'Damaging':
							mpa_missense += 1
						if annot['msvm_pred'] != 'no prediction':
							mpa_avail += 1
						#meta LR
						annot['mlr_score'] = record[71]
						annot['mlr_color'] = md_utilities.get_preditor_single_threshold_color(annot['mlr_score'], 'meta-lr')
						annot['mlr_pred'] = md_utilities.predictors_translations['basic'][record[73]]
						if annot['msvm_pred'] == 'Damaging':
							mpa_missense += 1
						if annot['msvm_pred'] != 'no prediction':
							mpa_avail += 1
						annot['m_rel'] = record[74] #reliability index for meta score (1-10): the higher, the higher the reliability
						if 'mpa_score' not in annot or annot['mpa_score'] < mpa_missense:
							#print('{0}/{1}'.format(mpa_missense, mpa_avail))
							annot['mpa_score'] = float('{0:.2f}'.format((mpa_missense / mpa_avail) * 10))
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
						annot['spliceai'] = "{0} {1}".format(record, md_utilities.local_files['spliceai_indels'][1])
					else:
						spliceais = re.split(r'\|', record[7])
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
						try:
							annot['dbscsnv_ada'] = "{:.2f}".format(float(record[14]))
							annot['dbscsnv_ada_color'] = md_utilities.get_preditor_single_threshold_color(float(annot['dbscsnv_ada']), 'dbscsnv')
						except:
							#"score" is '.'
							annot['dbscsnv_ada'] = "No score for dbscSNV ADA {}".format(md_utilities.local_files['dbscsnv'][1])
						try:
							annot['dbscsnv_rf'] = "{:.2f}".format(float(record[15]))
							annot['dbscsnv_rf_color'] = md_utilities.get_preditor_single_threshold_color(float(annot['dbscsnv_rf']), 'dbscsnv')
						except:
							#"score" is '.'
							annot['dbscsnv_rf'] = "No score for dbscSNV RF {}".format(md_utilities.local_files['dbscsnv'][1])
						dbscsnv_mpa_threshold = 0.8
						if 'mpa_score' not in annot or annot['mpa_score'] < 10:
							if (isinstance(annot['dbscsnv_ada'], float) and float(annot['dbscsnv_ada']) > dbscsnv_mpa_threshold) or (isinstance(annot['dbscsnv_rf'], float) and float(annot['dbscsnv_ada'])  > dbscsnv_mpa_threshold):
								annot['mpa_score'] = 10
								annot['mpa_impact'] = 'high splice'
	else:
		close_db()
		return render_template('md/unknown.html', query="variant id: {}".format(variant_id))
	close_db()
	if 'mpa_score' not in annot:
		annot['mpa_score'] = 0
		annot['mpa_impact'] = 'unknown'
	else:
		annot['mpa_color'] = md_utilities.get_preditor_double_threshold_color(annot['mpa_score'], 'mpa_mid', 'mpa_max')
		
	#get VV API version
	http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
	vv_data = None
	try:
		vv_data = json.loads(http.request('GET', md_utilities.urls['variant_validator_api_info']).data.decode('utf-8'))
	except:
		d_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails VariantValidator error', '<p>VariantValidator looks down!!<br /> - from {}</p>'.format(os.path.basename(__file__))), '[MobiDetails - VariantValidator Error]')
		vv_data = {'apiVersion': 'Service Unavailable'}
	
	return render_template('md/variant.html', favourite=favourite, var_cname=var_cname, aa_pos=aa_pos, urls=md_utilities.urls, thresholds=md_utilities.predictor_thresholds, local_files=md_utilities.local_files, vv_data=vv_data, variant_features=variant_features, variant=variant, pos_splice=pos_splice_site, protein_domain=domain, annot=annot)

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
		elif re.search(r'^[Nn][Cc]_0000\d{2}\.\d{1,2}:g\..+', query_engine):#strict HGVS genomic
			sql_table = 'variant'
			query_type = 'g_name'
			col_names = 'feature_id'
			db = get_db()
			match_object = re.search(r'^([Nn][Cc]_0000\d{2}\.\d{1,2}):g\.(.+)', query_engine)
			#res_common = md_utilities.get_common_chr_name(db, match_object.group(1))
			chrom = md_utilities.get_common_chr_name(db, match_object.group(1))[0]
			pattern = match_object.group(2)
			#res_common = md_utilities.get_common_chr_name(db, )
		elif re.search(r'^[Cc][Hh][Rr](\d{1,2}|[XYM]):g\..+', query_engine): #deal w/ genomic
			sql_table = 'variant'
			query_type = 'g_name'
			col_names = 'feature_id'
			match_object = re.search(r'^[Cc][Hh][Rr](\d{1,2}|[XYM]):g\.(.+)', query_engine)
			chrom = match_object.group(1)
			pattern = match_object.group(2)
			#if re.search(r'>', pattern):
			#	pattern = pattern.upper()
		elif re.search(r'^g\..+', query_engine):#g. ng dna vars
			query_type = 'ng_name'
			pattern = md_utilities.clean_var_name(query_engine)
		elif re.search(r'^c\..+', query_engine):#c. dna vars
			query_type = 'c_name'
			pattern = md_utilities.clean_var_name(query_engine)
		elif re.search(r'^%\d+$', query_engine):#only numbers: get matching variants (exact position match) - specific query
			match_obj = re.search(r'^%(\d+)$', query_engine)
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
				if 'db' not in locals():
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
				if pattern == 'g_name':
					curs.execute(
					"SELECT {0} FROM {1} WHERE chr = {2} AND {3} = '{4}'".format(col_names, sql_table, chrom, query_type, pattern)
					)
				else:
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