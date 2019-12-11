import os
import re
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db, close_db
from . import md_utilities

import psycopg2
import psycopg2.extras
import json
import urllib3
import certifi

bp = Blueprint('ajax', __name__)



######################################################################
#web app - ajax for litvar
@bp.route('/litVar', methods=['POST'])
def litvar():
	rsid = request.form['rsid']
	if rsid is not None:
		http = urllib3.PoolManager()
		litvar_data = None
		#litvar_url = "{0}{1}%23%23%22%5D%7D".format(md_utilities.urls['ncbi_litvar_api'], rsid)
		litvar_url = "{0}{1}".format(md_utilities.urls['ncbi_litvar_api'], rsid)
		#print(litvar_url)
		try:
			litvar_data = json.loads(http.request('GET', litvar_url).data.decode('utf-8'))
			#print(litvar_data)
		except:
			md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>Litvar API call failed in {}</p>'.format(os.path.basename(__file__)), '[MobiDetails - API Error]'))
			pass
		#print (rsid)
		if litvar_data is not None:
			#if len(litvar_data) == 0: or re.search(r'mandatory', litvar_data[0])
			if len(litvar_data) == 0:
				return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>'
			return render_template('ajax/litvar.html', urls=md_utilities.urls, pmids=litvar_data[0]['pmids'])
		else:
			return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>'
	else:
		return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>'

######################################################################
#web app - ajax for defgen export file
@bp.route('/defgen', methods=['POST'])
def defgen():
	variant_id = request.form['vfid']
	genome = request.form['genome']
	if variant_id is not None:
		db = get_db()
		curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
		# get all variant_features and gene info
		curs.execute(
			"SELECT * FROM variant_feature a, variant b, gene c WHERE a.id = b.feature_id AND a.gene_name = c.name AND a.id = '{0}' AND b.genome_version = '{1}'".format(variant_id, genome)
		)
		vf = curs.fetchone()
		file_content = "GENE;VARIANT;A_ENREGISTRER;ETAT;RESULTAT;VARIANT_P;VARIANT_C;ENST;NM;POSITION_GENOMIQUE;CLASSESUR5;CLASSESUR3;COSMIC;RS;REFERENCES;CONSEQUENCES;COMMENTAIRE;CHROMOSOME;GENOME_REFERENCE;NOMENCLATURE_HGVS;LOCALISATION;SEQUENCE_REF;LOCUS;ALLELE1;ALLELE2\r\n"
		#"$res->{nom}[0];$res->{nom}[1].$res->{acc_version}:$res->{var};;;;$res->{hgvs_prot};$res->{var};$res->{enst};$res->{nom}[1].$res->{acc_version};$pos;$defgen_acmg;;;$res->{snp_id};;$res->{type_prot};;$chr;hg19;$res->{nom_g};$res->{type_segment} $res->{num_segment};;;;\r\n";
		file_content += "{0};{1}.{2}:c.{3};;;;p.{4};c.{3};{5}:{1}.{2};{6};{7};;;rs{8};;{9};;;chr{10};{11};chr{10}:g.{12};{13} {14};;;;\r\n".format(vf['gene_name'][0], vf['gene_name'][1], vf['nm_version'], vf['c_name'], vf['p_name'], vf['enst'], vf['pos'], vf['acmg_class'], vf['dbsnp_id'], vf['prot_type'], vf['chr'], genome, vf['g_name'], vf['start_segment_type'], vf['start_segment_number'])
		#print(file_content)
		app_path = os.path.dirname(os.path.realpath(__file__))
		file_loc = "defgen/{0}-{1}-{2}{3}-{4}.csv".format(genome, vf['chr'], vf['pos'], vf['pos_ref'], vf['pos_alt'])
		defgen_file = open("{0}/static/{1}".format(app_path, file_loc), "w")
		defgen_file.write(file_content)
		close_db()
		return render_template('ajax/defgen.html', variant="{0}.{1}:c.{2}".format(vf['gene_name'][1], vf['nm_version'], vf['c_name']), defgen_file=file_loc, genome=genome)
	else:
		close_db()
		md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails Ajax error', '<p>DefGen file generation failed in {} (no variant_id)</p>'.format(os.path.basename(__file__)), '[MobiDetails - Ajax Error]'))
		return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">Impossible to create DEFGEN file</div>'

