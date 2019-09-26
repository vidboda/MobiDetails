import os
import re
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from MobiDetailsApp.auth import login_required
from MobiDetailsApp.db import get_db
from . import md_utilities

import psycopg2
import psycopg2.extras
import json
import urllib3

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
		return render_template('ajax/defgen.html', variant="{0}.{1}:c.{2}".format(vf['gene_name'][1], vf['nm_version'], vf['c_name']), defgen_file=file_loc, genome=genome)
	else:
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
	intervar_data = json.loads(http.request('GET', intervar_url).data.decode('utf-8'))
	db = get_db()
	curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
	# get all variant_features and gene info
	curs.execute(
		"SELECT html_code FROM valid_class WHERE acmg_translation = '{}'".format(intervar_data['Intervar'].lower())
	)
	res = curs.fetchone()
	return "<span style='color:{0};'>{1}</span>".format(res['html_code'], intervar_data['Intervar'])

#web app - ajax for LOVD API
@bp.route('/lovd', methods=['POST'])
def lovd():
	genome = request.form['genome']
	chrom = request.form['chrom']
	pos = request.form['pos']
	g_name = request.form['g_name']
	c_name = request.form['c_name']
	pos_end = md_utilities.compute_pos_end(g_name)
	http = urllib3.PoolManager()
	#http://www.lovd.nl/search.php?build=hg19&position=chr$evs_chr:".$evs_pos_start."_".$evs_pos_end
	lovd_url = "{0}search.php?build={1}&position=chr{2}:{3}_{4}".format(md_utilities.urls['lovd'], genome, chrom, pos, pos_end)
	lovd_data = re.split('\n', http.request('GET', lovd_url).data.decode('utf-8'))
	if len(lovd_data) == 1:
		return 'No match in LOVD public instances'
	#print(lovd_data)
	lovd_data.remove('"hg_build"\t"g_position"\t"gene_id"\t"nm_accession"\t"DNA"\t"url"')
	lovd_urls = []
	i = 1
	html = ''
	for candidate in lovd_data:
		fields = re.split('\t', candidate)
		#print(fields)
		if len(fields) > 1:
			fields[4] = fields[4].replace('"','')			
			if fields[4] == c_name:				
				lovd_urls.append(fields[5])
	if len(lovd_urls) > 0:
		for url in lovd_urls:
			url = url.replace('"','')
			html += "<a href='{0}' target='_blank'>Link {1}</a> - ".format(url, i)
			i += 1
	else:
		return 'No match in LOVD public instances'
	
	return html
	#return "<span>{0}</span><span>{1}</span>".format(lovd_data, lovd_url)