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
		litvar_url = "{0}{1}%23%23%22%5D%7D".format(md_utilities.urls['ncbi_litvar_api'], rsid)
		litvar_data = json.loads(http.request('GET', litvar_url).data.decode('utf-8'))
		#print (rsid)
		if len(litvar_data) == 0:
			return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">No match in Pubmed using LitVar API</div>'
		return render_template('ajax/litvar.html', urls=md_utilities.urls, pmids=litvar_data)
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
		return '<div class="w3-blue w3-ripple w3-padding-16 w3-large w3-center" style="width:100%">Impossible to create DEFGEN file</div>'
	
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
	#return intervar_url
	intervar_resp = http.request('GET', intervar_url).data.decode('utf-8')
	#print("----".format(intervar_resp))
	if intervar_resp != '':
		intervar_data = json.loads(intervar_resp)
	else:
		return "<span>No intervar class</span>"
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	curs.execute(
		"SELECT html_code FROM valid_class WHERE acmg_translation = '{}'".format(intervar_data['Intervar'].lower())
	)
	res = curs.fetchone()
	close_db()
	return "<span style='color:{0};'>{1}</span>".format(res['html_code'], intervar_data['Intervar'])

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
	lovd_data = re.split('\n', http.request('GET', lovd_url).data.decode('utf-8'))
	#print(lovd_url)
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
	#return "<span>{0}</span><span>{1}</span>".format(lovd_data, lovd_url)
	
#web app - ajax for variant creation via VV API https://rest.variantvalidator.org/webservices/variantvalidator.html
@bp.route('/create', methods=['POST'])
def create():
	gene = request.form['gene']
	acc_no = request.form['acc_no']
	new_variant = request.form['new_variant'].replace(" ", "")
	acc_version = request.form['acc_version']
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
		return md_utilities.info_panel('Variant already in MobiDetails: ', new_variant, res['id'])
	
	if re.search('c\..+', new_variant):
		http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
		vv_url = "{0}variantvalidator/GRCh38/{1}.{2}:{3}/{1}.{2}".format(md_utilities.urls['variant_validator_api'], acc_no, acc_version, new_variant)
		vv_key_var = "{0}.{1}:{2}".format(acc_no, acc_version, new_variant)
		try:
			vv_data = json.loads(http.request('GET', vv_url).data.decode('utf-8'))
		except:
			close_db()
			return md_utilities.danger_panel(new_variant, 'Variant Validator did not return any value for the variant. A possible cause is that the variant is too large.')
			
	else:
		close_db()
		return md_utilities.danger_panel(new_variant, 'Please provide the variant name as HGVS c. nomenclature (including c.)')
	return md_utilities.create_var_vv(vv_key_var, gene, acc_no, new_variant, acc_version, vv_data, 'webApp', db, g)