######################################################################	
#web app - ajax for intervar API
@bp.route('/intervar', methods=['POST'])
def intervar():
	genome = request.form['genome']
	chrom = request.form['chrom']
	pos = request.form['pos']
	ref = request.form['ref']
	alt = request.form['alt']
	if len(ref) > 1 or len(alt) > 1:
		return 'No wintervar for indels'
	http = urllib3.PoolManager()
	intervar_url = "{0}{1}_updated.v.201904&chr={2}&pos={3}&ref={4}&alt={5}".format(md_utilities.urls['intervar_api'], genome, chrom, pos, ref, alt)
	try:
		intervar_data = json.loads(http.request('GET', intervar_url).data.decode('utf-8'))
	except:
		md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>Intervar API call failed for {0}-{1}-{2}-{3}-{4}<br /> - from {5}</p>'.format(genome, chrom, pos, ref, alt, os.path.basename(__file__))), '[MobiDetails - API Error]')
		return "<span>No wintervar class</span>"
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT html_code FROM valid_class WHERE acmg_translation = '{}'".format(intervar_data['Intervar'].lower())
	)
	res = curs.fetchone()
	close_db()
	return "<span style='color:{0};'>{1}</span>".format(res['html_code'], intervar_data['Intervar'])

######################################################################
#web app - ajax for LOVD API
@bp.route('/lovd', methods=['POST'])
def lovd():
	genome = request.form['genome']
	chrom = request.form['chrom']
	g_name = request.form['g_name']
	c_name = request.form['c_name']
	positions = md_utilities.compute_start_end_pos(g_name)
	http = urllib3.PoolManager()
	#http://www.lovd.nl/search.php?build=hg19&position=chr$evs_chr:".$evs_pos_start."_".$evs_pos_end
	lovd_url = "{0}search.php?build={1}&position=chr{2}:{3}_{4}".format(md_utilities.urls['lovd'], genome, chrom, positions[0], positions[1])
	lovd_data = None
	try:
		lovd_data = re.split('\n', http.request('GET', lovd_url).data.decode('utf-8'))
	except:
		md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>LOVD API call failed in {}</p>'.format(os.path.basename(__file__)), '[MobiDetails - API Error]'))
		pass
	#print(lovd_url)
	if lovd_data is not None:
		if len(lovd_data) == 1:
			return 'No match in LOVD public instances'	
		lovd_data.remove('"hg_build"\t"g_position"\t"gene_id"\t"nm_accession"\t"DNA"\t"url"')
		lovd_urls = []
		i = 1
		html = ''
		html_list = []
		for candidate in lovd_data:
			fields = re.split('\t', candidate)
			#check if the variant is the same than ours		
			#print(fields)
			if len(fields) > 1:
				fields[4] = fields[4].replace('"','')			
				if fields[4] == c_name or re.match(c_name, fields[4]):	
					lovd_urls.append(fields[5])
		if len(lovd_urls) > 0:
			for url in lovd_urls:
				url = url.replace('"','')
				if re.search('databases.lovd.nl/shared/', url):
					html_list.append("<a href='{0}' target='_blank'>GVLOVDShared</a>".format(url))
				else:
					html_list.append("<a href='{0}' target='_blank'>Link {1}</a>".format(url, i))
				i += 1
		else:
			return 'No match in LOVD public instances'
		html = ' - '.join(html_list)
		return html
	else:
		md_utilities.send_error_email(md_utilities.prepare_email_html('MobiDetails API error', '<p>LOVD service looks down in {}</p>'.format(os.path.basename(__file__)), '[MobiDetails - API Error]'))
		return "LOVD service looks down"
	#return "<span>{0}</span><span>{1}</span>".format(lovd_data, lovd_url)
	
######################################################################
#web app - ajax for variant creation via VV API https://rest.variantvalidator.org/webservices/variantvalidator.html
@bp.route('/create', methods=['POST'])
def create():
	if request.form['new_variant'] == '':
		return md_utilities.danger_panel('Please fill in the form before submitting!')
	
	gene = request.form['gene']
	acc_no = request.form['acc_no']
	new_variant = request.form['new_variant'].replace(" ", "")
	original_variant = new_variant
	acc_version = request.form['acc_version']
	alt_nm = None
	if 'alt_iso' in request.form:
		alt_nm = request.form['alt_iso']
		#return md_utilities.danger_panel(alt_nm, acc_version)
		if alt_nm != '' and alt_nm != "{0}.{1}".format(acc_no, acc_version):
			acc_no, acc_version = alt_nm.split('.')
	#variant already registered?
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	var_db = new_variant.replace("c.", "")
	curs.execute(
		"SELECT id FROM variant_feature WHERE c_name = '{0}' AND gene_name[2] = '{1}'".format(var_db, acc_no)
	)
	res = curs.fetchone()
	if res is not None:
		close_db()
		return md_utilities.info_panel('Variant already in MobiDetails: ', var_db, res['id'])
	
	if re.search('c\..+', new_variant):
		#clean dels and up
		http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
		if alt_nm is None or acc_no == request.form['acc_no']:
			vv_url = "{0}variantvalidator/GRCh38/{1}.{2}:{3}/{1}.{2}".format(md_utilities.urls['variant_validator_api'], acc_no, acc_version, new_variant)
		else:
			vv_url = "{0}variantvalidator/GRCh38/{1}.{2}:{3}/all".format(md_utilities.urls['variant_validator_api'], acc_no, acc_version, new_variant)
		vv_key_var = "{0}.{1}:{2}".format(acc_no, acc_version, new_variant)
		
					
		try:
			vv_data = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
		except:
			close_db()
			return md_utilities.danger_panel(new_variant, 'Variant Validator did not return any value for the variant. Either it is down or your nomenclature is very odd!')
		if re.search('[di][neu][psl]',new_variant):
			#need to redefine vv_key_var for indels as the variant name returned by vv is likely to be different form the user's
			for key in vv_data:
				if re.search('{0}.{1}'.format(acc_no, acc_version), key):
					vv_key_var = key
					#print(key)
					var_obj = re.search(r':(c\..+)$', key)
					if var_obj is not None:
						new_variant = var_obj.group(1)
			
	else:
		close_db()
		return md_utilities.danger_panel(new_variant, 'Please provide the variant name as HGVS c. nomenclature (including c.)')
	return md_utilities.create_var_vv(vv_key_var, gene, acc_no, new_variant, original_variant, acc_version, vv_data, 'webApp', db, g)

######################################################################
#web app - ajax to mark/unmark variants as favourite for logged users
@bp.route('/favourite', methods=['POST'])
@login_required
def favourite():
	vf_id = request.form['vf_id']
	#print(vf_id)
	#g.user['id']
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	if request.form['marker'] == 'mark':
		curs.execute(
			"INSERT INTO mobiuser_favourite (mobiuser_id, feature_id) VALUES ('{0}', '{1}')".format(g.user['id'], vf_id)
		)
	else:
		curs.execute(
			"DELETE FROM mobiuser_favourite WHERE mobiuser_id = '{0}' AND feature_id = '{1}'".format(g.user['id'], vf_id)
		)
	db.commit()
	close_db()
	return 'ok'
	
######################################################################
#web app - ajax for search engine autocomplete
@bp.route('/autocomplete', methods=['POST'])
def autocomplete():
	query = request.form['query_engine']
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	if re.search(r'^c\..+', query):
		match_object = re.search(r'^c\.([\w\d>_\*-]+)', query)
		md_query = match_object.group(1)
		curs.execute(
			"SELECT c_name FROM variant_feature WHERE c_name LIKE '{}%' ORDER BY c_name LIMIT 10".format(md_query)
		)
		res = curs.fetchall()
		result = []
		for var in res:
			result.append('c.{}'.format(var[0]))
		#print(json.dumps(result))
		#print("SELECT c_name FROM variant_feature WHERE gene_name[1] = '{0}' AND c_name LIKE '{1}%' ORDER BY c_name LIMIT 10".format(gene, md_query))
		if result is not None:
			return json.dumps(result)
		else:
			return None
	i = 1
	if re.search(r'^[Nn][Mm]_.+', query):
		i = 2
		query = query.upper()
	elif not re.search(r'orf', query):
		query = query.upper()
	curs.execute(
		"SELECT DISTINCT name[1] FROM gene WHERE name[{0}] LIKE '%{1}%' ORDER BY name[1] LIMIT 5".format(i, query)
	)
	res = curs.fetchall()
	result = []
	for gene in res:
		result.append(gene[0])
	#print("SELECT DISTINCT name[1] FROM gene WHERE name[{0}] LIKE '%{1}%' ORDER BY name[1] LIMIT 5".format(i, query))
	if result is not None:
		return json.dumps(result)
	else:
		return None
	
######################################################################
#web app - ajax for variant creation autocomplete
@bp.route('/autocomplete_var', methods=['POST'])
def autocomplete_var():
	query = request.form['query_engine']
	gene = request.form['gene']
	if re.search(r'^c\..+', query):
		match_object = re.search(r'^c\.([\w\d>_\*-]+)', query)
		md_query = match_object.group(1)
		db = get_db()
		curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
		curs.execute(
			"SELECT c_name FROM variant_feature WHERE gene_name[1] = '{0}' AND c_name LIKE '{1}%' ORDER BY c_name LIMIT 10".format(gene, md_query)
		)
		res = curs.fetchall()
		result = []
		for var in res:
			result.append('c.{}'.format(var[0]))
		#print(json.dumps(result))
		#print("SELECT c_name FROM variant_feature WHERE gene_name[1] = '{0}' AND c_name LIKE '{1}%' ORDER BY c_name LIMIT 10".format(gene, md_query))
		if result is not None:
			return json.dumps(result)
		else:
			return None
	
	
